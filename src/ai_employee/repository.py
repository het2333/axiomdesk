from ai_employee.contracts import AgentRun, AuditEvent, ConversationEvent


class InMemoryRepository:
    def __init__(self) -> None:
        self._runs_by_event: dict[tuple[str, str], AgentRun] = {}
        self._runs_by_id: dict[str, AgentRun] = {}
        self.audit_events: list[AuditEvent] = []

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
