"""
会话历史 HTTP 接口：读 MySQL 中 Python Agent 写入的 conversations / messages。
鉴权与 WebSocket 一致：调用 Java 校验 Blade token。
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query

from models.conversation import ConversationItem, MessageItem
from service.auth_service import validate_token
from utils.conversation_db import list_conversations_for_user, list_messages_for_user

router = APIRouter(tags=["conversation"])


def _extract_token(
    authorization: Optional[str] = None,
    blade_auth: Optional[str] = None,
) -> Optional[str]:
    if authorization:
        a = authorization.strip()
        if a.lower().startswith("bearer "):
            return a[7:].strip()
    if blade_auth:
        b = blade_auth.strip()
        if b.lower().startswith("bearer "):
            return b[7:].strip()
        return b
    return None


async def require_auth_user(
    authorization: Annotated[Optional[str], Header(alias="Authorization")] = None,
    blade_auth: Annotated[Optional[str], Header(alias="Blade-Auth")] = None,
) -> dict:
    token = _extract_token(authorization, blade_auth)
    if not token:
        raise HTTPException(status_code=401, detail="未提供 token（Authorization: Bearer 或 Blade-Auth）")
    ok, user_info = await validate_token(token)
    if not ok or not user_info:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    return user_info


@router.get("/conversations", response_model=list[ConversationItem])
async def get_conversation_list(
    user: dict = Depends(require_auth_user),
    limit: int = Query(50, ge=1, le=100),
):
    """拉取当前登录用户的历史会话列表。"""
    uid = user.get("user_id")
    if uid is None:
        raise HTTPException(status_code=401, detail="用户信息缺少 user_id")
    rows = list_conversations_for_user(str(uid), limit)
    return [ConversationItem(**r) for r in rows]


@router.get("/conversations/{thread_id}/messages", response_model=list[MessageItem])
async def get_conversation_messages(
    thread_id: str = Path(..., description="会话 thread_id"),
    user: dict = Depends(require_auth_user),
):
    """拉取某会话下的全部消息（须为该会话所有者）。"""
    uid = user.get("user_id")
    if uid is None:
        raise HTTPException(status_code=401, detail="用户信息缺少 user_id")
    messages = list_messages_for_user(thread_id, str(uid))
    if messages is None:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")
    return [MessageItem(**m) for m in messages]
