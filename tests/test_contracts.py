from ai_employee.contracts import AgentRun, ConversationEvent, RunStatus


def test_event_has_required_tenant_and_message_fields() -> None:
    event = ConversationEvent(
        organization_id="acme",
        conversation_id="c-1",
        customer_id="u-1",
        message="交期多久",
        idempotency_key="e-1",
    )

    assert event.organization_id == "acme"
    assert event.message == "交期多久"


def test_new_run_keeps_the_event_organization_and_starts_running() -> None:
    event = ConversationEvent(
        organization_id="acme",
        conversation_id="c-1",
        customer_id="u-1",
        message="交期多久",
        idempotency_key="e-1",
    )

    run = AgentRun.new_for(event)

    assert run.organization_id == "acme"
    assert run.status is RunStatus.running
    assert run.thread_id == run.id
