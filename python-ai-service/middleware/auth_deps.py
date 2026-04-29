"""
认证依赖：提供便捷的依赖注入函数
"""
from fastapi import Request, HTTPException, status, Header
from typing import Optional, Dict


def get_current_user(request: Request) -> Dict:
    """
    从 request.state 中获取当前用户信息
    
    使用方式：
        from middleware.auth_deps import get_current_user
        
        @router.get("/some-endpoint")
        def some_function(user: Dict = Depends(get_current_user)):
            user_id = user["user_id"]
            ...
    
    Returns:
        用户信息字典
    
    Raises:
        HTTPException: 如果用户信息不存在（理论上不会发生，因为中间件已验证）
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未找到用户信息"
        )
    return user


def get_current_token(request: Request) -> str:
    """
    从 request.state 中获取当前 token
    
    Returns:
        token 字符串
    """
    token = getattr(request.state, "token", None)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未找到认证令牌"
        )
    return token


async def get_optional_user(request: Request) -> Optional[Dict]:
    """
    获取可选的用户信息（不强制要求登录）
    
    Returns:
        用户信息字典，如果未登录返回 None
    """
    return getattr(request.state, "user", None)
