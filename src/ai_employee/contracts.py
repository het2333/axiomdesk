from __future__ import annotations

from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class RunStatus(StrEnum):
    running = "running"
    awaiting_approval = "awaiting_approval"
    completed = "completed"
    rejected = "rejected"
    failed = "failed"


class ApprovalDecision(StrEnum):
    approved = "approved"
    rejected = "rejected"


class ConversationEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    organization_id: str
    conversation_id: str
    customer_id: str
    message: str
    idempotency_key: str


class KnowledgeDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    organization_id: str
    content: str


class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    excerpt: str


class ActionOutcome(BaseModel):
    action: str
    message: str
    evidence: list[Evidence] = Field(default_factory=list)


class AgentRun(BaseModel):
    id: str
    organization_id: str
    event: ConversationEvent
    thread_id: str
    status: RunStatus
    outcome: ActionOutcome | None = None

    @classmethod
    def new_for(cls, event: ConversationEvent) -> AgentRun:
        run_id = str(uuid4())
        return cls(
            id=run_id,
            organization_id=event.organization_id,
            event=event,
            thread_id=run_id,
            status=RunStatus.running,
        )


class ApprovalRequest(BaseModel):
    id: str
    organization_id: str
    run_id: str
    requested_action: str
    decision: ApprovalDecision | None = None


class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    organization_id: str
    run_id: str
    event_type: str
