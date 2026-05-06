from __future__ import annotations

import time

import pymysql
from langchain_core.messages import AIMessage, HumanMessage
from pymysql.cursors import Cursor

from config import (
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
)


def _connect() -> pymysql.connections.Connection:
    """短连接：与会话相关的写入频率适中，避免在异步路由里引入额外复杂度。"""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        cursorclass=Cursor,
    )


def init_db() -> None:
    """表结构由运维 / Java 侧 DDL 维护；此处保留空实现以兼容 rag_service 启动流程。"""
    return


def ensure_conversation(conversation_id: str, user_id: str) -> None:
    now = int(time.time())
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversations(id, user_id, created_at, updated_at)
                VALUES(%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE updated_at = VALUES(updated_at)
                """,
                (conversation_id, str(user_id), now, now),
            )
        conn.commit()


def add_message(conversation_id: str, role: str, content: str) -> None:
    if role not in ("user", "assistant"):
        raise ValueError("role must be 'user' or 'assistant'")
    now = int(time.time())
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages(conversation_id, role, content, created_at)
                VALUES(%s, %s, %s, %s)
                """,
                (conversation_id, role, content, now),
            )
        conn.commit()


def load_messages(conversation_id: str, max_messages: int) -> list:
    """按创建时间倒序取最新 max_messages，再反转为时间正序返回。

    默认聊天路径不再调用；保留供 checkpoint 丢失时的 bootstrap 或运维用途。
    """
    if max_messages <= 0:
        return []
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT role, content
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                (conversation_id, max_messages),
            )
            rows = cur.fetchall()

    rows = list(rows)
    rows.reverse()

    messages: list = []
    for role, content in rows:
        if role == "user":
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))
    return messages


def list_conversations_for_user(user_id: str, limit: int) -> list[dict]:
    """当前用户的会话列表，按 updated_at 倒序。"""
    if limit <= 0:
        return []
    uid = str(user_id)
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, created_at, updated_at
                FROM conversations
                WHERE user_id = %s
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (uid, limit),
            )
            rows = cur.fetchall()
    return [
        {
            "thread_id": r[0],
            "user_id": str(r[1]),
            "created_at": int(r[2]),
            "updated_at": int(r[3]),
        }
        for r in rows
    ]


def list_messages_for_user(thread_id: str, user_id: str) -> list[dict] | None:
    """
    返回会话内全部消息（时间正序）。
    若会话不存在，或不属于该 user_id，返回 None。
    """
    uid = str(user_id)
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id FROM conversations WHERE id = %s LIMIT 1",
                (thread_id,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    if str(row[0]) != uid:
        return None
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC, id ASC
                """,
                (thread_id,),
            )
            rows = cur.fetchall()
    return [
        {"role": r[0], "content": r[1], "created_at": int(r[2])}
        for r in rows
    ]


def validate_thread_access(thread_id: str, user_id: str) -> tuple[bool, str]:
    """
    WebSocket 会话归属：前缀须与 token 内 user_id 一致；若 conversations 中已有该 id，则 user_id 须与库内一致。
    """
    uid = str(user_id)
    if not thread_id.startswith(f"{uid}_"):
        return False, "thread_id 与当前用户不匹配"

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id FROM conversations WHERE id = %s LIMIT 1",
                (thread_id,),
            )
            row = cur.fetchone()

    if row is not None:
        db_uid = str(row[0])
        if db_uid != uid:
            return False, "无权使用该会话"
    return True, ""
