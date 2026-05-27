from typing import TypedDict, Literal, Annotated

from langchain_classic.schema.runnable import history
from langchain_community import embeddings
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from openai.resources.uploads import parts
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
import json
import pymysql
import requests
from pymysql.cursors import DictCursor
from langchain.agents import create_agent

# 定义llm、embedding、milvus_client、历史对话轮数上限
_classify_llm = ChatOpenAI(model="qwen-plus", temperature=0)  # 问题分类LLM
_embeddings = DashScopeEmbeddings(model="text-embedding-v4")  # 向量模型
_milvus_client = MilvusClient(uri=MILVUS_URI)  # milvus客户端
_generate_llm = ChatOpenAI(model="qwen-plus", temperature=0.7, streaming=True)  # 根据文档内容生成LLM
_direct_llm = ChatOpenAI(model="qwen-plus", temperature=0.9, streaming=True)  # 通用交互LLM

_MAX_HISTORY_TURNS = 10
_MAX_STORE = 2 * _MAX_HISTORY_TURNS
_MAX_USER_INFO_STORE = 6


@tool
def query_mysql(sql: str):
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


# 个人信息检索工具agent
_personal_info_agent = create_agent(
    model=ChatOpenAI(model="qwen-plus", temperature=0),
    tools=[query_mysql]
)


# 定义reducer消息合并规则函数
def _trim_messages(existing: list, new: list) -> list:
    return (existing + new)[-_MAX_STORE:]


# 定义状态State
class AgentState(TypedDict):
    messages: Annotated[list, _trim_messages]  # 历史对话

    # 入参
    query: str  # 用户问题
    user_id: str  # 用户id
    role_id: int  # 用户角色id
    role_name: str  # 用户角色名称

    # 图产生的字段
    query_type: str  # 问题类型
    access_levels: list  # 用户权限数组
    permission_filter: str  # 用户权限过滤条件
    retrieved_docs: list  # 向量检索出的文档内容
    no_permission: bool  # 是否权限不足

    # 出餐咯
    answer: str  # 模型返回结果


# 节点0：获取用户角色权限
# def get_user_permission(state: AgentState, config: RunnableConfig) -> AgentState:
def get_user_permission(state: AgentState, config: RunnableConfig) -> AgentState:
    # 1.获取token
    access_token = (config or {}).get("configure", {}).get("access_token", "")

    access_levels = ["public"]
    if not access_token:
        pass
    else:
        try:
            # 2.调用业务系统获取角色权限数组
            response = requests.get(
                f"{JAVA_SERVICE_URL}//level/getByUser",
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
                access_levels = result.get("data", "public")
        except Exception as e:
            print(f"调用业务系统获取角色权限失败：{e}")

    # 3. 拼接权限过滤条件
    levels_quoted = ",".join(f'"{al}"' for al in access_levels)
    permission_filter = f"access_level in [{levels_quoted}]"

    return {
        **state,
        "access_levels": access_levels,
        "permission_filter": permission_filter,
    }


# 节点1：问题分类
def classify_query(state: AgentState) -> AgentState:
    # 定义系统提示词
    system_prompt = """
    你是一位对语义有深度理解且严谨的精通全部语言的问题分类专家，根据用户问题，判断是哪种类型：
    
    1. company_policy - 公司制度、员工手册、福利待遇、请假规则、入职离职流程等
    2. tech_docs - BladeX框架、技术文档、API使用、开发问题、代码示例等
    3. personal_info - 个人信息相关，如我的考勤、我的薪资、我的假期余额、我的工时等
    4. mixed - 同时涉及多种类型的复合问题(如"开发人员的加班补贴政策")
    5. general - 闲聊、问候、与公司/技术无关的问题、需要联网搜索的问题

    用户的问题：
    {query}
    
    请按以下JSON格式返回:
    {{
        "query_type": "问题类型",
        "reasoning": "判断理由(1-2句话)",
        "confidence": "匹配度:高/中/低"
    }}
    
    """
    # 调用LLM返回问题分类json字符串
    messages = [
        SystemMessage(content=system_prompt.format(query=state["query"]))
    ]
    response = _classify_llm.invoke(messages)
    # 解析json并将结果放入state中
    try:
        result = json.load(response.content)
        query_type = result["query_type"]
        reasoning = result["reasoning"]
    except Exception as e:
        print(e)
        query_type = "mixed"
        reasoning = "分类失败，使用混合检索"

    return {
        **state,
        "query_type": query_type,
        "reasoning": reasoning,
    }


# 路由函数：根据分类结果分发节点
def route_query(state: AgentState) -> Literal[
    "rag_policy", "rag_tech", "rag_mixed", "direct_answer", "personal_info_retrieval"]:
    routing_map = {
        "company_policy": "rag_policy",
        "tech_docs": "rag_tech",
        "personal_info": "personal_info_retrieval",
        "mixed": "rag_mixed",
        "general": "rag_general"
    }
    return routing_map.get(state["query_type"], "mixed")


# 节点2-RAG共用工具函数：无权限检索向量数据库
# def _detect_no_permission(milvus_client, question_vector: list, type_filter: str) -> bool:
def _detect_no_permission(milvus_client: MilvusClient, query_vector: list, type_filer: str) -> bool:
    # 去除permission_filter检索：若返回数据则说明无权限检索到数据；若没有返回，说明没有提供相应的知识库内容
    check_res = milvus_client.search(
        collection_name=MILVUS_COLLECTION_NAME,
        data=query_vector,
        filter=type_filer if type_filer else "",
        limit=1,
        output_fields=["id"]
    )
    return (len(check_res[0])) > 0


# 节点2a：制度类RAG检索节点 def rag_policy_retrieval(state: AgentState) -> AgentState:
def rag_policy_retrieval(state: AgentState) -> AgentState:
    # 1.参数准备
    # 用户问题向量化
    query_vector = _embeddings.embed_query(state["query"])
    # 拼接向量检索条件
    type_filter = 'type == "policy"'
    permission_filter = state.get("permission_filter", "")
    final_filter = "and".join([permission_filter, type_filter]) if permission_filter else type_filter

    # 2.检索向量数据库获取检索内容
    search_res = _milvus_client.search(
        collection_name=MILVUS_COLLECTION_NAME,
        data=[query_vector],
        limit=5,
        filter=final_filter,
        output_fields=["text", "access_level"],
    )
    # 检索内容为空，判断是 "权限不足" 或 "文档不存在"
    no_permission = False
    if len(search_res[0]) == 0 and permission_filter:
        no_permission = _detect_no_permission(_milvus_client, [query_vector], type_filter)

    # 3.整理检索内容
    retrieved_docs = [
        {
            "content": res["entity"]["text"],
            "score": res["distance"],
            "access_level": res["entity"].get("access_level", "unknown"),
        }
        for res in search_res[0]
    ]
    print(
        f"【rag_policy】docs={len(retrieved_docs)} no_permission={no_permission} role={state.get('role_name', '')}"
    )

    return {
        **state,
        "retrieved_docs": retrieved_docs,
        "no_permission": no_permission
    }


# 节点2b：技术类RAG检索节点 def rag_tech_retrieval(state: AgentState) -> AgentState:
def rag_tech_retrieval(state: AgentState) -> AgentState:
    # 1.参数准备
    # 用户问题向量化
    query_vector = _embeddings.embed_query(state["query"])
    # 拼接向量检索条件
    type_filter = 'type == "tech"'
    permission_filter = state.get("permission_filter", "")
    final_filter = "and".join([permission_filter, type_filter]) if permission_filter else type_filter

    # 2.检索向量数据库获取检索内容
    search_res = _milvus_client.search(
        collection_name=MILVUS_COLLECTION_NAME,
        data=[query_vector],
        limit=10,
        filter=final_filter,
        output_fields=["text", "access_level"],
    )
    # 检索内容为空，判断是 "权限不足" 或 "文档不存在"
    no_permission = False
    if len(search_res[0]) == 0 and permission_filter:
        no_permission = _detect_no_permission(_milvus_client, [query_vector], type_filter)

    # 3.整理检索内容
    retrieved_docs = [
        {
            "content": res["entity"]["text"],
            "score": res["distance"],
            "access_level": res["entity"].get("access_level", "unknown"),
        }
        for res in search_res[0]
    ]
    print(
        f"【rag_tech】docs={len(retrieved_docs)} no_permission={no_permission} role={state.get('role_name', '')}"
    )

    return {
        **state,
        "retrieved_docs": retrieved_docs,
        "no_permission": no_permission
    }


# 节点2c：混合RAG检索 def rag_mixed_retrieval(state: AgentState) -> AgentState:
def rag_mixed_retrieval(state: AgentState) -> AgentState:
    # 1.参数准备
    # 用户问题向量化
    query_vector = _embeddings.embed_query(state["query"])
    # 拼接向量检索条件
    permission_filter = state.get("permission_filter", "")

    # 2.检索向量数据库获取检索内容
    search_res = _milvus_client.search(
        collection_name=MILVUS_COLLECTION_NAME,
        data=[query_vector],
        limit=8,
        filter=permission_filter if permission_filter else "",
        output_fields=["text", "access_level", "type"],
    )
    # 检索内容为空，判断是 "权限不足" 或 "文档不存在"
    no_permission = False
    if len(search_res[0]) == 0 and permission_filter:
        no_permission = _detect_no_permission(_milvus_client, [query_vector], "")

    # 3.整理检索内容
    retrieved_docs = [
        {
            "content": res["entity"]["text"],
            "score": res["distance"],
            "type": res["entity"].get("type", ""),
            "access_level": res["entity"].get("access_level", "unknown"),
        }
        for res in search_res[0]
    ]
    print(
        f"【rag_mixed】docs={len(retrieved_docs)} no_permission={no_permission} role={state.get('role_name', '')}"
    )

    return {
        **state,
        "retrieved_docs": retrieved_docs,
        "no_permission": no_permission
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


# 节点2d：个人信息检索 def personal_info_retrieval(state: AgentState) -> AgentState:
def personal_info_retrieval(state: AgentState) -> AgentState:
    # 0.参数准备
    user_id = state.get("user_id", "")

    # 定义系统提示词
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

            请调用 query_mysql 工具执行查询。
    """
    history = state.get("messages", [])[-_MAX_USER_INFO_STORE:]
    messages = [
        SystemMessage(system_prompt)
        + history
    ]
    # 2.调用agent并解析返回内容
    agent_result = _personal_info_agent.invoke({"message": messages}, config={"recursion_limit": 25})
    result_messages: list = []
    if isinstance(agent_result, dict):
        result_messages = agent_result.get("messages", []) or []
    elif hasattr(agent_result, "messages"):
        result_messages = list(getattr(agent_result, "messages", []) or [])

    # 3.获取agent返回参数并解析
    personal_data: dict = {}
    retrieved_docs: list[str] = []

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


# 节点3-流式共用工具函数
# def _stream_collect_text(llm: ChatOpenAI, messages: list, config: RunnableConfig | None) -> str:
def _stream_collect_text(llm: ChatOpenAI, messages: list, config: RunnableConfig | None) -> str:
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
                if isinstance(block, dict) and block.get("type", "") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
    return "".join(parts)


# 节点3a：RAG检索汇总生成 def generate_answer_with_rag(state: AgentState, config: RunnableConfig) -> AgentState:
def generate_answer_with_rag(state: AgentState, config: RunnableConfig) -> AgentState:
    # 0.检索文档内容为空
    if not state["retrieved_docs"]:
        role_name = state["role_name"]
        if state.get("no_permission", False):
            answer = (
                f"抱歉，您当前的角色「{role_name}」没有权限查看此类文档。\n"
                "如需访问，请联系管理员申请相应权限。"
            )
        else:
            answer = (
                "未在知识库中找到与您问题相关的文档，请确认相关文档是否已录入系统。"
            )
        return {
            **state,
            "answer": answer,
            "messages": [
                HumanMessage(content=state["query"]),
                AIMessage(content=answer),
            ],
        }

    # 1.定义提示词
    role_name = state.get("role_name", "employee")
    if state["query_type"] == "tech_docs":
        system_prompt = f"你是BladeX技术专家。当前提问用户的角色是「{role_name}」。根据技术文档回答问题,给出具体代码示例和步骤。"
    elif state["query_type"] == "company_policy":
        system_prompt = f"你是公司HR专家。当前提问用户的角色是「{role_name}」。根据员工手册准确回答制度问题,引用具体条款。"
    elif state["query_type"] == "personal_info":
        system_prompt = f"你是企业HR助手。当前用户正在查询自己的个人信息。请根据系统提供的数据准确回答用户的问题，注意保护用户隐私，只回答与问题相关的信息。"
    else:
        system_prompt = f"你是智能助手。当前提问用户的角色是「{role_name}」。根据提供的文档回答问题。"

    # 2.通过检索出的文档内容组装RAG上下文、messages
    context = "\n\n".join(
        f"文档片段{i + 1}(相关度:{doc['score']:.3f}):\n{doc['content']}"
        for i, doc in enumerate(state["retrieved_docs"])
    )

    history = state.get("messages", [])
    messages = [
        SystemMessage(system_prompt)
        + history
        + HumanMessage(
            content=(
                f"参考文档:\n{context}\n\n"
                f"用户问题: {state['query']}\n\n"
                f"请基于以上文档内容回答。如果文档中没有相关信息,请明确告知。"
            ))
    ]

    # 3.调用模型返回结果
    answer_text = _stream_collect_text(_generate_llm, messages, config)

    return {
        **state,
        "answer": answer_text,
        "messages": [
            HumanMessage(state["query"]),
            AIMessage(answer_text)
        ],
    }


# 节点3b；个人信息检索汇总生成 def generate_answer_with_db(state: AgentState, config: RunnableConfig) -> AgentState:
def generate_answer_with_db(state: AgentState, config: RunnableConfig) -> AgentState:
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

    answer_text = _stream_collect_text(_generate_llm, messages_to_send, config)

    return {
        **state,
        "answer": answer_text,
        "messages": [
            HumanMessage(content=state["question"]),
            AIMessage(content=answer_text),
        ],
    }


# 节点3c：通用聊天 def direct_answer(state: AgentState, config: RunnableConfig) -> AgentState:
def direct_answer(state: AgentState, config: RunnableConfig) -> AgentState:
    # 1.定义提示词
    system_prompt = f"你是一个企业内部助手，用户的角色是{state['role_name']},根据用户问题给出答案"
    # 2.组装messages
    history = state.get("messages", [])
    messages = [
        SystemMessage(system_prompt)
        + history
        + HumanMessage(
            f"用户的问题:{state['query']}\n\n"
        )
    ]
    # 3.调用模型返回结果
    answer_text = _stream_collect_text(_direct_llm, messages, config)

    return {
        **state,
        "answer": answer_text,
        "messages": [
            HumanMessage(state["query"]),
            AIMessage(answer_text)
        ]
    }


# 构建图 def create_classification_graph(checkpointer=None):
def create_classification_graph(checkpointer=None):
    workflow = StateGraph(AgentState)
    # 声明所有节点
    workflow.add_node("get_permission", get_user_permission)  # 节点0: 权限获取
    workflow.add_node("classify", classify_query())  # 节点1: 问题分类

    workflow.add_node("rag_policy", rag_policy_retrieval)  # 节点2a: 制度类RAG
    workflow.add_node("rag_tech", rag_tech_retrieval)  # 节点2b: 技术类RAG
    workflow.add_node("rag_mixed", rag_mixed_retrieval)  # 节点2c: 混合RAG
    workflow.add_node(
        "personal_info_retrieval", personal_info_retrieval
    )  # 节点2d: 个人信息MySQL检索

    workflow.add_node("generate_answer", generate_answer_with_rag)  # 节点3a: 生成答案
    workflow.add_node("generate_answer_with_db", generate_answer_with_db)  # 节点3c: 生成答案
    workflow.add_node("direct_answer", direct_answer)  # 节点3b: 直接回答

    # 路由函数和所有节点之间连接
    workflow.add_edge("get_permission", "classify")
    workflow.add_conditional_edges(
        "classify",
        route_query,
        {
            "rag_policy": "rag_policy",
            "rag_tech": "rag_tech",
            "rag_mixed": "rag_mixed",
            "direct_answer": "direct_answer",
            "personal_info_retrieval": "personal_info_retrieval",
        },
    )

    workflow.add_edge("rag_policy", "generate_answer")
    workflow.add_edge("rag_tech", "generate_answer")
    workflow.add_edge("rag_mixed", "generate_answer")
    workflow.add_edge("personal_info_retrieval", "generate_answer_with_db")

    workflow.add_edge("generate_answer", END)
    workflow.add_edge("generate_answer_with_db", END)
    workflow.add_edge("direct_answer", END)

    # 编译图
    return workflow.compile(checkpointer=checkpointer or InMemorySaver())
