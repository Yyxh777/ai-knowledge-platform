## Why

当前系统缺少统一的会话管理能力，用户难以查看和继续历史对话，导致对话体验割裂且上下文复用困难。现在引入会话管理与历史存储能力，可以为后续的多轮对话、会话检索和运营分析打下基础。

## What Changes

- 新增会话管理能力：创建会话、列出会话、查询会话详情、删除会话。
- 新增历史消息持久化能力：按会话保存用户与助手消息，并支持按时间顺序查询。
- 对现有聊天接口进行兼容扩展：支持 `session_id` 透传，未提供时可自动创建会话。
- 增加基础校验与权限隔离：确保用户只能访问自己的会话与消息历史。

## Capabilities

### New Capabilities
- `session-management`: 覆盖会话生命周期管理与历史消息持久化、查询能力。

### Modified Capabilities
- 无。

## Impact

- 受影响代码：`api/chat.py`、`models/chat.py`、`service/*`、`utils/conversation_db.py`、`workflows/rag_graph.py`。
- 受影响 API：聊天相关接口新增/扩展 `session_id` 语义，增加会话查询与管理接口。
- 受影响存储：`conversations.db` 需要新增或完善会话与消息表结构及索引。
- 依赖与系统：主要使用现有 FastAPI + SQLite 能力，无需新增外部基础设施。
