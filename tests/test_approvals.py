from ai_employee.contracts import ApprovalDecision, ConversationEvent, RunStatus
from ai_employee.repository import InMemoryRepository
from ai_employee.services import ApprovalService, RunService
from ai_employee.workflow import AgentWorkflow


def make_waiting_run(repository: InMemoryRepository):
    run = RunService(repository).start(
        ConversationEvent(
            organization_id="acme",
            conversation_id="conversation-1",
            customer_id="customer-1",
            message="请销售跟进",
            idempotency_key="follow-up-event",
        )
    )
    workflow = AgentWorkflow(repository)
    return workflow, workflow.execute(run.id)


def test_approval_resumes_original_thread_once() -> None:
    repository = InMemoryRepository()
    workflow, waiting = make_waiting_run(repository)
    approval = repository.approvals_for_run(waiting.id)[0]
    approvals = ApprovalService(repository, workflow)

    completed = approvals.decide("acme", approval.id, ApprovalDecision.approved)
    repeated = approvals.decide("acme", approval.id, ApprovalDecision.approved)

    assert completed.thread_id == waiting.thread_id
    assert completed.status is RunStatus.completed
    assert repeated.id == completed.id
    assert repository.tool_execution_count == 1


def test_rejection_has_no_follow_up_side_effect() -> None:
    repository = InMemoryRepository()
    workflow, waiting = make_waiting_run(repository)
    approval = repository.approvals_for_run(waiting.id)[0]

    rejected = ApprovalService(repository, workflow).decide(
        "acme", approval.id, ApprovalDecision.rejected
    )

    assert rejected.status is RunStatus.rejected
    assert repository.tool_execution_count == 0
