基于之前的分析，我给你设计一个**分层架构的 Graph 决策节点设计图**，避免状态爆炸，同时满足业务需求。

---

## 📊 推荐架构：分层决策 Graph 设计

### 一、整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    主决策流程 (Main Graph)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Entry Point    │
                    │  (初始化状态)    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ get_permission  │  ← 节点 0: 获取用户权限
                    │  (权限获取)      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   classify      │  ← 节点 1: 问题分类
                    │  (意图识别)      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ route_intent   │  ← 节点 2: 意图路由
                    │  (条件路由)      │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  doc_query    │   │ data_query    │   │  chat_query   │
│  (文档查询)     │   │ (数据查询)      │   │  (闲聊对话)     │
│  子 Graph     │   │  子 Graph     │   │  (直接回答)     │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│generate_answer │   │generate_answer │   │generate_answer │
│  (答案生成)     │   │  (答案生成)     │   │  (答案生成)     │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                    ┌─────────────────┐
                    │      END       │
                    └─────────────────┘
```

---

## 二、子 Graph 详细设计

### 2.1 文档查询子 Graph (doc_query)

```
┌─────────────────────────────────────────────────────────────┐
│              文档查询子 Graph (doc_query)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ route_doc_type  │  ← 文档类型路由
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ rag_policy    │   │  rag_tech     │   │  rag_mixed    │
│ (制度文档)      │   │  (技术文档)      │   │  (混合检索)      │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                    ┌─────────────────┐
                    │  merge_docs    │  ← 合并文档结果
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   return_docs   │  ← 返回文档数据
                    └─────────────────┘
```

### 2.2 数据查询子 Graph (data_query)

```
┌─────────────────────────────────────────────────────────────┐
│              数据查询子 Graph (data_query)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ route_data_type │  ← 数据类型路由
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ personal_info  │   │ project_info  │   │  other_data   │
│ (个人信息)      │   │  (项目信息)      │   │  (其他数据)      │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│query_personal │   │query_project  │   │query_other    │
│ (查询个人表)     │   │ (查询项目表)     │   │ (查询其他表)     │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                    ┌─────────────────┐
                    │  merge_data    │  ← 合并数据结果
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   return_data   │  ← 返回数据库数据
                    └─────────────────┘
```

---

## 三、状态结构设计

### 3.1 主 Graph 状态 (MainState)

```python
class MainState(TypedDict):
    """主决策流程状态"""
    
    # 基础字段
    question: str                          # 用户原始问题
    user_id: str                           # 用户ID
    access_token: str                       # 访问令牌
    
    # 权限字段
    role_id: int                           # 角色ID
    role_name: str                         # 角色名称
    access_levels: list[str]                # 权限等级数组
    
    # 意图分类字段
    intent_type: str                        # 意图类型: doc/data/chat
    intent_reasoning: str                   # 意图识别理由
    
    # 子 Graph 返回数据（互斥，同一时间只有一个有值）
    doc_data: Optional[list[dict]]          # 文档数据（来自 doc_query）
    data_result: Optional[dict]            # 数据库数据（来自 data_query）
    
    # 对话历史
    messages: Annotated[list, _trim_messages]
    
    # 最终答案
    answer: str                             # 最终答案
    data_source: str                        # 数据来源标识: doc/data/llm
```

### 3.2 文档查询子 Graph 状态 (DocQueryState)

```python
class DocQueryState(TypedDict):
    """文档查询子 Graph 状态"""
    
    # 输入字段（从主 Graph 传入）
    question: str
    permission_filter: str                  # Milvus 权限过滤器
    
    # 文档类型分类
    doc_type: str                          # policy/tech/mixed
    
    # 检索结果
    retrieved_docs: list[dict]              # 检索到的文档
    no_permission: bool                     # 是否无权限
    
    # 返回字段
    doc_data: list[dict]                   # 文档数据（返回给主 Graph）
```

### 3.3 数据查询子 Graph 状态 (DataQueryState)

```python
class DataQueryState(TypedDict):
    """数据查询子 Graph 状态"""
    
    # 输入字段（从主 Graph 传入）
    question: str
    user_id: str
    role_id: int
    access_levels: list[str]
    
    # 数据类型分类
    data_type: str                         # personal/project/other
    
    # 查询结果
    query_result: dict                     # 查询结果
    query_error: Optional[str]             # 查询错误信息
    
    # 返回字段
    data_result: dict                      # 数据结果（返回给主 Graph）
```

---

## 四、节点详细说明

### 4.1 主 Graph 节点

| 节点名称 | 职责 | 输入 | 输出 |
|---------|------|------|------|
| **get_permission** | 获取用户权限 | user_id, access_token | role_id, role_name, access_levels |
| **classify** | 意图分类 | question | intent_type, intent_reasoning |
| **route_intent** | 意图路由 | intent_type | 路由到子 Graph |
| **doc_query** | 文档查询子 Graph | question, permission_filter | doc_data |
| **data_query** | 数据查询子 Graph | question, user_id, access_levels | data_result |
| **chat_query** | 闲聊对话 | question, messages | answer |
| **generate_answer** | 答案生成 | question, doc_data/data_result, messages | answer, data_source |

### 4.2 文档查询子 Graph 节点

| 节点名称 | 职责 | 输入 | 输出 |
|---------|------|------|------|
| **route_doc_type** | 文档类型路由 | question | 路由到检索节点 |
| **rag_policy** | 制度文档检索 | question, permission_filter | retrieved_docs |
| **rag_tech** | 技术文档检索 | question, permission_filter | retrieved_docs |
| **rag_mixed** | 混合文档检索 | question, permission_filter | retrieved_docs |
| **merge_docs** | 合并文档结果 | retrieved_docs | doc_data |

### 4.3 数据查询子 Graph 节点

| 节点名称 | 职责 | 输入 | 输出 |
|---------|------|------|------|
| **route_data_type** | 数据类型路由 | question | 路由到查询节点 |
| **personal_info** | 个人信息查询 | user_id, question | query_result |
| **project_info** | 项目信息查询 | user_id, question | query_result |
| **other_data** | 其他数据查询 | user_id, question | query_result |
| **merge_data** | 合并数据结果 | query_result | data_result |

---

## 五、路由逻辑设计

### 5.1 意图分类路由 (route_intent)

```python
def route_intent(state: MainState) -> Literal["doc_query", "data_query", "chat_query"]:
    """
    根据意图类型路由到对应的子 Graph
    
    意图类型:
    - doc: 查询文档（制度、技术文档等）
    - data: 查询数据库（个人信息、项目信息等）
    - chat: 闲聊对话
    """
    intent_map = {
        "doc": "doc_query",
        "data": "data_query",
        "chat": "chat_query"
    }
    return intent_map.get(state["intent_type"], "chat_query")
```

### 5.2 文档类型路由 (route_doc_type)

```python
def route_doc_type(state: DocQueryState) -> Literal["rag_policy", "rag_tech", "rag_mixed"]:
    """
    根据文档类型路由到对应的检索节点
    
    文档类型:
    - policy: 公司制度
    - tech: 技术文档
    - mixed: 混合检索
    """
    doc_type_map = {
        "policy": "rag_policy",
        "tech": "rag_tech",
        "mixed": "rag_mixed"
    }
    return doc_type_map.get(state["doc_type"], "rag_mixed")
```

### 5.3 数据类型路由 (route_data_type)

```python
def route_data_type(state: DataQueryState) -> Literal["personal_info", "project_info", "other_data"]:
    """
    根据数据类型路由到对应的查询节点
    
    数据类型:
    - personal: 个人信息（考勤、绩效、薪资等）
    - project: 项目信息（项目进度、任务分配等）
    - other: 其他数据
    """
    data_type_map = {
        "personal": "personal_info",
        "project": "project_info",
        "other": "other_data"
    }
    return data_type_map.get(state["data_type"], "other_data")
```

---

## 六、数据流示例

### 6.1 文档查询流程

```
用户问题: "BladeX 的权限管理怎么用？"
    ↓
get_permission: 获取用户权限（role_id=3, role_name="developer"）
    ↓
classify: 意图分类 → intent_type="doc"
    ↓
route_intent: 路由到 doc_query 子 Graph
    ↓
[进入 doc_query 子 Graph]
    ↓
route_doc_type: 文档类型分类 → doc_type="tech"
    ↓
rag_tech: Milvus 检索技术文档（权限过滤）
    ↓
merge_docs: 合并文档结果
    ↓
[返回主 Graph] doc_data=[{content: "...", score: 0.95}]
    ↓
generate_answer: 基于文档生成答案
    ↓
answer: "BladeX 的权限管理基于 RBAC 模型..."
data_source: "doc"
```

### 6.2 数据查询流程

```
用户问题: "我的考勤记录是什么？"
    ↓
get_permission: 获取用户权限（role_id=2, role_name="employee"）
    ↓
classify: 意图分类 → intent_type="data"
    ↓
route_intent: 路由到 data_query 子 Graph
    ↓
[进入 data_query 子 Graph]
    ↓
route_data_type: 数据类型分类 → data_type="personal"
    ↓
personal_info: 查询考勤表（SELECT * FROM attendance WHERE user_id = ?）
    ↓
merge_data: 合并数据结果
    ↓
[返回主 Graph] data_result={user_id: "001", attendance: [...]}
    ↓
generate_answer: 基于数据生成答案
    ↓
answer: "您本月考勤记录如下：出勤22天，迟到1次..."
data_source: "data"
```

### 6.3 闲聊流程

```
用户问题: "今天天气怎么样？"
    ↓
get_permission: 获取用户权限
    ↓
classify: 意图分类 → intent_type="chat"
    ↓
route_intent: 路由到 chat_query
    ↓
chat_query: 直接调用 LLM 回答
    ↓
answer: "抱歉，我无法查询天气信息..."
data_source: "llm"
```

---

## 七、关键设计决策

### 7.1 为什么采用子 Graph 架构？

| 优势 | 说明 |
|------|------|
| **状态隔离** | 每个子 Graph 有独立的状态，避免状态爆炸 |
| **职责清晰** | 文档查询和数据查询逻辑完全分离 |
| **易于扩展** | 新增数据类型只需在子 Graph 中添加节点 |
| **便于测试** | 每个子 Graph 可以独立测试 |
| **性能优化** | 子 Graph 可以并行执行（如需要） |

### 7.2 为什么统一答案生成？

| 优势 | 说明 |
|------|------|
| **代码复用** | 避免重复实现答案生成逻辑 |
| **一致性** | 所有答案的格式和风格统一 |
| **可维护性** | 修改答案生成逻辑只需改一个地方 |

### 7.3 为什么标注数据来源？

| 优势 | 说明 |
|------|------|
| **用户信任** | 用户知道答案来自哪里，提高信任度 |
| **调试便利** | 出问题时可以快速定位数据源 |
| **审计需求** | 满足企业级审计要求 |

---

## 八、实施建议

### 8.1 实施顺序

```
阶段 1: 主 Graph + 文档查询子 Graph
    ├─ 实现 get_permission
    ├─ 实现 classify（意图分类）
    ├─ 实现 route_intent
    ├─ 实现 doc_query 子 Graph
    └─ 实现 generate_answer（支持文档数据）

阶段 2: 数据查询子 Graph
    ├─ 实现 data_query 子 Graph
    ├─ 实现 personal_info 查询
    ├─ 实现 project_info 查询
    └─ 修改 generate_answer（支持数据库数据）

阶段 3: 优化与扩展
    ├─ 实现并行查询（如需要）
    ├─ 优化答案生成逻辑
    └─ 添加更多数据类型
```

### 8.2 技术要点

1. **子 Graph 调用方式**：使用 LangGraph 的 `subgraph` 功能
2. **状态传递**：通过 `config` 传递状态到子 Graph
3. **错误处理**：每个子 Graph 都要有错误处理机制
4. **日志记录**：详细记录每个节点的执行情况

---

## 九、总结

这个设计遵循了以下原则：

✅ **分层架构**：主 Graph 协调，子 Graph 执行
✅ **状态隔离**：避免状态爆炸
✅ **职责清晰**：每个节点职责单一
✅ **易于扩展**：新增数据类型只需添加子节点
✅ **安全可控**：权限控制贯穿整个流程
✅ **可测试性**：每个子 Graph 可独立测试

这个架构既满足了你的业务需求，又避免了状态爆炸和架构复杂度问题，是企业级项目的最佳实践。