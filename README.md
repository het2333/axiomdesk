# AxiomDesk

> **Governed AI for B2B customer execution.**

AxiomDesk 是面向国内 B2B 企业的客服执行型 AI 平台。它不只生成一段客服回复，而是在企业知识、权限策略和人工审批的约束下完成真实工作：查证依据、规划下一步、请求授权、恢复原任务，并沉淀可审计结果。

## 目录

- [为什么使用 AxiomDesk](#为什么使用-axiomdesk)
- [核心能力](#核心能力)
- [执行闭环](#执行闭环)
- [架构](#架构)
- [已实现与规划](#已实现与规划)
- [快速开始](#快速开始)
- [API 概览](#api-概览)
- [适用场景](#适用场景)
- [部署与安全](#部署与安全)
- [开发](#开发)
- [路线图](#路线图)

## 为什么使用 AxiomDesk

客户问“交期多久”时，客服不该在文档、群聊和多个系统之间反复确认；客户说“请销售明天跟进”时，AI 也不该绕过审批直接创建任务。

AxiomDesk 将企业客服流程改造成可控制的执行闭环：

```text
客户消息
  → 检索当前企业的知识
  → 判断回复或业务动作
  → 自动执行 / 请求人工审批
  → 恢复同一任务并记录结果
```

| 普通 AI 回复 | AxiomDesk |
| --- | --- |
| 目标是生成一段话 | 目标是将客户问题推进到可执行结果 |
| 回答依据不可见 | 知识命中可作为回复证据 |
| 高风险动作依赖人工记忆 | 动作策略明确为自动、审批或禁止 |
| 审批后重新发起流程 | 从原 LangGraph 线程继续执行 |
| 重复消息可能造成重复动作 | 运行与工具调用都有幂等边界 |

## 核心能力

### 多轮执行与恢复

每次客户事件产生一个可追踪的 Agent Run。LangGraph 使用稳定 `thread_id` 保存上下文；任务被审批打断后，通过 `Command(resume=...)` 继续原图，而非新建一个不相关的会话。

### 租户级知识检索

知识文档与运行记录都绑定组织。检索先做组织过滤，再返回命中的文档片段；一个组织的数据不会出现在另一个组织的答案、审批或审计结果中。

### 受控工具调用

当前运行时区分低风险回复和需要审批的业务动作。每一个工具执行都带有幂等键，重复事件、网络重试或重复审批不会带来第二次副作用。

### 人工审批与审计

审批是工作流节点，而不是事后备注。审批人批准或拒绝后，平台记录决定、更新运行结果，并保留与该运行关联的审计事件。

### 渠道适配层

业务 Runtime 不绑定某个聊天渠道。企业微信 Adapter 将渠道消息标准化为 `ConversationEvent`，后续可用同一接口增加钉钉、飞书、网页或 CRM 事件入口。

## 执行闭环

```text
Inbound event
    │
    ▼
Tenant boundary ──→ Knowledge retrieval ──→ Action plan
                                              │
                         ┌────────────────────┴───────────────────┐
                         ▼                                        ▼
                    Safe reply                             Risky action
                         │                                        │
                         ▼                                        ▼
                      Complete                         Approval interrupt
                                                                  │
                                                        approved / rejected
                                                                  │
                                                                  ▼
                                                        Resume same thread
                                                                  │
                                                                  ▼
                                                     Idempotent tool + audit
```

## 架构

```text
Channel Adapter / REST API
            │
            ▼
      ConversationEvent
            │
            ▼
 FastAPI domain boundary
            │
    ┌───────┼──────────────────────────────────────────┐
    ▼       ▼                 ▼                         ▼
Tenant   LangGraph       Knowledge retrieval     Audit / tool ledger
policy   workflow        (organization scoped)   (idempotent)
```

| 层 | 当前技术选择 | 职责 |
| --- | --- | --- |
| API | FastAPI + Pydantic | 输入校验、组织边界、运行与审批接口 |
| Workflow | LangGraph | 检索、规划、审批中断、恢复与终止 |
| Domain | Python typed contracts | 事件、运行、审批、证据与审计模型 |
| Storage | In-memory baseline | 可重复测试的开发基线 |
| Production target | PostgreSQL + pgvector | 持久化运行、知识与向量检索 |

## 已实现与规划

### 当前已实现

- 组织隔离的消息、知识、运行和审批模型
- LangGraph 检索、计划、执行与中断恢复
- 回答证据与中文短语匹配检索
- 风险动作审批、同线程恢复与拒绝处理
- 运行幂等和工具副作用幂等
- 企业微信入站消息标准化 Adapter
- FastAPI 运行、知识库、审批与运行查询接口
- pytest、Ruff 与 mypy 自动验证

### 正在生产化

- PostgreSQL、Alembic 与 LangGraph Checkpoint
- 成员登录、管理员/操作员/审批员/审计员角色
- 企业微信真实回调验签、加密消息与主动发送
- CRM/ERP 连接器、报价/售后/跟进工具策略
- PDF、Word、Excel、WPS 文档知识库导入
- 自动化评测、监控指标和审计看板
- Docker Compose 私有化部署、模型路由和计费

> 规划能力不会被描述为已上线能力。真实企业微信、CRM/ERP 和模型接入仍需要客户提供凭据、回调域名及业务授权。

## 快速开始

### 环境要求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

### 安装与验证

```bash
git clone https://github.com/het2333/axiomdesk.git
cd axiomdesk
uv sync --all-groups
uv run pytest -q
uv run ruff check src tests
uv run mypy src
```

### 启动 API

```bash
uv run uvicorn ai_employee.api:create_app --factory --reload
```

开发基线使用 `X-Organization-Id` 表示组织。生产模式会使用成员令牌或经过验证的渠道配置，而不会信任客户端自报的组织标识。

### 添加知识文档

```bash
curl -X POST http://127.0.0.1:8000/v1/knowledge-documents \
  -H 'X-Organization-Id: acme' \
  -H 'Content-Type: application/json' \
  -d '{"id":"delivery-policy","content":"标准交期为 7 天。"}'
```

### 处理客户消息

```bash
curl -X POST http://127.0.0.1:8000/v1/conversation-events \
  -H 'X-Organization-Id: acme' \
  -H 'Content-Type: application/json' \
  -d '{"conversation_id":"c-1","customer_id":"u-1","message":"交期多久","idempotency_key":"m-1"}'
```

回复任务直接完成；含“跟进”的请求进入 `awaiting_approval`，由审批接口决定继续或拒绝。

## API 概览

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `POST` | `/v1/conversation-events` | 接收标准化客户消息，创建或复用运行 |
| `POST` | `/v1/knowledge-documents` | 添加当前组织可检索的知识文档 |
| `GET` | `/v1/runs/{run_id}` | 查询当前组织可见的运行结果 |
| `POST` | `/v1/approvals/{approval_id}/decisions` | 批准或拒绝高风险动作，并恢复原任务 |

## 适用场景

- **工业品与设备售后**：交期、备件、维修流程、销售跟进
- **B2B SaaS**：产品政策、技术支持、续费和客户成功协作
- **贸易与批发**：询盘分流、报价草稿、订单状态和回款跟进
- **企业服务**：标准服务答复、工单分派和人工确认的客户承诺

## 部署与安全

生产部署目标是私有化或专有云：API、PostgreSQL、Redis 和 Worker 通过容器编排部署；模型、渠道和业务系统凭据只从环境变量或密钥服务加载。

- 不在源码、日志或 API 响应中暴露渠道、模型或 CRM 密钥。
- LLM 不能自选任意 URL 或凭据；连接器使用管理员配置的白名单端点和类型化参数。
- 审批、策略修改、工具调用与结果都应写入审计记录。
- 组织成员只能访问本组织资源；审计员是只读角色。

## 开发

```bash
uv run pytest -q
uv run ruff check src tests
uv run mypy src
```

仓库使用测试优先方式维护关键行为，重点覆盖租户隔离、重复副作用、审批绕过、检索证据与同线程恢复。

## 路线图

1. **可用**：持久化、真实企业微信、成员与角色。
2. **可执行**：CRM/ERP 工具、报价/售后/跟进审批策略。
3. **可运营**：文件知识库、自动化评测、监控和审计看板。
4. **可销售**：私有化部署、国内模型路由、行业包和计费。

## License

[Apache-2.0](LICENSE)
