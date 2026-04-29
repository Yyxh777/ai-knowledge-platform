import config  # noqa: F401
from config import REDIS_URL, REDIS_TTL_SEC
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from workflows.rag_graph import create_classification_graph, MAX_HISTORY_TURNS
from utils.conversation_db import init_db, ensure_conversation, add_message, load_messages
import time

_checkpointer: AsyncRedisSaver | None = None
_graph = None


async def startup() -> None:
    """FastAPI 启动时调用：初始化 SQLite 会话表，编译 LangGraph 工作流。"""
    global _graph, _checkpointer
    init_db()
    _checkpointer = AsyncRedisSaver(
        redis_url=REDIS_URL,
        ttl={"default_ttl": REDIS_TTL_SEC},
    )
    await _checkpointer.asetup()
    _graph = create_classification_graph(checkpointer=_checkpointer)


async def shutdown() -> None:
    """FastAPI 关闭时调用：保留接口，当前无需资源释放。"""
    global _checkpointer
    if _checkpointer:
        await _checkpointer.aclose()
        _checkpointer = None
    return
# ────────────────────────────────────────────────────────────────────────────────


async def chat_with_rag_stream(query: str, access_token: str, thread_id: str, user_info: dict):
    """
    流式返回 RAG 聊天结果，支持会话记忆。

    使用 LangGraph 分类决策图（classify → retrieve → generate_answer），
    通过 astream_events 逐 token yield 实现真流式输出。

    Args:
        query:        用户问题
        access_token: 用户的访问令牌，用于调用 Java 服务获取权限
        thread_id:    会话线程 ID，格式为 "{user_id}_{timestamp_ms}"，必须由已认证的调用方传入
        user_info:    已认证用户信息字典，必须包含 user_id
    """
    if _graph is None:
        raise RuntimeError("RAG graph 尚未初始化，请确认 FastAPI lifespan 已正常执行 startup()")

    user_id = str(user_info.get("user_id", ""))

    # checkpoint thread_id 用“每次请求唯一”，避免 Redis checkpoint 里的 messages
    # 与 SQLite 回填历史重复合并；会话历史仍以 SQLite 为准。
    ckpt_thread_id = f"{thread_id}__ckpt_{int(time.time() * 1000)}"
    config = {"configurable": {"thread_id": ckpt_thread_id, "access_token": access_token}}

    # 1) 先从业务库加载历史（不包含本次用户提问）
    history_messages = load_messages(thread_id, max_messages=MAX_HISTORY_TURNS * 2)

    # 2) 建立会话并落库用户这一句（确保“一句一存”）
    ensure_conversation(thread_id, user_id)
    add_message(thread_id, role="user", content=query)

    initial_state = {
        "question":          query,
        "user_id":           user_id,
        "question_type":     "",
        "retrieved_docs":    [],
        "answer":            "",
        "reasoning":         "",
        # messages 使用 operator.add 归约器：此处传 [] 不会覆盖历史，
        # LangGraph 会将 checkpointer 里已有的历史与本次 [] 相加（即原样保留历史）
        # 注意：这里加载的是“历史”，不包含本次 query；模型会用 state.question 作为当前提问
        "messages":          history_messages,
        "role_id":           user_info.get("role_id", 0),
        "role_name":         user_info.get("role_name", ""),
        "access_levels":     [],
        "permission_filter": "",
        "no_permission":     False,
    }

    try:
        # 记录本次对话是否已通过 LLM token 流输出了内容
        # 若没有（如"无权限"/"无文档"直接返回固定字符串），则从节点完成事件中取答案
        streamed_tokens = 0
        assistant_text = ""

        async for event in _graph.astream_events(initial_state, config=config, version="v2"):
            kind = event["event"]
            node = event.get("metadata", {}).get("langgraph_node", "")

            # 返回内容示例：
            # {
            #     "event": "on_chat_model_stream",     # 事件类型
            #     "metadata": {
            #         "langgraph_node": "generate_answer"   # 是哪个节点触发的
            #     },
            #     "data": {
            #         "chunk": AIMessageChunk(content="你")  # LLM 这次输出的一个 token
            #     }
            # }


            # ① 真流式：LLM 每生成一个 token 立即 yield
            if kind == "on_chat_model_stream" and node in ("generate_answer", "direct_answer","generate_answer_with_db"):
                content = event["data"]["chunk"].content
                if isinstance(content, str) and content:
                    streamed_tokens += len(content)
                    assistant_text += content
                    yield content

            # ② 固定字符串答案：节点内未调用 LLM（无权限/无文档），从节点结束事件里取
            elif kind == "on_chain_end" and node in ("generate_answer", "direct_answer","generate_answer_with_db"):
                if streamed_tokens == 0:
                    answer = event["data"].get("output", {}).get("answer", "")
                    if answer:
                        assistant_text = answer
                        yield answer

        # 结束：只在成功流出后落库 AI 回复
        if assistant_text:
            add_message(thread_id, role="assistant", content=assistant_text)

    except Exception as e:
        print(f"流式处理错误: {e}")
        raise
