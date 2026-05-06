"""会话历史 API 的响应模型。"""

from pydantic import BaseModel, Field


class ConversationItem(BaseModel):
    """会话摘要（与 MySQL conversations 表对应）。"""

    thread_id: str = Field(description="会话 ID，即 WebSocket 使用的 thread_id")
    user_id: str
    created_at: int = Field(description="创建时间 Unix 秒")
    updated_at: int = Field(description="最近更新时间 Unix 秒")


class MessageItem(BaseModel):
    """单条聊天记录。"""

    role: str = Field(description="user 或 assistant")
    content: str
    created_at: int = Field(description="创建时间 Unix 秒")
