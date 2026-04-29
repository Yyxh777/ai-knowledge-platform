from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage


_DB_PATH = Path(__file__).resolve().parent.parent / "conversations.db"


def _connect() -> sqlite3.Connection:
    # 每次调用新建连接：开发期最简单，且不引入额外连接池复杂度
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db() -> None:
    """初始化会话表结构（幂等）。"""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user','assistant')),
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
            ON messages(conversation_id, created_at, id)
            """
        )


def ensure_conversation(conversation_id: str, user_id: str) -> None:
    now = int(time.time())
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO conversations(id, user_id, created_at, updated_at)
            VALUES(?, ?, ?, ?)
            """,
            (conversation_id, user_id, now, now),
        )
        conn.execute(
            """
            UPDATE conversations SET updated_at = ?
            WHERE id = ?
            """,
            (now, conversation_id),
        )


def add_message(conversation_id: str, role: str, content: str) -> None:
    if role not in ("user", "assistant"):
        raise ValueError("role must be 'user' or 'assistant'")
    now = int(time.time())
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO messages(conversation_id, role, content, created_at)
            VALUES(?, ?, ?, ?)
            """,
            (conversation_id, role, content, now),
        )


def load_messages(conversation_id: str, max_messages: int) -> list:
    """按创建时间倒序取最新 max_messages，再反转为时间正序返回。"""
    if max_messages <= 0:
        return []
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (conversation_id, max_messages),
        ).fetchall()

    # rows 已按倒序取出，需反转回正序喂给模型
    rows.reverse()

    messages: list = []
    for role, content in rows:
        if role == "user":
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))
    return messages

