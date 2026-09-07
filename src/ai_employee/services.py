from ai_employee.contracts import AgentRun, AuditEvent, ConversationEvent
from ai_employee.repository import InMemoryRepository


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
