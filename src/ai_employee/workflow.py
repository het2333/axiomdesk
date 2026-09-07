from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from ai_employee.contracts import ActionOutcome, AgentRun, ApprovalDecision, Evidence, RunStatus
from ai_employee.repository import InMemoryRepository
from ai_employee.retrieval import KnowledgeRetriever


class WorkflowState(TypedDict, total=False):
    run_id: str
    organization_id: str
    message: str
    action: str
    evidence: list[Evidence]


class AgentWorkflow:
    def __init__(self, repository: InMemoryRepository) -> None:
        self.repository = repository
        self.retriever = KnowledgeRetriever(repository)
        self.graph = self._build_graph()

    def execute(self, run_id: str) -> AgentRun:
        run = self.repository.get_run(run_id)
        self.graph.invoke(
            {
                "run_id": run.id,
                "organization_id": run.organization_id,
                "message": run.event.message,
            },
            config={"configurable": {"thread_id": run.thread_id}},
        )
        return self.repository.get_run(run.id)

    def _build_graph(self):
        builder = StateGraph(WorkflowState)
        builder.add_node("retrieve", self._retrieve)
        builder.add_node("plan", self._plan)
        builder.add_node("act", self._act)
        builder.add_edge(START, "retrieve")
        builder.add_edge("retrieve", "plan")
        builder.add_edge("plan", "act")
        builder.add_edge("act", END)
        return builder.compile(checkpointer=InMemorySaver())

    def _retrieve(self, state: WorkflowState) -> dict[str, list[Evidence]]:
        return {
            "evidence": self.retriever.search(state["organization_id"], state["message"]),
        }

    def _plan(self, state: WorkflowState) -> dict[str, str]:
        action = "create_follow_up" if "跟进" in state["message"] else "reply"
        return {"action": action}

    def _act(self, state: WorkflowState) -> dict[str, object]:
        run = self.repository.get_run(state["run_id"])
        action = state["action"]
        if action == "reply":
            run.status = RunStatus.completed
            run.outcome = ActionOutcome(
                action="reply",
                message=state["message"],
                evidence=state.get("evidence", []),
            )
            return {}

        approval = self.repository.create_or_get_approval(
            run.organization_id, run.id, "create_follow_up"
        )
        run.status = RunStatus.awaiting_approval
        decision = interrupt({"approval_id": approval.id, "action": approval.requested_action})
        if decision == ApprovalDecision.approved.value:
            self.repository.register_tool_execution(run.id, approval.requested_action)
            run.status = RunStatus.completed
            run.outcome = ActionOutcome(action=approval.requested_action, message="已创建跟进")
        else:
            run.status = RunStatus.rejected
            run.outcome = ActionOutcome(action=approval.requested_action, message="审批已拒绝")
        return {}
