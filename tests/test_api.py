import pytest
from fastapi.testclient import TestClient

from ai_employee.api import create_app
from ai_employee.repository import InMemoryRepository


@pytest.fixture
def repository() -> InMemoryRepository:
    return InMemoryRepository()


@pytest.fixture
def client(repository: InMemoryRepository) -> TestClient:
    return TestClient(create_app(repository))


def test_duplicate_event_returns_the_same_run(client: TestClient) -> None:
    payload = {
        "conversation_id": "c-1",
        "customer_id": "u-1",
        "message": "交期多久",
        "idempotency_key": "m-1",
    }

    first = client.post("/v1/conversation-events", headers={"X-Organization-Id": "acme"}, json=payload)
    repeated = client.post(
        "/v1/conversation-events", headers={"X-Organization-Id": "acme"}, json=payload
    )

    assert first.status_code == 202
    assert repeated.status_code == 202
    assert repeated.json()["id"] == first.json()["id"]


def test_other_organization_cannot_decide_private_approval(
    client: TestClient, repository: InMemoryRepository
) -> None:
    created = client.post(
        "/v1/conversation-events",
        headers={"X-Organization-Id": "acme"},
        json={
            "conversation_id": "c-1",
            "customer_id": "u-1",
            "message": "请销售跟进",
            "idempotency_key": "m-2",
        },
    )
    approval_id = repository.approvals_for_run(created.json()["id"])[0].id

    response = client.post(
        f"/v1/approvals/{approval_id}/decisions",
        headers={"X-Organization-Id": "globex"},
        json={"decision": "approved"},
    )

    assert response.status_code == 404


def test_knowledge_endpoint_is_scoped_to_the_request_organization(client: TestClient) -> None:
    response = client.post(
        "/v1/knowledge-documents",
        headers={"X-Organization-Id": "acme"},
        json={"id": "delivery-policy", "content": "标准交期为 7 天。"},
    )

    assert response.status_code == 201
    assert response.json()["organization_id"] == "acme"
