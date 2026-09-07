from ai_employee.contracts import ConversationEvent
from ai_employee.repository import InMemoryRepository
from ai_employee.services import RunService


def make_event(organization_id: str = "acme", idempotency_key: str = "event-7") -> ConversationEvent:
    return ConversationEvent(
        organization_id=organization_id,
        conversation_id="conversation-1",
        customer_id="customer-1",
        message="交期多久",
        idempotency_key=idempotency_key,
    )


def test_same_event_returns_existing_run() -> None:
    service = RunService(InMemoryRepository())

    first = service.start(make_event())
    repeated = service.start(make_event())

    assert repeated.id == first.id
    assert service.repository.run_count == 1


def test_same_key_is_not_shared_between_organizations() -> None:
    service = RunService(InMemoryRepository())

    acme_run = service.start(make_event("acme", "same"))
    globex_run = service.start(make_event("globex", "same"))

    assert acme_run.id != globex_run.id
    assert service.repository.run_count == 2
