"""
认证服务：通过调用 Java 服务验证 token 的有效性
"""
import httpx
import time
import logging
from typing import Optional, Dict, Tuple
from config import (
    TOKEN_VALIDATE_ENDPOINT,
    TOKEN_CACHE_TTL,
    ENABLE_TOKEN_CACHE,
    JAVA_SERVICE_TIMEOUT,
    JAVA_CLIENT_CREDENTIALS,
    JAVA_REQUESTED_WITH,
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 统计信息
class AuthStats:
    """认证统计信息"""
    def __init__(self):
        self.total_validations = 0
        self.cache_hits = 0
        self.validation_success = 0
        self.validation_failure = 0
        self.java_service_errors = 0
    
    def get_stats(self) -> Dict:
        cache_hit_rate = (self.cache_hits / self.total_validations * 100) if self.total_validations > 0 else 0
        return {
            "total_validations": self.total_validations,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": f"{cache_hit_rate:.2f}%",
            "validation_success": self.validation_success,
            "validation_failure": self.validation_failure,
            "java_service_errors": self.java_service_errors,
        }

auth_stats = AuthStats()


class TokenCache:
    """简单的 token 缓存机制，避免频繁调用 Java 服务"""
    def __init__(self):
        self.cache: Dict[str, Tuple[Dict, float]] = {}
    
    def get(self, token: str) -> Optional[Dict]:
        if token in self.cache:
            user_info, expire_time = self.cache[token]
            if time.time() < expire_time:
                return user_info
            else:
                del self.cache[token]
        return None
    
    def set(self, token: str, user_info: Dict, ttl: int = TOKEN_CACHE_TTL):
        expire_time = time.time() + ttl
        self.cache[token] = (user_info, expire_time)
    
    def clear(self, token: str):
        if token in self.cache:
            del self.cache[token]
    
    def size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)
    
    def cleanup_expired(self):
        """清理过期的缓存"""
        current_time = time.time()
        expired_tokens = [
            token for token, (_, expire_time) in self.cache.items()
            if expire_time < current_time
        ]
        for token in expired_tokens:
            del self.cache[token]
        return len(expired_tokens)


# 全局缓存实例
token_cache = TokenCache()


async def validate_token(token: str, use_cache: bool = True) -> Tuple[bool, Optional[Dict]]:
    """
    验证 token 是否有效，并返回用户信息
    
    Args:
        token: JWT token 字符串
        use_cache: 是否使用缓存（默认 True）
    
    Returns:
        (is_valid, user_info): 
            - is_valid: token 是否有效
            - user_info: 用户信息字典，包含 userId, tenantId, account, realName 等
    """
    auth_stats.total_validations += 1
    
    if not token:
        auth_stats.validation_failure += 1
        return False, None
    
    # 检查缓存
    if use_cache and ENABLE_TOKEN_CACHE:
        cached_user = token_cache.get(token)
        if cached_user:
            auth_stats.cache_hits += 1
            auth_stats.validation_success += 1
            logger.debug(f"Token 缓存命中: {cached_user.get('account')}")
            return True, cached_user
    
    try:
        # 调用 Java 服务验证 token
        logger.debug(f"调用 Java 服务验证 token: {TOKEN_VALIDATE_ENDPOINT}")
        
        async with httpx.AsyncClient(timeout=JAVA_SERVICE_TIMEOUT) as client:
            response = await client.get(
                TOKEN_VALIDATE_ENDPOINT,
                headers={
                    "Blade-Auth":           f"bearer {token}",
                    "Authorization":        JAVA_CLIENT_CREDENTIALS,
                    "Blade-Requested-With": JAVA_REQUESTED_WITH,
                }
            )
            
            logger.debug(f"Java 服务响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                # token 有效，解析用户信息
                result = response.json()
                logger.debug(f"Java 服务响应: {result}")
                
                if result.get("code") == 200 and result.get("success"):
                    user_info = result.get("data", {})
                    
                    # 提取关键用户信息
                    user_data = {
                        "user_id": user_info.get("id"),
                        "tenant_id": user_info.get("tenantId"),
                        "account": user_info.get("account"),
                        "real_name": user_info.get("realName"),
                        "name": user_info.get("name"),
                        "dept_id": user_info.get("deptId"),
                        "role_id": user_info.get("roleId"),
                        "role_name": user_info.get("roleName"),
                    }
                    
                    # 缓存验证结果
                    if use_cache and ENABLE_TOKEN_CACHE:
                        token_cache.set(token, user_data)
                    
                    auth_stats.validation_success += 1
                    logger.info(f"Token 验证成功: {user_data.get('account')}")
                    return True, user_data
            
            # token 无效（401、403 等）
            auth_stats.validation_failure += 1
            logger.warning(f"Token 验证失败: HTTP {response.status_code}")
            return False, None
            
    except httpx.TimeoutException:
        # 超时，为了安全起见返回验证失败
        auth_stats.java_service_errors += 1
        logger.error(f"Token 验证超时: {TOKEN_VALIDATE_ENDPOINT}")
        return False, None
    except Exception as e:
        # 其他异常，记录日志
        auth_stats.java_service_errors += 1
        logger.error(f"Token 验证异常: {str(e)}")
        return False, None


async def get_user_info_by_token(token: str) -> Optional[Dict]:
    """
    通过 token 获取用户信息（便捷方法）
    
    Args:
        token: JWT token 字符串
    
    Returns:
        用户信息字典，如果 token 无效返回 None
    """
    is_valid, user_info = await validate_token(token)
    return user_info if is_valid else None


def extract_token_from_header(auth_header: Optional[str]) -> Optional[str]:
    """
    从请求头中提取 token
    
    Args:
        auth_header: Authorization 或 Blade-Auth 请求头的值
    
    Returns:
        提取的 token 字符串，如果格式不正确返回 None
    """
    if not auth_header:
        return None
    
    # 支持 "Bearer <token>" 或 "bearer <token>" 格式（不区分大小写）
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:]
    
    # 支持直接传 token
    return auth_header


def check_user_access_level(user_info: Dict, required_access_level: str, access_levels: list = None) -> bool:
    """
    检查用户是否有权限访问特定级别的资源。

    权限数据来源：Java 服务为每个用户维护一张 access_level 表，
    并通过角色关联表决定该用户拥有哪些 level（返回为字符串数组）。
    本函数只做集合包含判断，不在 Python 侧猜测角色与权限的映射关系。

    Args:
        user_info:              已认证的用户信息字典
        required_access_level:  文档所要求的访问级别，如 "public" / "internal" / "hr_only" / "project"
        access_levels:          用户实际拥有的权限级别列表，由调用方从 Java 服务获取后传入；
                                若不传则从 user_info["access_levels"] 取，仍为空则拒绝访问。

    Returns:
        True = 有权限；False = 无权限
    """
    # public 文档任何已登录用户均可访问
    if required_access_level == "public":
        return True

    # 从参数或 user_info 中取用户实际拥有的 access_levels
    if access_levels is None:
        access_levels = user_info.get("access_levels", [])

    # 若没有任何权限数据，按最小权限原则拒绝访问（fail-secure）
    if not access_levels:
        logger.warning(
            f"用户 {user_info.get('account')} 的 access_levels 为空，拒绝访问 '{required_access_level}'"
        )
        return False

    # 核心逻辑：用户的 access_levels 里包含所需级别，即允许访问
    return required_access_level in access_levels


def get_auth_stats() -> Dict:
    """获取认证统计信息"""
    return auth_stats.get_stats()


def clear_token_cache():
    """清空 token 缓存"""
    token_cache.cache.clear()
    logger.info("Token 缓存已清空")

