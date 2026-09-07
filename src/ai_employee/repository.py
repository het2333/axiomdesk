from uuid import uuid4

from ai_employee.contracts import (
    AgentRun,
    ApprovalDecision,
    ApprovalRequest,
    AuditEvent,
    ConversationEvent,
    KnowledgeDocument,
    RunStatus,
)


class InMemoryRepository:
    def __init__(self) -> None:
        self._runs_by_event: dict[tuple[str, str], AgentRun] = {}
        self._runs_by_id: dict[str, AgentRun] = {}
        self._documents_by_organization: dict[str, list[KnowledgeDocument]] = {}
        self._approvals_by_key: dict[tuple[str, str, str], ApprovalRequest] = {}
        self.audit_events: list[AuditEvent] = []
        self._tool_execution_keys: set[tuple[str, str]] = set()

    @property
    def run_count(self) -> int:
        return len(self._runs_by_id)

    def create_or_get_run(self, event: ConversationEvent) -> tuple[AgentRun, bool]:
        key = (event.organization_id, event.idempotency_key)
        existing_run = self._runs_by_event.get(key)
        if existing_run is not None:
            return existing_run, False

        run = AgentRun.new_for(event)
        self._runs_by_event[key] = run
        self._runs_by_id[run.id] = run
        return run, True

    def append_audit(self, audit_event: AuditEvent) -> None:
        self.audit_events.append(audit_event)

    @property
    def tool_execution_count(self) -> int:
        return len(self._tool_execution_keys)

    def get_run(self, run_id: str) -> AgentRun:
        return self._runs_by_id[run_id]

    def set_run_status(self, run_id: str, status: RunStatus) -> AgentRun:
        run = self.get_run(run_id)
        run.status = status
        return run

    def create_or_get_approval(
        self, organization_id: str, run_id: str, requested_action: str
    ) -> ApprovalRequest:
        key = (organization_id, run_id, requested_action)
        approval = self._approvals_by_key.get(key)
        if approval is None:
            approval = ApprovalRequest(
                id=str(uuid4()),
                organization_id=organization_id,
                run_id=run_id,
                requested_action=requested_action,
            )
            self._approvals_by_key[key] = approval
        return approval

    def approvals_for_run(self, run_id: str) -> list[ApprovalRequest]:
        return [approval for approval in self._approvals_by_key.values() if approval.run_id == run_id]

    def approval_for(self, organization_id: str, approval_id: str) -> ApprovalRequest:
        for approval in self._approvals_by_key.values():
            if approval.id == approval_id and approval.organization_id == organization_id:
                return approval
        raise KeyError(approval_id)

    def record_decision(self, approval: ApprovalRequest, decision: ApprovalDecision) -> ApprovalRequest:
        approval.decision = decision
        return approval

    def register_tool_execution(self, run_id: str, action: str) -> bool:
        key = (run_id, action)
        if key in self._tool_execution_keys:
            return False
        self._tool_execution_keys.add(key)
        return True

    def add_document(self, document: KnowledgeDocument) -> None:
        self._documents_by_organization.setdefault(document.organization_id, []).append(document)

    def documents_for(self, organization_id: str) -> list[KnowledgeDocument]:
        return self._documents_by_organization.get(organization_id, [])
