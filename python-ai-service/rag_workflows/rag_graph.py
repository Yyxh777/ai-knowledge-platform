from typing import TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pymilvus import MilvusClient
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.llms.tongyi import Tongyi
from langgraph.checkpoint.memory import InMemorySaver
from config import (
    DASHSCOPE_API_KEY,
    MILVUS_URI,
    MILVUS_COLLECTION_NAME,
    JAVA_SERVICE_URL,
    JAVA_CLIENT_CREDENTIALS,
    JAVA_REQUESTED_WITH,
    JAVA_SERVICE_TIMEOUT,
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
)
import operator
import json
import httpx
import pymysql
import requests
from pymysql.cursors import DictCursor
from langchain.agents import create_agent

# 文档类型与中文名映射(与 document_service 存入Milvus的 type 字段值一致)
DOC_TYPE_DISPLAY = {
    "policy": "制度类",
    "tech": "技术文档",
}

# ── 模块级单例：进程启动时初始化一次，所有节点共享，避免每次请求重复建连接 ──────────
# LLM：分类节点用 Tongyi（旧版接口，返回字符串），生成节点用 ChatOpenAI（支持流式事件）
_llm_classify = ChatOpenAI(model="qwen-plus", temperature=0)
# streaming=True 且节点内用 .stream() 拼接，上层 graph.astream_events 才能收到 on_chat_model_stream（打字机效果）
_llm_generate = ChatOpenAI(model="qwen-plus", temperature=0.7, streaming=True)
_llm_direct = ChatOpenAI(
    model="qwen-plus",
    temperature=0.9,
    streaming=True,
    extra_body={"enable_search": True},
)
# Embeddings：向量化查询语句，DashScope text-embedding-v4 输出 1024 维
_embeddings = DashScopeEmbeddings(model="text-embedding-v4")
# Milvus：MilvusClient 内部维护连接池，单实例多线程安全
_milvus_client = MilvusClient(uri=MILVUS_URI)
# Agent LLM：用于个人信息检索的工具调用
_llm_agent = ChatOpenAI(model="qwen-plus", temperature=0)

# ────────────────────────────────────────────────────────────────────────────────


def _stream_collect_text(llm: ChatOpenAI, messages: list, config: RunnableConfig | None) -> str:
    """
    同步流式调用 ChatOpenAI，拼接完整文本。

    必须用 stream 而非 invoke：invoke 会一次返回整段，LangGraph astream_events 不会出现
    on_chat_model_stream，前端只能收到整条答案。
    传入 config 以便 token 流挂到当前 Graph run，rag_service 才能收到 on_chat_model_stream。
    """
    parts: list[str] = []
    stream_iter = llm.stream(messages, config=config) if config is not None else llm.stream(messages)
    for chunk in stream_iter:
        c = getattr(chunk, "content", None)
        if not c:
            continue
        if isinstance(c, str):
            parts.append(c)
        elif isinstance(c, list):
            for block in c:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text") or "")
                elif isinstance(block, str):
                    parts.append(block)
    return "".join(parts)


BASE = "http://127.0.0.1:3210"
@tool
def web_search(query: str, limit: int = 5):
    """
    联网搜索，当用户需要查询最新信息时，请调用该函数。
    Args:
        query: 查询关键词
        limit: 返回结果数量，默认5条
    Returns:
        JSON 字符串，格式为：
        {
            "status": "ok",
            "data": {
                "query": "",
                "engines": [
                    "bing"
                ],
                "totalResults": 5,
                "results": [
                    {
                        "title": "",
                        "url": "",
                        "description": "",
                        "source": "",
                        "engine": ""
                    }
                ],
                "partialFailures": []
            },
            "error": null,
            "hint": null
        }
    """
    r = requests.post(f"{BASE}/search", json={"query": query, "limit": limit}, timeout=30)
    r.raise_for_status()
    r_json =  r.json()
    print(f"【web_search】r_json={r_json}")
    return r_json

# ── SQL 查询工具────────────
@tool
def query_mysql(sql: str) -> str:
    """

    当需要进行查询用户个人信息且通过数据库查询时，请调用该函数。
    该函数用于在指定MySQL服务器上运行一段SQL代码，完成数据查询相关工作，
    并且当前函数是使用pymsql连接MySQL数据库。
    本函数只负责运行SQL代码并进行数据查询

    执行 MySQL 查询并返回结果。

    Args:
        sql: 字符串形式的SQL查询语句，用于执行对MySQL中aikp数据库中各张表进行查询，并获得各表中的各类相关信息（仅支持 SELECT）

    Returns:
        查询结果的 JSON 字符串

    注意：
        - 只能执行 SELECT 查询，禁止 INSERT/UPDATE/DELETE
        - 查询 数据库 时必须在 WHERE 中包含当前 user_id，确保仅查本人数据
        - 返回结果最多 100 条
    """
    print(f"【query_mysql】sql={sql}")
    sql_stripped = sql.strip().upper()
    if not sql_stripped.startswith("SELECT"):
        return json.dumps({"error": "只允许执行 SELECT 查询"}, ensure_ascii=False)

    conn = None
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST,
            port=int(MYSQL_PORT),
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            charset="utf8mb4",
            cursorclass=DictCursor,
        )
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchmany(100)
            result = [dict(row) for row in rows]
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": f"查询失败: {str(e)}"}, ensure_ascii=False)
    finally:
        if conn:
            conn.close()


# 绑定工具到 Agent LLM
_tools = [query_mysql]
# _llm_with_tools = _llm_agent.bind_tools(_tools)
_tool_agent = create_agent(_llm_agent,tools=[query_mysql])
_web_search_agent = create_agent(_llm_direct,tools=[web_search])

# 对话历史最大保留轮数（每轮 = 1 条 HumanMessage + 1 条 AIMessage）
# 同时控制 checkpoint 中 messages 通道上限与 LLM 上下文窗口，两者保持一致
MAX_HISTORY_TURNS = 10
_MAX_STORED = MAX_HISTORY_TURNS * 2  # checkpoint 里最多保留这么多条消息
# 个人信息节点：注入到 Agent 的最近消息条数（用于多轮追问，如「我的部门呢」）
# 个人信息查询通过工具调用，故历史消息条数可以适当减少，避免上下文过长，影响模型理解
PERSONAL_INFO_HISTORY_MESSAGES = 6


def _trim_messages(existing: list, new: list) -> list:
    """
    有界对话历史 Reducer。

    operator.add 会无限追加，导致 checkpoint 中 messages 持续膨胀。
    此 Reducer 在追加新消息的同时丢弃超出上限的旧消息，
    确保 checkpoint 里永远只存最近 N 轮，存储量恒定。
    """
    return (existing + new)[-_MAX_STORED:]


# 1. 定义状态结构
class AgentState(TypedDict):
    """决策流的状态"""

    # 对话历史：有界 Reducer，checkpoint 存储量恒定（最多 MAX_HISTORY_TURNS 轮）
    messages: Annotated[list, _trim_messages]

    # 入参字段
    question: str  # 用户原始问题
    # 权限相关字段
    user_id: str  # 用户ID,由API层调用时传入
    role_id: int  # Java服务返回的角色ID
    role_name: str  # 角色名称,如 developer/hr/admin

    # 图中产生的字段
    question_type: str  # 分类结果: company_policy/tech_docs/general/mixed/personal_info
    retrieved_docs: list[dict]  # 检索到的文档
    reasoning: str  # 分类推理过程(用于调试)
    access_levels: list[str]  # Java服务返回的权限level数组,如 ["public","internal"]
    permission_filter: str  # 翻译成Milvus的filter表达式
    no_permission: bool  # True=文档存在但无权限; False=文档不存在或有权限
    # 个人信息相关字段
    personal_data: dict  # 从MySQL查询到的个人数据

    # 出参
    answer: str  # 最终答案


# 节点0：获取用户角色与权限
def get_user_permission(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    调用Java服务获取当前用户的权限等级数组,
    将 access_levels 翻译成 Milvus filter 表达式存入 state。

    Java服务接口:
        GET http://localhost:8081/level/getByUser
        Headers:
            - Blade-Requested-With: BladeHttpRequest
            - Authorization: Basic c2FiZXIzOnNhYmVyM19zZWNyZXQ=
            - Blade-Auth: bearer {access_token}
        Response:
        {
            "code": 200,
            "success": true,
            "data": ["public", "tech", "policy"],
            "msg": "操作成功"
        }
    """
    print(f"【get_permission】user_id={state['user_id']}")

    access_levels = ["public"]  # 兜底：最低权限（fail-secure 原则）

    # 从 LangGraph config 中取 access_token
    access_token = (config or {}).get("configurable", {}).get("access_token", "")

    # ── Early return：没有 token 直接降级，不发起无意义的网络请求 ──────────────
    # 设计原则：
    #   1. token 验证已在 API 层（WebSocket 握手时）完成，正常流程下此处必有 token
    #   2. 若真的缺失 token（异常路径），调用 Java 服务只会收到 401，
    #      多一次 I/O 换来的结果与直接降级完全一致，徒增延迟和错误日志
    #   3. 提前返回使代码逻辑清晰：有 token → 请求权限；无 token → 最低权限
    if not access_token:
        pass
    else:
        try:
            response = httpx.get(
                f"{JAVA_SERVICE_URL}/level/getByUser",
                headers={
                    "Blade-Auth": f"bearer {access_token}",
                    "Authorization": JAVA_CLIENT_CREDENTIALS,
                    "Blade-Requested-With": JAVA_REQUESTED_WITH,
                },
                timeout=JAVA_SERVICE_TIMEOUT,
            )
            response.raise_for_status()
            result = response.json()

            if result.get("success") and result.get("code") == 200:
                access_levels = result.get("data", ["public"])
            else:
                pass

        except httpx.TimeoutException:
            pass
        except httpx.HTTPStatusError as e:
            _ = e
        except Exception as e:
            _ = e

    print(f"【get_permission】role={state['role_name']} levels={access_levels}")

    # 将 access_levels 翻译成 Milvus filter 字符串
    # 例: ["public","internal"] → access_level in ["public","internal"]
    levels_quoted = ",".join(f'"{lv}"' for lv in access_levels)
    permission_filter = f"access_level in [{levels_quoted}]"

    print(f"【get_permission】milvus_filter={permission_filter}")

    return {
        **state,
        "access_levels": access_levels,
        "permission_filter": permission_filter,
    }


# 2. 节点1: 问题分类节点
def classify_question(state: AgentState) -> AgentState:
    """
    使用LLM判断问题类型
    不用关键词,让模型理解语义
    """
    print("【classify】start")

    llm = _llm_classify

    classification_prompt = """
        你是一个问题分类专家。根据用户问题,判断属于哪种类型:

        1. company_policy - 公司制度、员工手册、福利待遇、请假规则、入职离职流程等
        2. tech_docs - BladeX框架、技术文档、API使用、开发问题、代码示例等
        3. personal_info - 个人信息相关，如我的考勤、我的薪资、我的假期余额、我的工时等
        4. mixed - 同时涉及多种类型的复合问题(如"开发人员的加班补贴政策")
        5. general - 闲聊、问候、与公司/技术无关的问题、需要联网搜索的问题

        用户问题: {question}

        请按以下JSON格式返回:
        {{
            "type": "问题类型",
            "reasoning": "判断理由(1-2句话)",
            "confidence": "高/中/低"
        }}
    """

    messages = [
        SystemMessage(content=classification_prompt.format(question=state["question"]))
    ]

    print("invoke start")
    response = llm.invoke(messages)
    print("invoke end")
    # 解析LLM返回的JSON：ChatOpenAI 返回 AIMessage，取 .content 再解析
    try:
        result = json.loads(response.content)
        question_type = result["type"]
        reasoning = result["reasoning"]
    except Exception as e:
        # 兜底:如果解析失败,默认走混合检索
        _ = e
        question_type = "mixed"
        reasoning = "分类失败,使用混合检索"

    print(f"【classify】type={question_type} reason={reasoning}")

    return {**state, "question_type": question_type, "reasoning": reasoning}


# 3. 路由函数: 根据分类结果决定下一步
def route_question(state: AgentState) -> Literal["rag_policy", "rag_tech", "rag_mixed", "direct_answer", "personal_info_retrieval"]:
    """
    条件边的路由函数
    根据 question_type 返回下一个节点名称
    """
    question_type = state["question_type"]

    routing_map = {
        "company_policy": "rag_policy",
        "tech_docs": "rag_tech",
        "mixed": "rag_mixed",
        "general": "direct_answer",
        "personal_info": "personal_info_retrieval",
    }

    next_node = routing_map.get(question_type, "rag_mixed")

    print(f"【route】{question_type} -> {next_node}")

    return next_node  # 默认混合检索


# ── 共用工具函数 ──────────────────────────────────────────────────────────────
def _detect_no_permission(milvus_client, question_vector: list, type_filter: str) -> bool:
    """
    无权限检测: 在加权限filter后检索为0条时调用。
    去掉 access_level 权限限制,只保留文档类型filter,再查一次。
    - 能查到结果 → 文档存在但被权限拦截 → 返回 True(无权限)
    - 查不到结果 → 文档本身不存在      → 返回 False(无文档)
    """
    check_res = milvus_client.search(
        collection_name=MILVUS_COLLECTION_NAME,
        data=[question_vector],
        limit=1,
        filter=type_filter if type_filter else None,
        search_params={},  # metric_type 已在创建索引时指定（IP），无需重复传
        output_fields=["id"],
    )
    return len(check_res[0]) > 0


# ─────────────────────────────────────────────────────────────────────────────


# 4. 节点2a: 制度类RAG检索
def rag_policy_retrieval(state: AgentState) -> AgentState:
    """检索公司制度文档,同时注入权限filter,只返回当前用户有权查看的制度文档"""
    print("【rag_policy】start")

    milvus_client = _milvus_client
    embeddings = _embeddings

    question_vector = embeddings.embed_query(state["question"])

    # 文档类型filter叠加权限filter:
    # 例: (type == 1) and (access_level in ["public","hr_only"])
    base_filter = 'type == "policy"'
    perm_filter = state.get("permission_filter", "")
    final_filter = (
        f"({base_filter}) and ({perm_filter})" if perm_filter else base_filter
    )

    search_res = milvus_client.search(
        collection_name=MILVUS_COLLECTION_NAME,
        data=[question_vector],
        limit=5,
        filter=final_filter,
        search_params={},  # metric_type 已在创建索引时指定（IP），无需重复传
        output_fields=["text", "access_level"],
    )

    retrieved_docs = [
        {
            "content": res["entity"]["text"],
            "score": res["distance"],
            "access_level": res["entity"].get("access_level", "unknown"),
        }
        for res in search_res[0]
    ]

    # 检索为空时,判断是"权限不足"还是"文档不存在"
    no_permission = False
    if not retrieved_docs and perm_filter:
        no_permission = _detect_no_permission(
            milvus_client, question_vector, base_filter
        )
    print(
        f"【rag_policy】docs={len(retrieved_docs)} no_permission={no_permission} role={state.get('role_name','')}"
    )

    return {
        **state,
        "retrieved_docs": retrieved_docs,
        "no_permission": no_permission,
    }


# 4. 节点2b: 技术类RAG检索
def rag_tech_retrieval(state: AgentState) -> AgentState:
    """检索技术文档,同时注入权限filter,只返回当前用户有权查看的技术文档"""
    print("【rag_tech】start")

    milvus_client = _milvus_client
    embeddings = _embeddings

    question_vector = embeddings.embed_query(state["question"])

    base_filter = 'type == "tech"'
    perm_filter = state.get("permission_filter", "")
    final_filter = (
        f"({base_filter}) and ({perm_filter})" if perm_filter else base_filter
    )

    search_res = milvus_client.search(
        collection_name=MILVUS_COLLECTION_NAME,
        data=[question_vector],
        limit=10,  # 技术问题需要更多代码示例
        filter=final_filter,
        search_params={},  # metric_type 已在创建索引时指定（IP），无需重复传
        output_fields=["text", "access_level"],
    )

    retrieved_docs = [
        {
            "content": res["entity"]["text"],
            "score": res["distance"],
            "access_level": res["entity"].get("access_level", "unknown"),
        }
        for res in search_res[0]
    ]

    # 检索为空时,判断是"权限不足"还是"文档不存在"
    no_permission = False
    if not retrieved_docs and perm_filter:
        no_permission = _detect_no_permission(
            milvus_client, question_vector, base_filter
        )
    print(
        f"【rag_tech】docs={len(retrieved_docs)} no_permission={no_permission} role={state.get('role_name','')}"
    )

    return {
        **state,
        "retrieved_docs": retrieved_docs,
        "no_permission": no_permission,
    }


# 4. 节点2c: 混合RAG检索
def rag_mixed_retrieval(state: AgentState) -> AgentState:
    """跨类型检索(不加type过滤),仅注入权限filter,只返回当前用户有权查看的所有类型文档"""
    print("【rag_mixed】start")

    milvus_client = _milvus_client
    embeddings = _embeddings

    question_vector = embeddings.embed_query(state["question"])

    # 混合检索不限制type,只用权限filter
    perm_filter = state.get("permission_filter", "")

    search_res = milvus_client.search(
        collection_name=MILVUS_COLLECTION_NAME,
        data=[question_vector],
        limit=8,
        filter=perm_filter if perm_filter else None,
        search_params={},  # metric_type 已在创建索引时指定（IP），无需重复传
        output_fields=["text", "type", "access_level"],
    )

    retrieved_docs = [
        {
            "content": res["entity"]["text"],
            "score": res["distance"],
            "type": res["entity"].get("type", ""),
            "access_level": res["entity"].get("access_level", "unknown"),
        }
        for res in search_res[0]
    ]

    # 混合检索无类型限制,无权限检测时传 None(不限 type)
    no_permission = False
    if not retrieved_docs and perm_filter:
        no_permission = _detect_no_permission(milvus_client, question_vector, None)
    print(
        f"【rag_mixed】docs={len(retrieved_docs)} no_permission={no_permission} role={state.get('role_name','')}"
    )

    return {
        **state,
        "retrieved_docs": retrieved_docs,
        "no_permission": no_permission,
    }


def _personal_doc(content: str, score: float = 1.0) -> dict:
    """构造个人信息节点返回的 retrieved_docs 单项，与 RAG 文档结构一致便于 generate_answer 复用。"""
    return {
        "content": content,
        "score": score,
        "type": "personal",
        "access_level": "private",
    }


def _format_personal_result(result_data: list) -> str:
    """将 MySQL 查询结果格式化为可读文本，供放入 retrieved_docs 和后续 LLM 生成答案。"""
    if not result_data:
        return "未查询到相关数据。"
    if len(result_data) == 1:
        return "查询结果：\n" + "\n".join(
            f"- {k}: {v}" for k, v in result_data[0].items()
        )
    lines = [f"查询到 {len(result_data)} 条记录："]
    for i, row in enumerate(result_data[:5], 1):
        lines.append(f"\n记录{i}:\n" + "\n".join(f"  - {k}: {v}" for k, v in row.items()))
    return "\n".join(lines)


# 4. 节点2d: 个人信息检索（Agent + Tool 模式，同步节点与其它节点一致）
def personal_info_retrieval(state: AgentState) -> AgentState:
    """
    使用 Agent + Tool 模式查询个人信息。
    LLM 根据用户问题决定查询哪个表、构造 SQL；注入最近几轮对话历史以支持多轮追问。
    """
    user_id = state.get("user_id", "")
    question = state.get("question", "")
    print(f"【personal_info】start user_id={user_id}")

    system_prompt = f"""
        你是一个数据查询助手，帮助用户查询自己的个人信息。

        当前用户ID: {user_id}

        注意：
        1. 查询时要先查询数据库有哪些表，并通过表名和表的注释去查询对应的数据库表，可重复调用 query_mysql 工具去查询，直到检索出对应的数据，若检索不到则说明原因
        2. 你要执行sql语句之前 ，一定要根据表的注释！来判断是否需要查询该表！查询之前一定要先判断是否需要查询该表！先看表的注释！优先查询有注释的表！！！！

        规则：
        1. 只能查询当前用户自己的数据，WHERE 条件必须包含用户ID限制
        2. 只能执行 SELECT 查询
        3. 查询表时确保没有脱离 user_id 的限制
        4. 不要返回敏感字段如 password
        5. 若问题无法通过现有表回答，请说明原因

        请调用 query_mysql 工具执行查询。"""

    # 注入最近 N 条消息，支持多轮追问（如「我的部门呢」）
    history = state.get("messages", [])[-PERSONAL_INFO_HISTORY_MESSAGES:]
    messages = (
        [SystemMessage(content=system_prompt)]
        + list(history)
        + [HumanMessage(content=question)]
    )

    agent_result = _tool_agent.invoke(
        {"messages": messages},
        config={"recursion_limit": 25},
    )
    result_messages: list = []
    if isinstance(agent_result, dict):
        result_messages = agent_result.get("messages", []) or []
    elif hasattr(agent_result, "messages"):
        result_messages = list(getattr(agent_result, "messages", []) or [])

    personal_data: dict = {}
    retrieved_docs: list = []

    for msg in result_messages:
        # 非工具节点不进入
        if not isinstance(msg, ToolMessage):
            continue
        # 获取工具名称，非query_mysql工具不进入
        tool_name = getattr(msg, "name", "") or ""
        if tool_name and tool_name != "query_mysql":
            continue
        # 解析工具返回内容
        raw = msg.content
        result_str = raw if isinstance(raw, str) else str(raw)
        try:
            result_data = json.loads(result_str)
        except json.JSONDecodeError as e:
            retrieved_docs.append(_personal_doc(f"查询结果解析失败: {e}", 0.0))
            continue
        # 若格式为dict的返回内容有error标识，则查询失败
        if isinstance(result_data, dict) and "error" in result_data:
            retrieved_docs.append(
                _personal_doc(f"查询失败: {result_data['error']}", 0.0)
            )
            continue
        # 若有值list则成功返回
        if isinstance(result_data, list) and len(result_data) > 0:
            personal_data = (
                result_data[0] if len(result_data) == 1 else {"records": result_data}
            )
            retrieved_docs.append(
                _personal_doc(_format_personal_result(result_data), 1.0)
            )
        else:
            retrieved_docs.append(_personal_doc("未查询到相关数据。", 0.0))

    if not retrieved_docs:
        last_ai: AIMessage | None = None
        for m in reversed(result_messages):
            if isinstance(m, AIMessage):
                last_ai = m
                break
        text = (last_ai.content if last_ai else "") or ""
        if isinstance(text, list):
            text = "".join(str(p) for p in text)
        retrieved_docs.append(_personal_doc(text or "暂无回复", 1.0))
    print(f"【personal_info】docs={len(retrieved_docs)}")

    return {
        **state,
        "personal_data": personal_data,
        "retrieved_docs": retrieved_docs,
        "no_permission": False,
    }


# 5. 节点3a: 基于检索结果生成答案
def generate_answer_with_rag(state: AgentState, config: RunnableConfig) -> AgentState:
    """基于检索到的文档生成答案"""
    print("【generate_answer】start")

    # 文档为空时直接返回,不调用LLM,避免用训练数据瞎编答案
    if not state["retrieved_docs"]:
        role_name = state.get("role_name", "")
        if state.get("no_permission", False):
            answer = (
                f"抱歉，您当前的角色「{role_name}」没有权限查看此类文档。\n"
                "如需访问，请联系管理员申请相应权限。"
            )
        else:
            answer = (
                "未在知识库中找到与您问题相关的文档，请确认相关文档是否已录入系统。"
            )
        print(f"【generate_answer】skip_llm docs=0 no_permission={state.get('no_permission', False)}")
        # 固定答案也追加进历史，保证上下文连贯
        return {
            **state,
            "answer": answer,
            "messages": [
                HumanMessage(content=state["question"]),
                AIMessage(content=answer),
            ],
        }

    llm = _llm_generate

    # 构造 RAG 上下文（仅当前轮携带，不存入历史，避免历史膨胀）
    context = "\n\n".join(
        [
            f"文档片段{i + 1} (相关度: {doc['score']:.3f}):\n{doc['content']}"
            for i, doc in enumerate(state["retrieved_docs"])
        ]
    )

    # 根据问题类型定制 System Prompt
    role_name = state.get("role_name", "employee")
    if state["question_type"] == "tech_docs":
        system_prompt = f"你是BladeX技术专家。当前提问用户的角色是「{role_name}」。根据技术文档回答问题,给出具体代码示例和步骤。"
    elif state["question_type"] == "company_policy":
        system_prompt = f"你是公司HR专家。当前提问用户的角色是「{role_name}」。根据员工手册准确回答制度问题,引用具体条款。"
    elif state["question_type"] == "personal_info":
        system_prompt = f"你是企业HR助手。当前用户正在查询自己的个人信息。请根据系统提供的数据准确回答用户的问题，注意保护用户隐私，只回答与问题相关的信息。"
    else:
        system_prompt = f"你是智能助手。当前提问用户的角色是「{role_name}」。根据提供的文档回答问题。"

    # _trim_messages Reducer 已在存储层保证上限，直接取全部即可
    history = state.get("messages", [])

    # 消息结构：system → 历史 → 当前问题（附带检索文档）
    messages_to_send = (
        [SystemMessage(content=system_prompt)]
        + history
        + [
            HumanMessage(
                content=(
                    f"参考文档:\n{context}\n\n"
                    f"用户问题: {state['question']}\n\n"
                    f"请基于以上文档内容回答。如果文档中没有相关信息,请明确告知。"
                )
            )
        ]
    )

    answer_text = _stream_collect_text(llm, messages_to_send, config)
    print(f"【generate_answer】done len={len(answer_text)} docs={len(state['retrieved_docs'])}")

    return {
        **state,
        "answer": answer_text,
        # 追加本轮干净的 Q&A 到历史（operator.add 会接在已有 messages 后面）
        "messages": [
            HumanMessage(content=state["question"]),
            AIMessage(content=answer_text),
        ],
    }

# 5. 节点3b: 基于数据库数据检索到的生成答案
def generate_answer_with_db(state: AgentState, config: RunnableConfig) -> AgentState:
    """基于数据库数据检索到的生成答案"""
    print("\n" + "=" * 60)
    print("【节点3a: generate_answer - 生成答案】")
    print("=" * 60)

    # 文档为空时直接返回,不调用LLM,避免用训练数据瞎编答案

    llm = _llm_generate

    # 构造 RAG 上下文（仅当前轮携带，不存入历史，避免历史膨胀）
    context = "\n\n".join(
        [
            f"文档片段{i + 1} (相关度: {doc['score']:.3f}):\n{doc['content']}"
            for i, doc in enumerate(state["retrieved_docs"])
        ]
    )

    # 根据问题类型定制 System Prompt
    role_name = state.get("role_name", "employee")
    
    system_prompt = f"你是公司用户信息查询助手。当前提问用户的角色是「{role_name}」。根据查询出的数据回答问题,说明情况。"
    print(f"🤖 使用角色: 公司用户信息查询助手 | 用户角色: {role_name}")
    
    # _trim_messages Reducer 已在存储层保证上限，直接取全部即可
    history = state.get("messages", [])

    # 消息结构：system → 历史 → 当前问题（附带检索文档）
    messages_to_send = (
        [SystemMessage(content=system_prompt)]
        + history
        + [
            HumanMessage(
                content=(
                    f"参考数据:\n{context}\n\n"
                    f"用户问题: {state['question']}\n\n"
                    f"请基于以上参考数据内容回答。如果参考数据中没有相关信息,请明确告知。"
                )
            )
        ]
    )

    print(f"📄 上下文长度: {len(context)} 字 | 历史轮数: {len(history) // 2}")
    print("💬 正在调用LLM生成答案（流式）...")
    answer_text = _stream_collect_text(llm, messages_to_send, config)

    print(f"✅ 答案生成完成! 长度: {len(answer_text)} 字")
    print("=" * 60 + "\n")

    return {
        **state,
        "answer": answer_text,
        # 追加本轮干净的 Q&A 到历史（operator.add 会接在已有 messages 后面）
        "messages": [
            HumanMessage(content=state["question"]),
            AIMessage(content=answer_text),
        ],
    }


# 5. 节点3c: 直接回答(不需要RAG)
def direct_answer(state: AgentState, config: RunnableConfig) -> AgentState:
    """闲聊/通用问题,直接用LLM回答，同时维护对话历史"""
    print("【direct_answer】start")

    llm = _llm_direct

    # system_prompt = """
    # 你是一个友好的助手。用户的问题不涉及公司文档或技术问题，请自然对话，回答简洁清晰。

    # 注意：
    # 1. 如果用户的问题有可能需要联网搜索（如今天几月几日、最新的新闻、最新的政策等)，请调用 web_search 函数。
    # 2. 你现有的训练后的内部数据不是最新的，现实的时间和你内部数据的时间不一定相同
    # 3. 现在现实时间是2026年4月27日，并不是2024年了
    # """
    system_prompt = "你是一个友好的助手。用户的问题不涉及公司文档或技术问题，请自然对话，回答简洁清晰。"

    # _trim_messages Reducer 已在存储层保证上限，直接取全部即可
    history = state.get("messages", [])

    messages_to_send = (
        [SystemMessage(content=system_prompt)]
        + history
        + [HumanMessage(content=state["question"])]
    )

    answer_text = _stream_collect_text(llm, messages_to_send, config)

    print(f"【direct_answer】done len={len(answer_text)}")

    return {
        **state,
        "answer": answer_text,
        "retrieved_docs": [],
        "messages": [
            HumanMessage(content=state["question"]),
            AIMessage(content=answer_text),
        ],
    }


# 6. 构建图
def create_classification_graph(checkpointer=None):
    """
    创建问题分类+权限管理决策图。

    图结构:
        get_permission(节点0) → classify(节点1) → route_question(条件路由)
            ├→ rag_policy(节点2a)        ┐
            ├→ rag_tech(节点2b)          ├→ generate_answer(节点3a) → END
            ├→ rag_mixed(节点2c)         ┘
            ├→ personal_info_retrieval(节点2d) → generate_answer(节点3a) → END
            └→ direct_answer(节点3b) → END

    checkpointer 默认为 InMemorySaver()；外部传入同一实例可跨调用保持会话记忆。
    """
    workflow = StateGraph(AgentState)

    # 注册所有节点
    workflow.add_node("get_permission", get_user_permission)  # 节点0: 权限获取
    workflow.add_node("classify", classify_question)  # 节点1: 问题分类
    workflow.add_node("rag_policy", rag_policy_retrieval)  # 节点2a: 制度类RAG
    workflow.add_node("rag_tech", rag_tech_retrieval)  # 节点2b: 技术类RAG
    workflow.add_node("rag_mixed", rag_mixed_retrieval)  # 节点2c: 混合RAG
    workflow.add_node(
        "personal_info_retrieval", personal_info_retrieval
    )  # 节点2d: 个人信息MySQL检索
    workflow.add_node("generate_answer", generate_answer_with_rag)  # 节点3a: 生成答案
    workflow.add_node("generate_answer_with_db", generate_answer_with_db)  # 节点3a: 生成答案
    workflow.add_node("direct_answer", direct_answer)  # 节点3b: 直接回答

    # 入口: 先获取权限
    workflow.set_entry_point("get_permission")

    # 权限获取完成后固定进入分类节点
    workflow.add_edge("get_permission", "classify")

    # 分类完成后条件路由
    workflow.add_conditional_edges(
        "classify",
        route_question,
        {
            "rag_policy": "rag_policy",
            "rag_tech": "rag_tech",
            "rag_mixed": "rag_mixed",
            "direct_answer": "direct_answer",
            "personal_info_retrieval": "personal_info_retrieval",
        },
    )

    # 四个检索节点汇聚到生成答案节点
    workflow.add_edge("rag_policy", "generate_answer")
    workflow.add_edge("rag_tech", "generate_answer")
    workflow.add_edge("rag_mixed", "generate_answer")
    workflow.add_edge("personal_info_retrieval", "generate_answer_with_db")
    workflow.add_edge("generate_answer", END)
    workflow.add_edge("generate_answer_with_db", END)
    workflow.add_edge("direct_answer", END)

    return workflow.compile(checkpointer=checkpointer or InMemorySaver())


# 7. 使用示例
async def chat_with_classification(question: str, user_id: str = "guest"):
    """
    使用分类+权限决策流处理问题。
    user_id: 由上层API传入,用于调用Java服务获取角色和权限。
    """
    graph = create_classification_graph()

    # 初始状态: 权限字段初始化为空,由 get_user_permission 节点填充
    initial_state = {
        "question": question,
        "user_id": user_id,
        "role_id": 0,
        "role_name": "",
        "access_levels": [],
        "permission_filter": "",
        "no_permission": False,
        "question_type": "",
        "retrieved_docs": [],
        "answer": "",
        "reasoning": "",
        "personal_data": {},
    }

    # thread_id 用 user_id 隔离不同用户的会话记忆
    config = {"configurable": {"thread_id": user_id}}
    result = await graph.ainvoke(initial_state, config=config)

    print(
        f"【chat_done】user_id={result['user_id']} role={result['role_name']} "
        f"type={result['question_type']} docs={len(result['retrieved_docs'])} answer_len={len(result['answer'])}"
    )

    return {
        "answer": result["answer"],
        "question_type": result["question_type"],
        "reasoning": result["reasoning"],
        "role_name": result["role_name"],
        "access_levels": result["access_levels"],
        "doc_count": len(result["retrieved_docs"]),
    }


import asyncio

if __name__ == "__main__":
    print("\n" + "🔧" * 30)
    print("【测试用例】")
    print("🔧" * 30)

    # 测试1: 普通员工问制度类问题(只能看public文档)
    # print("\n>>> 测试1: 普通员工 - 制度类问题")
    # result = asyncio.run(chat_with_classification("请假需要提前几天申请?", user_id="user_001"))
    # print(f"预期路径: get_permission → classify → rag_policy(filter:type==1 AND access_level in ['public']) → generate_answer")

    # 测试2: HR问薪资制度(可以看public+hr_only文档)
    # print("\n>>> 测试2: HR用户 - 制度类问题")
    # result = asyncio.run(chat_with_classification("各岗位薪资标准是什么?", user_id="hr_001"))
    # print(f"预期路径: get_permission → classify → rag_policy(filter:type==1 AND access_level in ['public','hr_only']) → generate_answer")

    # 测试3: 开发人员问技术文档
    # print("\n>>> 测试3: 开发人员 - 技术类问题")
    # result = asyncio.run(chat_with_classification("bladeX的lombok使用教程?", user_id="dev_001"))
    # print(f"预期路径: get_permission → classify → rag_tech → generate_answer")

    # 测试4: 混合问题
    # print("\n>>> 测试4: 混合问题")
    # result = asyncio.run(chat_with_classification("开发人员加班有什么补偿?", user_id="dev_001"))
    # print(f"预期路径: get_permission → classify → rag_mixed → generate_answer")

    # 测试5: 闲聊(不需要权限过滤)
    # print("\n>>> 测试5: 闲聊问题")
    # result = asyncio.run(chat_with_classification("今天广州天气怎么样?", user_id="user_001"))
    # print(f"预期路径: get_permission → classify → direct_answer")

    pass  # 所有测试已注释
