from langgraph.pregel import _checkpoint

import config  # noqa: F401
from config import POSTGRES_URI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from workflows.rag_graph import create_classification_graph
from utils.conversation_db import init_db, ensure_conversation, add_message

# 定义图、连接池、checkpointer
_checkpoint: AsyncPostgresSaver() | None = None
_cp_pool: AsyncConnectionPool | None = None
_graph = None


# 定义startup启动函数
async def startup() -> None:
    global _checkpoint, _cp_pool, _graph
    if not POSTGRES_URI:
        raise RuntimeError("未配置 POSTGRES_URI，无法初始化 LangGraph PostgreSQL checkpoint")

    # 初始化连接池并打开
    init_db()
    _cp_pool = AsyncConnectionPool(
        conninfo=POSTGRES_URI,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
        open=False
    )
    await _cp_pool.open()

    _checkpoint = AsyncPostgresSaver(_cp_pool)
    await _checkpoint.setup()

    _graph = create_classification_graph(checkpointer=_checkpoint)


# 定义shutdown关闭函数
async def shutdown() -> None:
    global _checkpoint, _cp_pool, _graph
    _checkpoint = None
    if _cp_pool is not None:
        await _cp_pool.close()
        _cp_pool = None


# 流式接口方法
async def chat_with_rag_stream(query: str, access_token: str, thread_id: str, user_info: dict):
    if not _graph:
        raise RuntimeError("RAG graph 尚未初始化，请确认 FastAPI lifespan 已正常执行 startup()")

    user_id = str(user_info.get("user_id", ""))
    config = {"configurable": {"thread_id": thread_id, "access_token": access_token}}

    ensure_conversation(thread_id, user_id)  # 插入线程用户关系表
    add_message(thread_id, role="user", content=query)  # 插入线程聊天记录表

    # 初始化state
    initial_state = {
        "question": query,
        "user_id": user_id,
        "question_type": "",
        "retrieved_docs": [],
        "answer": "",
        "reasoning": "",
        "messages": [],
        "role_id": user_info.get("role_id", 0),
        "role_name": user_info.get("role_name", ""),
        "access_levels": [],
        "permission_filter": "",
        "no_permission": False,
    }

    # 调用工作流并整理返回结果
    try:
        streamed_tokens = 0  # 流式返回的token数量
        assistant_text = ""  # 助手返回的文本

        async for event in _graph.astream_events(initial_state, config=config, version="v2"):
            kind = event["event"]
            node = event.get("metadata", {}).get("langgraph_node", "")

            if kind == "on_chat_model_stream" and node in (
                    "generate_answer",
                    "direct_answer",
                    "generate_answer_with_db",
            ):
                content = event["data"]["chunk"].content # 获取节点输出的内容
                if isinstance(content, str) and content:
                    streamed_tokens+=len(content)
                    assistant_text+=content
                    yield assistant_text
            elif kind == "on_chain_end" and node in (
                    "generate_answer",
                    "direct_answer",
                    "generate_answer_with_db",
            ):
                if streamed_tokens == 0:
                    answer = event["data"].get("output", {}).get("answer", "")
                    if answer:
                        assistant_text=answer
                        yield assistant_text

        if assistant_text:
            add_message(thread_id,"assistant",content=assistant_text)

    except Exception as e:
        print(f"流式处理错误: {e}")
        raise
