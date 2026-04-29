"""
认证中间件：拦截所有请求，验证 token
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from service.auth_service import validate_token, extract_token_from_header


class AuthMiddleware(BaseHTTPMiddleware):
    """
    认证中间件
    拦截所有请求，从请求头中提取 token 并验证
    """
    
    # 不需要认证的路径（白名单）
    SKIP_AUTH_PATHS = [
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/ai/ws/chat",  # WebSocket 连接后自行认证
    ]
    
    async def dispatch(self, request: Request, call_next):
        # 跳过 OPTIONS 预检请求（CORS）
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # 检查是否在白名单中
        if any(request.url.path.startswith(path) for path in self.SKIP_AUTH_PATHS):
            return await call_next(request)
        
        # 从请求头中提取 token
        # 支持两种请求头：Blade-Auth 或 Authorization
        auth_header = request.headers.get("Blade-Auth") or request.headers.get("Authorization")
        token = extract_token_from_header(auth_header)
        
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "code": 401,
                    "success": False,
                    "msg": "缺少认证令牌",
                }
            )
        
        # 验证 token
        is_valid, user_info = await validate_token(token, use_cache=True)
        
        if not is_valid:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "code": 401,
                    "success": False,
                    "msg": "认证令牌无效或已过期",
                }
            )
        
        # 将用户信息添加到 request.state，供后续使用
        request.state.user = user_info
        request.state.token = token
        
        # 继续处理请求
        response = await call_next(request)
        return response
