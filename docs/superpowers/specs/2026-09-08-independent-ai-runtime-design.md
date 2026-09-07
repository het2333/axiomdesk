# Independent AI Employee Runtime Design

## Goal

Build an independently authored, China-ready B2B AI Employee runtime. The first release accepts normalized enterprise conversation events, retrieves tenant-scoped knowledge, pauses risky actions for approval, and resumes the same durable run after a decision.

## Scope

The release contains a Python FastAPI service, a LangGraph workflow, PostgreSQL persistence, a generic channel adapter contract, and an enterprise-WeChat adapter boundary. It does not contain a multi-channel customer-service suite, CRM, marketing automation, or copied source, schemas, UI, tests, or content from any existing customer-service product.

## Architecture

One Python service owns the public HTTP API and the execution workflow. A channel adapter normalizes inbound messages into `ConversationEvent`; the workflow owns no channel-specific behavior. PostgreSQL stores tenant data, agent runs, approval decisions, and an idempotency ledger. LangGraph uses a thread identifier equal to the run identifier so an approved action resumes the original graph rather than creating a second run.

```text
Enterprise WeChat adapter / future adapters
                 |
                 v
        ConversationEvent API
                 |
                 v
  tenant context -> retrieve evidence -> decide action
                                      |          |
                                      |          v
                                      |      safe tool call
                                      v
                             approval checkpoint
                                      |
                                      v
                             Command(resume=decision)
                                      |
                                      v
                           persisted run + audit event
```

## Domain Model

- `Organization`: isolated business tenant.
- `Member`: an organization administrator, operator, approver, or auditor.
- `Customer`: a contact owned by one organization.
- `Conversation`: a customer interaction stream from one channel.
- `ConversationEvent`: normalized incoming message with an idempotency key.
- `KnowledgeDocument`: tenant-owned source text and metadata.
- `AgentRun`: a durable execution record with status, thread id, input, and outcome.
- `ApprovalRequest`: an explicit decision required before a risk-classified tool action.
- `AuditEvent`: append-only record of material actions.

## Workflow

1. Validate that the event belongs to the authenticated organization and has not been accepted before.
2. Persist a run in `running` status.
3. Retrieve only knowledge that belongs to the same organization and attach source identifiers as evidence.
4. Select a response action. The first release supports `reply` and `create_follow_up`.
5. Execute a low-risk action exactly once using the idempotency ledger. A high-risk action emits an approval request and interrupts the LangGraph thread.
6. An approver sends `approved` or `rejected`. Approval resumes the original graph through `Command(resume=...)`; rejection records a safe outcome without a tool side effect.
7. Persist the terminal result and append audit events. An interrupted or failed run can be resumed from its same thread id.

## API Boundary

- `POST /v1/conversation-events`: create or return an idempotent agent run.
- `POST /v1/approvals/{approval_id}/decisions`: record a decision and resume the linked run.
- `GET /v1/runs/{run_id}`: return execution status and evidence-safe outcome.
- `POST /v1/knowledge-documents`: add tenant-scoped source text for retrieval.

Every request identifies an organization using an explicit development header in the first release. Production authentication is intentionally deferred, but every service boundary requires the organization id so tenant isolation cannot be optional.

## Safety and Recovery

- Actions are classified by explicit policy, not model preference.
- Only `reply` is low risk; follow-up creation requires approval in this release.
- Each tool execution uses `(organization_id, idempotency_key)` as its uniqueness boundary.
- An approval cannot resume an unrelated run or cross tenant boundaries.
- Runs use durable graph checkpoints when a PostgreSQL checkpointer is configured. The local test implementation supplies an in-memory checkpointer-compatible store.
- All material state transitions append an audit event.

## Test Strategy

Tests are authored first and independently. They prove tenant isolation, duplicate-event idempotency, retrieval evidence scoping, approval interruption, approved resume, rejected no-side-effect behavior, and same-thread recovery. HTTP tests cover organization boundaries at the public API.

## Constraints

- Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, PostgreSQL, LangGraph, and pytest.
- Source code uses `ai_employee` naming only; no legacy platform API identifiers, models, endpoints, or import paths.
- No external model key is required for tests; deterministic policy logic makes the first workflow verifiable.
- Third-party dependency licenses remain in their original terms.
