from ai_employee.contracts import ConversationEvent, KnowledgeDocument, RunStatus
from ai_employee.repository import InMemoryRepository
from ai_employee.services import RunService
from ai_employee.workflow import AgentWorkflow


def start_run(repository: InMemoryRepository, message: str):
    return RunService(repository).start(
        ConversationEvent(
            organization_id="acme",
            conversation_id="conversation-1",
            customer_id="customer-1",
            message=message,
            idempotency_key=message,
        )
    )


def test_question_completes_with_cited_reply() -> None:
    repository = InMemoryRepository()
    repository.add_document(
        KnowledgeDocument(
            id="delivery-policy",
            organization_id="acme",
            content="标准交期为 7 天。",
        )
    )
    run = start_run(repository, "交期多久")

    completed = AgentWorkflow(repository).execute(run.id)

    assert completed.status is RunStatus.completed
    assert completed.outcome is not None
    assert completed.outcome.action == "reply"
    assert completed.outcome.evidence[0].document_id == "delivery-policy"


def test_follow_up_interrupts_without_a_side_effect() -> None:
    repository = InMemoryRepository()
    run = start_run(repository, "请销售跟进")

    interrupted = AgentWorkflow(repository).execute(run.id)

    assert interrupted.status is RunStatus.awaiting_approval
    assert repository.tool_execution_count == 0
    assert repository.approvals_for_run(run.id)[0].requested_action == "create_follow_up"
