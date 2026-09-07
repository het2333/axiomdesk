# Etheralia AI Employee

An independently authored B2B AI employee runtime for enterprise conversations.

The first release accepts normalized customer events, retrieves organization-scoped
knowledge, requires approval for follow-up actions, and resumes the original
LangGraph thread after an approval decision.

## Local development

```bash
uv sync --all-groups
uv run pytest -q
uv run ruff check src tests
uv run mypy src
```

## First-release HTTP API

Every endpoint requires `X-Organization-Id`.

- `POST /v1/conversation-events` accepts a normalized message event.
- `POST /v1/knowledge-documents` adds tenant-scoped source text.
- `GET /v1/runs/{run_id}` returns a run visible to the calling organization.
- `POST /v1/approvals/{approval_id}/decisions` resumes a pending run.

The initial channel boundary is an Enterprise WeChat adapter. It translates inbound
payloads into a domain event and does not perform network I/O.
