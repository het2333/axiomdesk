from ai_employee.contracts import AgentRun, ApprovalDecision, AuditEvent, ConversationEvent
from ai_employee.repository import InMemoryRepository
from ai_employee.workflow import AgentWorkflow


class RunService:
    def __init__(self, repository: InMemoryRepository) -> None:
        self.repository = repository

    def start(self, event: ConversationEvent) -> AgentRun:
        run, created = self.repository.create_or_get_run(event)
        if created:
            self.repository.append_audit(
                AuditEvent(
                    organization_id=event.organization_id,
                    run_id=run.id,
                    event_type="run_started",
                )
            )
        return run


class ApprovalService:
    def __init__(self, repository: InMemoryRepository, workflow: AgentWorkflow) -> None:
        self.repository = repository
        self.workflow = workflow

    def decide(
        self, organization_id: str, approval_id: str, decision: ApprovalDecision
    ) -> AgentRun:
        approval = self.repository.approval_for(organization_id, approval_id)
        if approval.decision is not None:
            return self.repository.get_run(approval.run_id)
        self.repository.record_decision(approval, decision)
        return self.workflow.resume(approval.run_id, decision)
