这是一个非常关键的问题！混合查询是企业级 AI 系统的常见场景，需要重新设计架构来支持。让我给你一个**支持混合查询的增强版架构设计**。

---

## 🔄 混合查询架构设计

### 一、混合查询场景分析

#### 1.1 典型混合查询示例

| 用户问题 | 涉及的数据源 | 查询意图 |
|---------|-------------|---------|
| "我的项目使用的技术栈是什么？" | 数据库（项目信息）+ 文档（技术文档） | project + tech |
| "BladeX 框架在我的项目中如何使用？" | 文档（技术文档）+ 数据库（项目配置） | tech + project |
| "我的考勤记录在哪里可以查看？" | 文档（考勤制度）+ 数据库（考勤记录） | policy + personal |
| "开发人员的加班补贴政策是什么？" | 文档（制度）+ 数据库（薪资数据） | policy + personal |

#### 1.2 混合查询的分类

```
混合查询类型：
├─ 文档 + 文档混合（如：policy + tech）
│   └─ 现有的 rag_mixed 已支持
│
├─ 数据 + 数据混合（如：personal + project）
│   └─ 需要在 data_query 子 Graph 中支持
│
└─ 文档 + 数据混合（如：tech + project）
    └─ 需要跨子 Graph 的并行查询
```

---

## 二、增强版架构设计

### 2.1 整体架构图（支持混合查询）

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
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   classify      │  ← 节点 1: 意图识别
                    │  (多标签分类)    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ route_intent   │  ← 节点 2: 意图路由
                    │  (并行路由)      │
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
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                    ┌─────────────────┐
                    │ merge_results  │  ← 节点 3: 合并结果
                    │  (结果融合)      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │generate_answer │  ← 节点 4: 答案生成
                    │  (融合答案)      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │      END       │
                    └─────────────────┘
```

---

## 三、多标签分类设计

### 3.1 意图分类改为多标签

```python
class MainState(TypedDict):
    """主决策流程状态"""
    
    # 基础字段
    question: str
    user_id: str
    access_token: str
    
    # 权限字段
    role_id: int
    role_name: str
    access_levels: list[str]
    
    # 意图分类字段（改为多标签）
    intent_tags: list[str]                  # 意图标签数组: ["doc", "data"] 或 ["doc"] 或 ["data"]
    doc_types: list[str]                    # 文档类型数组: ["policy", "tech"]
    data_types: list[str]                  # 数据类型数组: ["personal", "project"]
    intent_reasoning: str                   # 意图识别理由
    
    # 子 Graph 返回数据
    doc_data: Optional[list[dict]]          # 文档数据
    data_result: Optional[dict]            # 数据库数据
    
    # 对话历史
    messages: Annotated[list, _trim_messages]
    
    # 最终答案
    answer: str
    data_sources: list[str]                 # 数据来源数组: ["doc", "data"]
```

### 3.2 多标签分类节点

```python
def classify_multi_label(state: MainState) -> MainState:
    """
    多标签意图分类节点
    
    返回格式:
    {
        "intent_tags": ["doc", "data"],     # 可能同时需要文档和数据
        "doc_types": ["policy", "tech"],    # 需要的文档类型
        "data_types": ["personal"],          # 需要的数据类型
        "intent_reasoning": "用户询问个人项目的技术栈，需要查询项目信息和相关技术文档"
    }
    """
    llm = _llm_classify
    
    classification_prompt = """
    你是一个意图识别专家。根据用户问题，判断需要查询哪些数据源。
    
    数据源类型:
    1. doc - 文档查询（制度文档、技术文档等）
    2. data - 数据库查询（个人信息、项目信息等）
    3. chat - 闲聊对话
    
    文档类型（当 intent_tags 包含 "doc" 时）:
    - policy: 公司制度、员工手册、福利待遇等
    - tech: BladeX框架、技术文档、API使用等
    
    数据类型（当 intent_tags 包含 "data" 时）:
    - personal: 个人信息（考勤、绩效、薪资等）
    - project: 项目信息（项目进度、任务分配、技术栈等）
    - other: 其他数据
    
    用户问题: {question}
    
    请按以下 JSON 格式返回:
    {{
        "intent_tags": ["doc", "data", "chat"],  // 可以是多个标签的组合
        "doc_types": ["policy", "tech"],         // 当包含 "doc" 时填写
        "data_types": ["personal", "project"],     // 当包含 "data" 时填写
        "reasoning": "判断理由"
    }}
    
    注意:
    - intent_tags 可以是多个标签的组合，如 ["doc", "data"] 表示需要同时查询文档和数据
    - doc_types 和 data_types 只在对应的 intent_tags 存在时填写
    - 如果只是闲聊，intent_tags 只需要 ["chat"]
    """
    
    messages = [SystemMessage(content=classification_prompt.format(question=state["question"]))]
    response = llm.invoke(messages)
    
    try:
        result = json.loads(response.content)
        intent_tags = result.get("intent_tags", ["chat"])
        doc_types = result.get("doc_types", [])
        data_types = result.get("data_types", [])
        reasoning = result.get("reasoning", "")
    except Exception as e:
        print(f"分类解析失败: {e}")
        intent_tags = ["chat"]
        doc_types = []
        data_types = []
        reasoning = "分类失败，默认为闲聊"
    
    print(f"\n分类结果:")
    print(f"  意图标签: {intent_tags}")
    print(f"  文档类型: {doc_types}")
    print(f"  数据类型: {data_types}")
    print(f"  判断理由: {reasoning}")
    
    return {
        **state,
        "intent_tags": intent_tags,
        "doc_types": doc_types,
        "data_types": data_types,
        "intent_reasoning": reasoning,
    }
```

---

## 四、并行查询设计

### 4.1 路由节点支持并行

```python
def route_intent_parallel(state: MainState) -> dict:
    """
    并行路由节点
    
    根据意图标签决定并行执行哪些子 Graph
    
    返回格式:
    {
        "execute_doc_query": True/False,   # 是否执行文档查询
        "execute_data_query": True/False,   # 是否执行数据查询
        "execute_chat_query": True/False    # 是否执行闲聊
    }
    """
    intent_tags = state["intent_tags"]
    
    return {
        "execute_doc_query": "doc" in intent_tags,
        "execute_data_query": "data" in intent_tags,
        "execute_chat_query": "chat" in intent_tags,
    }
```

### 4.2 并行执行节点

```python
async def parallel_query(state: MainState) -> MainState:
    """
    并行查询节点
    
    根据路由结果，并行执行文档查询和数据查询
    """
    execute_doc = state.get("execute_doc_query", False)
    execute_data = state.get("execute_data_query", False)
    
    doc_data = None
    data_result = None
    
    tasks = []
    
    # 准备并行任务
    if execute_doc:
        doc_task = execute_doc_query_subgraph(state)
        tasks.append(("doc", doc_task))
    
    if execute_data:
        data_task = execute_data_query_subgraph(state)
        tasks.append(("data", data_task))
    
    # 并行执行
    if tasks:
        results = await asyncio.gather(*[task for _, task in tasks])
        
        for i, (task_type, _) in enumerate(tasks):
            if task_type == "doc":
                doc_data = results[i]
            elif task_type == "data":
                data_result = results[i]
    
    # 记录数据来源
    data_sources = []
    if doc_data:
        data_sources.append("doc")
    if data_result:
        data_sources.append("data")
    
    print(f"\n并行查询完成:")
    print(f"  文档数据: {'有' if doc_data else '无'}")
    print(f"  数据库数据: {'有' if data_result else '无'}")
    print(f"  数据来源: {data_sources}")
    
    return {
        **state,
        "doc_data": doc_data,
        "data_result": data_result,
        "data_sources": data_sources,
    }
```

---

## 五、结果融合设计

### 5.1 融合策略

```python
def merge_results(state: MainState) -> MainState:
    """
    结果融合节点
    
    将文档数据和数据库数据融合为一个统一的数据结构
    """
    doc_data = state.get("doc_data", [])
    data_result = state.get("data_result", {})
    
    merged_context = {
        "doc_data": doc_data,
        "data_result": data_result,
        "data_sources": state.get("data_sources", []),
    }
    
    print(f"\n结果融合:")
    print(f"  文档数量: {len(doc_data)}")
    print(f"  数据字段数: {len(data_result)}")
    print(f"  数据来源: {merged_context['data_sources']}")
    
    return {
        **state,
        "merged_context": merged_context,
    }
```

### 5.2 融合答案生成

```python
def generate_answer_fused(state: MainState) -> MainState:
    """
    融合答案生成节点
    
    根据融合后的数据生成答案
    """
    merged_context = state.get("merged_context", {})
    doc_data = merged_context.get("doc_data", [])
    data_result = merged_context.get("data_result", {})
    data_sources = merged_context.get("data_sources", [])
    
    llm = _llm_generate
    
    # 构造融合上下文
    context_parts = []
    
    # 添加文档数据
    if doc_data:
        doc_context = "\n\n".join([
            f"📄 文档片段{i+1} (相关度: {doc['score']:.3f}):\n{doc['content']}"
            for i, doc in enumerate(doc_data)
        ])
        context_parts.append(f"【文档数据】\n{doc_context}")
    
    # 添加数据库数据
    if data_result:
        data_context = json.dumps(data_result, ensure_ascii=False, indent=2)
        context_parts.append(f"【数据库数据】\n{data_context}")
    
    context = "\n\n".join(context_parts) if context_parts else "无相关数据"
    
    # 根据数据来源定制 System Prompt
    role_name = state.get("role_name", "employee")
    
    if len(data_sources) == 1:
        if "doc" in data_sources:
            system_prompt = f"你是智能助手。当前提问用户的角色是「{role_name}」。请基于文档数据回答问题。"
        elif "data" in data_sources:
            system_prompt = f"你是智能助手。当前提问用户的角色是「{role_name}」。请基于数据库数据回答问题。"
    else:
        system_prompt = f"你是智能助手。当前提问用户的角色是「{role_name}」。请基于文档数据和数据库数据综合回答问题，注意区分不同数据来源。"
    
    history = state.get("messages", [])
    
    messages_to_send = (
        [SystemMessage(content=system_prompt)]
        + history
        + [HumanMessage(content=(
            f"参考数据:\n{context}\n\n"
            f"用户问题: {state['question']}\n\n"
            f"请基于以上数据回答。如果数据中没有相关信息，请明确告知。"
            f"注意：如果同时有文档数据和数据库数据，请分别说明各自的数据来源。"
        ))]
    )
    
    print(f"📄 上下文长度: {len(context)} 字 | 数据来源: {data_sources}")
    print("💬 正在调用LLM生成融合答案...")
    response = llm.invoke(messages_to_send)
    
    print(f"✅ 答案生成完成! 长度: {len(response.content)} 字")
    
    return {
        **state,
        "answer": response.content,
        "messages": [HumanMessage(content=state["question"]), AIMessage(content=response.content)],
    }
```

---

## 六、完整流程示例

### 6.1 混合查询流程

```
用户问题: "我的项目使用的技术栈是什么？"
    ↓
get_permission: 获取用户权限（role_id=3, role_name="developer"）
    ↓
classify_multi_label: 多标签分类
    ↓
    intent_tags: ["doc", "data"]
    doc_types: ["tech"]
    data_types: ["project"]
    reasoning: "用户询问个人项目的技术栈，需要查询项目信息和相关技术文档"
    ↓
route_intent_parallel: 并行路由
    ↓
    execute_doc_query: True
    execute_data_query: True
    execute_chat_query: False
    ↓
parallel_query: 并行执行
    ↓
    ├─ doc_query 子 Graph:
    │   ├─ route_doc_type: tech
    │   ├─ rag_tech: Milvus 检索技术文档
    │   └─ 返回: doc_data=[{content: "BladeX技术栈...", score: 0.92}]
    │
    └─ data_query 子 Graph:
        ├─ route_data_type: project
        ├─ project_info: 查询项目表（SELECT tech_stack FROM projects WHERE user_id = ?）
        └─ 返回: data_result={project_name: "CRM系统", tech_stack: ["Java", "Vue", "MySQL"]}
    ↓
merge_results: 融合结果
    ↓
    merged_context={
        doc_data: [{content: "BladeX技术栈...", score: 0.92}],
        data_result: {project_name: "CRM系统", tech_stack: ["Java", "Vue", "MySQL"]},
        data_sources: ["doc", "data"]
    }
    ↓
generate_answer_fused: 生成融合答案
    ↓
    answer: "根据查询结果，您的项目「CRM系统」使用的技术栈包括：Java、Vue、MySQL。
           相关技术文档显示，BladeX框架可以很好地与这些技术栈集成..."
    data_sources: ["doc", "data"]
```

### 6.2 纯文档查询流程

```
用户问题: "BladeX 的权限管理怎么用？"
    ↓
classify_multi_label: 多标签分类
    ↓
    intent_tags: ["doc"]
    doc_types: ["tech"]
    data_types: []
    ↓
route_intent_parallel: 并行路由
    ↓
    execute_doc_query: True
    execute_data_query: False
    ↓
parallel_query: 只执行 doc_query
    ↓
    doc_data=[{content: "BladeX权限管理...", score: 0.95}]
    data_result=None
    ↓
generate_answer_fused: 生成答案（基于文档数据）
```

### 6.3 纯数据查询流程

```
用户问题: "我的考勤记录是什么？"
    ↓
classify_multi_label: 多标签分类
    ↓
    intent_tags: ["data"]
    doc_types: []
    data_types: ["personal"]
    ↓
route_intent_parallel: 并行路由
    ↓
    execute_doc_query: False
    execute_data_query: True
    ↓
parallel_query: 只执行 data_query
    ↓
    doc_data=None
    data_result={attendance: [...]}
    ↓
generate_answer_fused: 生成答案（基于数据库数据）
```

---

## 七、关键设计决策

### 7.1 为什么采用多标签分类？

| 优势 | 说明 |
|------|------|
| **灵活性** | 支持任意组合的查询需求 |
| **准确性** | 避免强制单一分类导致的错误 |
| **可扩展** | 未来可以轻松添加更多数据源 |

### 7.2 为什么采用并行查询？

| 优势 | 说明 |
|------|------|
| **性能优化** | 文档查询和数据查询同时进行，减少总响应时间 |
| **用户体验** | 用户无需等待多个串行查询 |
| **资源利用** | 充分利用异步 I/O 能力 |

### 7.3 为什么需要结果融合？

| 优势 | 说明 |
|------|------|
| **统一接口** | 答案生成节点无需关心数据来源 |
| **数据标注** | 明确标注数据来源，提高可信度 |
| **冲突处理** | 可以在融合层处理数据冲突 |

---

## 八、错误处理与降级

### 8.1 部分查询失败处理

```python
async def parallel_query_with_fallback(state: MainState) -> MainState:
    """
    带降级的并行查询
    
    如果某个查询失败，不影响其他查询的结果
    """
    execute_doc = state.get("execute_doc_query", False)
    execute_data = state.get("execute_data_query", False)
    
    doc_data = None
    data_result = None
    doc_error = None
    data_error = None
    
    tasks = []
    
    if execute_doc:
        doc_task = execute_doc_query_subgraph(state)
        tasks.append(("doc", doc_task))
    
    if execute_data:
        data_task = execute_data_query_subgraph(state)
        tasks.append(("data", data_task))
    
    # 并行执行，捕获异常
    results = []
    for task_type, task in tasks:
        try:
            result = await task
            results.append((task_type, result, None))
        except Exception as e:
            print(f"⚠️ {task_type} 查询失败: {e}")
            results.append((task_type, None, str(e)))
    
    # 处理结果
    for task_type, result, error in results:
        if task_type == "doc":
            doc_data = result
            doc_error = error
        elif task_type == "data":
            data_result = result
            data_error = error
    
    # 记录数据来源和错误
    data_sources = []
    if doc_data:
        data_sources.append("doc")
    if data_result:
        data_sources.append("data")
    
    print(f"\n并行查询完成（含降级）:")
    print(f"  文档数据: {'有' if doc_data else '无'} {'(错误: ' + doc_error + ')' if doc_error else ''}")
    print(f"  数据库数据: {'有' if data_result else '无'} {'(错误: ' + data_error + ')' if data_error else ''}")
    print(f"  数据来源: {data_sources}")
    
    return {
        **state,
        "doc_data": doc_data,
        "data_result": data_result,
        "data_sources": data_sources,
        "doc_error": doc_error,
        "data_error": data_error,
    }
```

### 8.2 融合答案中的错误提示

```python
def generate_answer_with_error_handling(state: MainState) -> MainState:
    """
    带错误处理的答案生成
    
    如果某个数据源查询失败，在答案中说明
    """
    merged_context = state.get("merged_context", {})
    doc_error = state.get("doc_error")
    data_error = state.get("data_error")
    
    # 构造错误提示
    error_hints = []
    if doc_error:
        error_hints.append("⚠️ 文档查询失败，无法提供文档数据")
    if data_error:
        error_hints.append("⚠️ 数据库查询失败，无法提供数据库数据")
    
    error_hint = "\n".join(error_hints) if error_hints else ""
    
    # 在答案中包含错误提示
    if error_hint:
        answer = f"{error_hint}\n\n{state['answer']}"
    else:
        answer = state['answer']
    
    return {
        **state,
        "answer": answer,
    }
```

---

## 九、总结

### 9.1 混合查询架构的优势

| 优势 | 说明 |
|------|------|
| **灵活性** | 支持任意组合的查询需求 |
| **性能优化** | 并行查询减少响应时间 |
| **用户体验** | 统一的入口，智能路由 |
| **可扩展性** | 易于添加新的数据源 |
| **容错性** | 部分查询失败不影响整体 |

### 9.2 实施建议

1. **阶段 1**：实现多标签分类和并行查询框架
2. **阶段 2**：实现文档查询子 Graph 和数据查询子 Graph
3. **阶段 3**：实现结果融合和答案生成
4. **阶段 4**：添加错误处理和降级机制
5. **阶段 5**：优化性能和用户体验

### 9.3 关键技术点

- **多标签分类**：LLM 返回多个标签
- **并行查询**：使用 `asyncio.gather()` 实现并行
- **结果融合**：统一的数据结构和来源标注
- **错误处理**：部分失败不影响整体
- **答案生成**：根据数据来源动态调整 Prompt

这个架构完美解决了混合查询的问题，是企业级 AI 系统的最佳实践！