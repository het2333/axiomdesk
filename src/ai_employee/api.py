from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel

from ai_employee.contracts import (
    AgentRun,
    ApprovalDecision,
    ConversationEvent,
    KnowledgeDocument,
    RunStatus,
)
from ai_employee.repository import InMemoryRepository
from ai_employee.services import ApprovalService, RunService
from ai_employee.workflow import AgentWorkflow


class ConversationEventInput(BaseModel):
    conversation_id: str
    customer_id: str
    message: str
    idempotency_key: str


class KnowledgeDocumentInput(BaseModel):
    id: str
    content: str


class ApprovalDecisionInput(BaseModel):
    decision: ApprovalDecision


def require_organization(
    x_organization_id: Annotated[str, Header(alias="X-Organization-Id")],
) -> str:
    return x_organization_id


def create_app(repository: InMemoryRepository | None = None) -> FastAPI:
    active_repository = repository or InMemoryRepository()
    workflow = AgentWorkflow(active_repository)
    run_service = RunService(active_repository)
    approval_service = ApprovalService(active_repository, workflow)
    app = FastAPI(title="Etheralia AI Employee")

    @app.post(
        "/v1/conversation-events",
        response_model=AgentRun,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_conversation_event(
        payload: ConversationEventInput,
        organization_id: Annotated[str, Depends(require_organization)],
    ) -> AgentRun:
        event = ConversationEvent(organization_id=organization_id, **payload.model_dump())
        run = run_service.start(event)
        if run.status is RunStatus.running:
            workflow.execute(run.id)
        return active_repository.run_for(organization_id, run.id)

    @app.post(
        "/v1/knowledge-documents",
        response_model=KnowledgeDocument,
        status_code=status.HTTP_201_CREATED,
    )
    def create_knowledge_document(
        payload: KnowledgeDocumentInput,
        organization_id: Annotated[str, Depends(require_organization)],
    ) -> KnowledgeDocument:
        document = KnowledgeDocument(organization_id=organization_id, **payload.model_dump())
        active_repository.add_document(document)
        return document

    @app.get("/v1/runs/{run_id}", response_model=AgentRun)
    def get_run(
        run_id: str,
        organization_id: Annotated[str, Depends(require_organization)],
    ) -> AgentRun:
        try:
            return active_repository.run_for(organization_id, run_id)
        except KeyError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error

    @app.post("/v1/approvals/{approval_id}/decisions", response_model=AgentRun)
    def decide_approval(
        approval_id: str,
        payload: ApprovalDecisionInput,
        organization_id: Annotated[str, Depends(require_organization)],
    ) -> AgentRun:
        try:
            return approval_service.decide(organization_id, approval_id, payload.decision)
        except KeyError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error

    return app
