# Independent AI Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a standalone FastAPI and LangGraph runtime that processes tenant-scoped customer events, retrieves evidence, gates risky actions through approval, and resumes durable runs.

**Architecture:** Pydantic contracts and a repository protocol isolate domain behavior from persistence. A deterministic LangGraph workflow produces safe replies or approval interruptions. Decisions resume the original graph thread through `Command(resume=...)` and an idempotency ledger protects external actions.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, LangGraph, SQLAlchemy 2, PostgreSQL driver, pytest, Ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-09-08-independent-ai-runtime-design.md`

## Global Constraints

- Use only `ai_employee` domain names; do not copy legacy platform models, API contracts, source text, or fixtures.
- Every run, document, approval, and side effect must be organization-scoped.
- `reply` is low risk; `create_follow_up` requires approval.
- Tests must fail before production code is added.
- Tests require no model credential or hosted database.

---

### Task 1: Establish contracts and package tooling

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `src/ai_employee/__init__.py`, `src/ai_employee/contracts.py`, `tests/test_contracts.py`

**Interfaces:** Produces immutable Pydantic contracts `ConversationEvent`, `KnowledgeDocument`, `AgentRun`, `ApprovalRequest`, `AuditEvent`, `Evidence`, and status/decision enums.

- [ ] **Step 1: Write the failing test**

```python
from ai_employee.contracts import ConversationEvent


def test_event_has_required_tenant_and_message_fields():
    event = ConversationEvent(organization_id="acme", conversation_id="c-1", customer_id="u-1", message="交期多久", idempotency_key="e-1")
    assert event.organization_id == "acme"
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_contracts.py -q`

Expected: FAIL because the package does not exist.

- [ ] **Step 3: Implement minimal contracts**

```python
class ConversationEvent(BaseModel):
    organization_id: str
    conversation_id: str
    customer_id: str
    message: str
    idempotency_key: str
```

Add `RunStatus` with `running`, `awaiting_approval`, `completed`, `rejected`, and `failed`; use UUID default factories for durable records.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_contracts.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore src/ai_employee tests/test_contracts.py
git commit -m "feat: add independent runtime contracts"
```

### Task 2: Implement tenant-scoped, idempotent run storage

**Files:**
- Create: `src/ai_employee/repository.py`, `src/ai_employee/services.py`, `tests/test_run_service.py`

**Interfaces:** Consumes `ConversationEvent` and produces `InMemoryRepository.create_or_get_run(event) -> tuple[AgentRun, bool]` and `RunService.start(event) -> AgentRun`.

- [ ] **Step 1: Write failing behavior tests**

```python
def test_same_event_returns_existing_run():
    service = RunService(InMemoryRepository())
    first = service.start(make_event(idempotency_key="event-7"))
    assert service.start(make_event(idempotency_key="event-7")).id == first.id


def test_same_key_is_not_shared_between_organizations():
    service = RunService(InMemoryRepository())
    assert service.start(make_event("acme", "same")).id != service.start(make_event("globex", "same")).id
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_run_service.py -q`

Expected: FAIL because repository and service modules do not exist.

- [ ] **Step 3: Implement minimal storage**

```python
key = (event.organization_id, event.idempotency_key)
if key in self._runs_by_event:
    return self._runs_by_event[key], False
run = AgentRun.new_for(event)
self._runs_by_event[key] = run
return run, True
```

Append `run_started` only for newly created runs and expose organization-scoped getters.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_run_service.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ai_employee/repository.py src/ai_employee/services.py tests/test_run_service.py
git commit -m "feat: add tenant scoped run storage"
```

### Task 3: Add organization-isolated evidence retrieval

**Files:**
- Create: `src/ai_employee/retrieval.py`, `tests/test_retrieval.py`

**Interfaces:** Consumes `KnowledgeDocument` and produces `KnowledgeRetriever.search(organization_id, query) -> list[Evidence]`.

- [ ] **Step 1: Write the failing isolation test**

```python
def test_search_never_returns_another_organization_document():
    repository.add_document(KnowledgeDocument(id="a", organization_id="acme", content="标准交期为 7 天"))
    repository.add_document(KnowledgeDocument(id="b", organization_id="globex", content="标准交期为 1 天"))
    assert [item.document_id for item in retriever.search("acme", "交期")] == ["a"]
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_retrieval.py -q`

Expected: FAIL because `KnowledgeRetriever` does not exist.

- [ ] **Step 3: Implement deterministic retrieval**

Filter documents by organization before substring scoring and return only `Evidence(document_id, excerpt)` values.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_retrieval.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ai_employee/retrieval.py tests/test_retrieval.py
git commit -m "feat: add tenant isolated evidence retrieval"
```

### Task 4: Implement the approval-aware LangGraph workflow

**Files:**
- Create: `src/ai_employee/workflow.py`, `tests/test_workflow.py`

**Interfaces:** Produces `AgentWorkflow.execute(run_id) -> AgentRun` and `AgentWorkflow.resume(run_id, decision) -> AgentRun`.

- [ ] **Step 1: Write the failing workflow tests**

```python
def test_question_completes_with_cited_reply():
    run = workflow.execute(make_run("交期多久"))
    assert run.status is RunStatus.completed
    assert run.outcome.action == "reply"


def test_follow_up_interrupts_without_a_side_effect():
    run = workflow.execute(make_run("请销售跟进"))
    assert run.status is RunStatus.awaiting_approval
    assert repository.tool_execution_count == 0
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_workflow.py -q`

Expected: FAIL because `AgentWorkflow` does not exist.

- [ ] **Step 3: Implement StateGraph nodes**

Classify messages containing `跟进` as `create_follow_up`; classify all other messages as `reply`. Retrieve evidence, create an approval and call `interrupt({"approval_id": approval.id})` for follow-up. Compile with a checkpointer and `thread_id=run.thread_id`.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_workflow.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ai_employee/workflow.py tests/test_workflow.py
git commit -m "feat: add approval aware agent workflow"
```

### Task 5: Resume decisions and protect side effects

**Files:**
- Modify: `src/ai_employee/repository.py`, `src/ai_employee/services.py`, `src/ai_employee/workflow.py`
- Create: `tests/test_approvals.py`

**Interfaces:** Produces `ApprovalService.decide(organization_id, approval_id, decision) -> AgentRun`.

- [ ] **Step 1: Write failing resume tests**

```python
def test_approval_resumes_original_thread_once():
    waiting = workflow.execute(make_run("请销售跟进"))
    approval = repository.approvals_for_run(waiting.id)[0]
    completed = approvals.decide("acme", approval.id, ApprovalDecision.approved)
    assert completed.thread_id == waiting.thread_id
    assert repository.tool_execution_count == 1
    approvals.decide("acme", approval.id, ApprovalDecision.approved)
    assert repository.tool_execution_count == 1


def test_rejection_has_no_follow_up_side_effect():
    waiting = workflow.execute(make_run("请销售跟进"))
    approval = repository.approvals_for_run(waiting.id)[0]
    assert approvals.decide("acme", approval.id, ApprovalDecision.rejected).status is RunStatus.rejected
    assert repository.tool_execution_count == 0
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_approvals.py -q`

Expected: FAIL because `ApprovalService` does not exist.

- [ ] **Step 3: Implement decision and ledger**

Use `Command(resume=decision.value)` with the existing thread id. Store tool keys as `(run.id, action)`, set an approval decision once, and return 404-equivalent `NotFoundError` when the organization does not own it.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_approvals.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ai_employee/repository.py src/ai_employee/services.py src/ai_employee/workflow.py tests/test_approvals.py
git commit -m "feat: resume approved runs safely"
```

### Task 6: Add public API, enterprise-WeChat boundary, and verification

**Files:**
- Create: `src/ai_employee/api.py`, `src/ai_employee/adapters/__init__.py`, `src/ai_employee/adapters/enterprise_wechat.py`, `tests/test_api.py`, `README.md`
- Modify: `pyproject.toml`

**Interfaces:** Produces `create_app(repository) -> FastAPI` and `EnterpriseWeChatAdapter.to_event(payload, organization_id) -> ConversationEvent`.

- [ ] **Step 1: Write failing API tests**

```python
def test_duplicate_event_returns_the_same_run(client):
    payload = {"conversation_id": "c-1", "customer_id": "u-1", "message": "交期多久", "idempotency_key": "m-1"}
    first = client.post("/v1/conversation-events", headers={"X-Organization-Id": "acme"}, json=payload)
    repeated = client.post("/v1/conversation-events", headers={"X-Organization-Id": "acme"}, json=payload)
    assert first.status_code == 202
    assert repeated.json()["id"] == first.json()["id"]


def test_other_organization_cannot_decide_private_approval(client):
    response = client.post("/v1/approvals/apr-private/decisions", headers={"X-Organization-Id": "globex"}, json={"decision": "approved"})
    assert response.status_code == 404
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_api.py -q`

Expected: FAIL because `create_app` does not exist.

- [ ] **Step 3: Implement the HTTP boundary**

Require `X-Organization-Id`, invoke the event workflow, expose approval decisions and runs, and return 404 for cross-tenant records. The adapter translates a provider payload without making network calls.

- [ ] **Step 4: Verify GREEN and static checks**

Run: `pytest -q && ruff check src tests && mypy src`

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

```bash
git add src/ai_employee tests README.md pyproject.toml
git commit -m "feat: expose independent agent api"
```
