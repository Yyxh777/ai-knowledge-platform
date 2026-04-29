from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from models.chat import ChatRequest, ChatResponse
from service.rag_service import  chat_with_rag_stream
from service.auth_service import validate_token
from middleware.auth_deps import get_current_user
from typing import Dict
import json
import time

router = APIRouter()


async def safe_send(websocket: WebSocket, data: dict) -> bool:
    """
    安全发送 WebSocket 消息。
    连接已断开时静默忽略，不抛出异常。
    返回 True=发送成功，False=连接已断开
    """
    try:
        await websocket.send_json(data)
        return True
    except Exception:
        return False


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    # 接受客户端连接
    await websocket.accept()

    # 值初始化，防止连接断开时 except 出现异常，访问到未赋值变量
    user_info: Dict = {}
    token: str = ""

    try:
        # 获取客户端第一条消息（token认证消息）
        auth_data = await websocket.receive_text()
        auth_message = json.loads(auth_data)           
        token = auth_message.get("token", "")          

        # 若token为空，则返回
        if not token:
            await safe_send(websocket, {"type": "error", "content": "缺少 token，请先登录"})
            await websocket.close()
            return

        # token发送至Java服务进行校验
        is_valid, user_info = await validate_token(token)   
        if not is_valid:                                     
            await safe_send(websocket, {"type": "error", "content": "token 无效或已过期"})
            await websocket.close()
            return

        # 验证成功：conversation_id 使用 thread_id
        # 允许前端在重连时复用 thread_id；若未提供则生成新的
        user_id = str(user_info["user_id"])
        thread_id = auth_message.get("thread_id") or f"{user_id}_{int(time.time() * 1000)}"
        thread_id = str(thread_id)

        await safe_send(websocket, {
            "type":      "auth_success",
            "user": {
                "user_id":   user_id,
                "account":   user_info["account"],
            },
            "thread_id": thread_id,   # 告知前端本次会话 ID，方便调试或前端追踪
        })

        print(f"WebSocket 用户 {user_info['account']}({user_id}) 已连接，会话 thread_id={thread_id}")

        # 成功则进行消息循环
        while True:
            # 等待客户端消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            # 提取问题内容
            query = message_data.get("message", "")
            if not query:
                continue

            await safe_send(websocket, {"type": "start"})

            # 发送给 Agent，thread_id 由服务端控制，外部无法伪造
            try:
                async for chunk in chat_with_rag_stream(
                    query,
                    user_info=user_info,
                    access_token=token,
                    thread_id=thread_id,
                ):
                    # 流式响应持续获取内容并发送给客户端
                    await safe_send(websocket, {"type": "token", "content": chunk})  

                # 生成结束，放在 try 内，只有成功才发 end
                await safe_send(websocket, {"type": "end"})  

            except Exception as e:
                print(f"处理消息错误: {str(e)}")
                await safe_send(websocket, {
                    "type": "error",
                    "content": f"处理消息时出错: {str(e)}"
                })

    except WebSocketDisconnect:                                          
        print(f"用户 {user_info.get('account', '未认证用户')} 断开连接") 
    except json.JSONDecodeError:
        await safe_send(websocket, {"type": "error", "content": "消息格式错误"})
        await websocket.close()
    except Exception as e:
        print(f"WebSocket 错误: {str(e)}")
        await websocket.close()

