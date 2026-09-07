from ai_employee.contracts import Evidence
from ai_employee.repository import InMemoryRepository


class KnowledgeRetriever:
    def __init__(self, repository: InMemoryRepository) -> None:
        self.repository = repository

    def search(self, organization_id: str, query: str) -> list[Evidence]:
        phrases = [query[index : index + 2] for index in range(len(query) - 1)] or [query]
        return [
            Evidence(document_id=document.id, excerpt=document.content)
            for document in self.repository.documents_for(organization_id)
            if any(phrase in document.content for phrase in phrases)
        ]
