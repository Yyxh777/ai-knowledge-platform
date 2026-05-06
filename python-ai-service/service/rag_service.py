import config  # noqa: F401
from config import POSTGRES_URI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from workflows.rag_graph import create_classification_graph
from utils.conversation_db import init_db, ensure_conversation, add_message

_checkpointer: AsyncPostgresSaver | None = None
_cp_pool: AsyncConnectionPool | None = None
_graph = None


async def startup() -> None:
    """FastAPI 启动：会话表由外部 DDL 维护；初始化 PostgreSQL checkpoint 并编译 LangGraph。"""
    global _graph, _checkpointer, _cp_pool
    if not POSTGRES_URI:
        raise RuntimeError("未配置 POSTGRES_URI，无法初始化 LangGraph PostgreSQL checkpoint")

    init_db()

    _cp_pool = AsyncConnectionPool(
        conninfo=POSTGRES_URI,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
        open=False,
    )
    await _cp_pool.open()

    _checkpointer = AsyncPostgresSaver(_cp_pool)
    await _checkpointer.setup()
    _graph = create_classification_graph(checkpointer=_checkpointer)


async def shutdown() -> None:
    """关闭 checkpoint 连接池。"""
    global _checkpointer, _cp_pool
    _checkpointer = None
    if _cp_pool is not None:
        await _cp_pool.close()
        _cp_pool = None


async def chat_with_rag_stream(query: str, access_token: str, thread_id: str, user_info: dict):
    """
    流式返回 RAG 聊天结果，支持会话记忆。

    使用 LangGraph 分类决策图（classify → retrieve → generate_answer），
    通过 astream_events 逐 token yield 实现真流式输出。

    图内多轮记忆以 PostgreSQL checkpoint（thread_id）为准；MySQL 仅落库供 Java 侧展示。

    Args:
        query:        用户问题
        access_token: 用户的访问令牌，用于调用 Java 服务获取权限
        thread_id:    会话线程 ID，格式为 "{user_id}_{timestamp_ms}"，同一会话保持不变
        user_info:    已认证用户信息字典，必须包含 user_id
    """
    if _graph is None:
        raise RuntimeError("RAG graph 尚未初始化，请确认 FastAPI lifespan 已正常执行 startup()")

    user_id = str(user_info.get("user_id", ""))
    config = {"configurable": {"thread_id": thread_id, "access_token": access_token}}

    ensure_conversation(thread_id, user_id)
    add_message(thread_id, role="user", content=query)

    initial_state = {
        "question": query,
        "user_id": user_id,
        "question_type": "",
        "retrieved_docs": [],
        "answer": "",
        "reasoning": "",
        # 不以 MySQL 回填 messages，避免与 checkpoint 内已有 history 重复合并
        "messages": [],
        "role_id": user_info.get("role_id", 0),
        "role_name": user_info.get("role_name", ""),
        "access_levels": [],
        "permission_filter": "",
        "no_permission": False,
    }

    try:
        streamed_tokens = 0
        assistant_text = ""

        async for event in _graph.astream_events(initial_state, config=config, version="v2"):
            kind = event["event"]
            node = event.get("metadata", {}).get("langgraph_node", "")

            if kind == "on_chat_model_stream" and node in (
                "generate_answer",
                "direct_answer",
                "generate_answer_with_db",
            ):
                content = event["data"]["chunk"].content
                if isinstance(content, str) and content:
                    streamed_tokens += len(content)
                    assistant_text += content
                    yield content

            elif kind == "on_chain_end" and node in (
                "generate_answer",
                "direct_answer",
                "generate_answer_with_db",
            ):
                if streamed_tokens == 0:
                    answer = event["data"].get("output", {}).get("answer", "")
                    if answer:
                        assistant_text = answer
                        yield answer

        if assistant_text:
            add_message(thread_id, role="assistant", content=assistant_text)

    except Exception as e:
        print(f"流式处理错误: {e}")
        raise
