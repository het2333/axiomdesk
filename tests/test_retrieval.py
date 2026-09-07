from ai_employee.contracts import KnowledgeDocument
from ai_employee.repository import InMemoryRepository
from ai_employee.retrieval import KnowledgeRetriever


def test_search_never_returns_another_organization_document() -> None:
    repository = InMemoryRepository()
    repository.add_document(
        KnowledgeDocument(
            id="delivery-policy",
            organization_id="acme",
            content="标准交期为 7 天。",
        )
    )
    repository.add_document(
        KnowledgeDocument(
            id="other-policy",
            organization_id="globex",
            content="标准交期为 1 天。",
        )
    )

    evidence = KnowledgeRetriever(repository).search("acme", "交期")

    assert [item.document_id for item in evidence] == ["delivery-policy"]


def test_search_returns_empty_evidence_when_no_document_matches() -> None:
    repository = InMemoryRepository()
    repository.add_document(
        KnowledgeDocument(
            id="delivery-policy",
            organization_id="acme",
            content="标准交期为 7 天。",
        )
    )

    assert KnowledgeRetriever(repository).search("acme", "退款") == []
