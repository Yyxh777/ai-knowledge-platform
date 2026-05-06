# Python AI Service - 认证代码完整回顾

## 文件结构

```
python-ai-service/
├── middleware/
│   ├── auth_middleware.py    # 拦截所有请求
│   └── auth_deps.py          # 获取用户信息工具
├── service/
│   └── auth_service.py       # 验证 token 核心逻辑
├── api/
│   ├── chat.py              # 聊天接口
│   └── document.py          # 文档接口
├── main.py                  # 启动入口
└── .env                     # 配置文件
```

---

## 1. auth_service.py - 验证 token 核心逻辑

```python
import httpx
import os
from typing import Optional, Dict, Tuple
import time

# 配置
JAVA_SERVICE_URL = os.getenv("JAVA_SERVICE_URL", "http://localhost:8080")
TOKEN_VALIDATE_ENDPOINT = f"{JAVA_SERVICE_URL}/blade-system/user/info"
TOKEN_CACHE_TTL = 300  # 5分钟缓存

# 缓存类
class TokenCache:
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

token_cache = TokenCache()

# 核心验证函数
async def validate_token(token: str, use_cache: bool = True) -> Tuple[bool, Optional[Dict]]:
    """验证 token 是否有效"""
    if not token:
        return False, None
    
    # 1. 先查缓存
    if use_cache:
        cached_user = token_cache.get(token)
        if cached_user:
            return True, cached_user
    
    # 2. 调用 Java 服务
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                TOKEN_VALIDATE_ENDPOINT,
                headers={"Blade-Auth": f"bearer {token}"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 200 and result.get("success"):
                    user_info = result.get("data", {})
                    
                    # 3. 提取用户信息
                    user_data = {
                        "user_id": user_info.get("id"),
                        "tenant_id": user_info.get("tenantId"),
                        "account": user_info.get("account"),
                        "real_name": user_info.get("realName"),
                        "role_name": user_info.get("roleName"),
                    }
                    
                    # 4. 存入缓存
                    if use_cache:
                        token_cache.set(token, user_data)
                    
                    return True, user_data
            
            return False, None
            
    except Exception as e:
        print(f"验证失败: {str(e)}")
        return False, None

# 工具函数：从请求头提取 token
def extract_token_from_header(auth_header: Optional[str]) -> Optional[str]:
    """从 'Bearer abc123' 中提取 'abc123'"""
    if not auth_header:
        return None
    
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:]
    
    return auth_header
```

---

## 2. auth_middleware.py - 拦截所有请求

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from service.auth_service import validate_token, extract_token_from_header

class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件：拦截所有请求并验证 token"""
    
    # 白名单：这些路径不需要验证
    SKIP_AUTH_PATHS = [
        "/docs",
        "/health",
    ]
    
    async def dispatch(self, request: Request, call_next):
        # 1. 检查白名单
        if any(request.url.path.startswith(path) for path in self.SKIP_AUTH_PATHS):
            return await call_next(request)
        
        # 2. 提取 token
        auth_header = request.headers.get("Blade-Auth") or request.headers.get("Authorization")
        token = extract_token_from_header(auth_header)
        
        if not token:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "success": False, "msg": "缺少认证令牌"}
            )
        
        # 3. 验证 token
        is_valid, user_info = await validate_token(token, use_cache=True)
        
        if not is_valid:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "success": False, "msg": "认证令牌无效或已过期"}
            )
        
        # 4. 保存用户信息到 request.state
        request.state.user = user_info
        request.state.token = token
        
        # 5. 放行请求
        return await call_next(request)
```

---

## 3. auth_deps.py - 获取用户信息工具

```python
from fastapi import Request, HTTPException

def get_current_user(request: Request) -> dict:
    """从 request.state 中获取当前用户信息"""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="未找到用户信息")
    return user
```

**用法**：
```python
def some_function(user: dict = Depends(get_current_user)):
    user_id = user["user_id"]      # 获取用户ID
    account = user["account"]      # 获取账号
    role = user["role_name"]       # 获取角色
```

---

## 4. main.py - 启动入口

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.chat import router as chat_router
from api.document import router as document_router
from middleware.auth_middleware import AuthMiddleware

app = FastAPI()

# 配置 CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# 注册认证中间件（重要！）
app.add_middleware(AuthMiddleware)

# 注册路由
app.include_router(chat_router, prefix="/ai")
app.include_router(document_router, prefix="/ai")

@app.get("/health")
def health_check():
    return {"status": "ok"}
```

---

## 5. document.py - 文档接口示例

```python
from fastapi import APIRouter, Depends
from middleware.auth_deps import get_current_user

router = APIRouter()

@router.post("/uploadDocument")
def upload_document(req: UploadDocumentRequest, user: dict = Depends(get_current_user)):
    """上传文档（需要登录）"""
    # 可以使用用户信息
    print(f"用户 {user['account']}({user['user_id']}) 上传文档")
    
    result = upload_document_data(req.id, req.file_url, req.doc_type, req.access_level)
    return result

@router.delete("/removeDocument")
def remove_document(id: str, user: dict = Depends(get_current_user)):
    """删除文档（需要登录）"""
    print(f"用户 {user['account']} 删除文档: {id}")
    
    result = remove_document_data(id)
    return result
```

---

## 6. chat.py - 聊天接口示例

```python
from fastapi import APIRouter, Depends
from middleware.auth_deps import get_current_user

router = APIRouter()

@router.post("/chat")
def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    """聊天接口（需要登录）"""
    print(f"用户 {user['account']} 发起聊天")
    
    answer = chat_with_rag(req.query)
    return ChatResponse(answer=answer)
```

---

## 7. .env - 配置文件

```bash
# Java 服务地址
JAVA_SERVICE_URL=http://localhost:8080

# Token 缓存时间（秒）
TOKEN_CACHE_TTL=300

# 是否启用缓存
ENABLE_TOKEN_CACHE=true
```

---

## 执行流程

```
1. 客户端请求：
   POST /ai/chat
   Headers: { "Blade-Auth": "bearer abc123" }

2. AuthMiddleware 拦截：
   - 提取 token = "abc123"
   - 调用 validate_token("abc123")

3. auth_service.py 验证：
   - 先查缓存（没有）
   - 调用 Java 服务
   - 返回 user_info = {"user_id": "1", "account": "admin"}

4. AuthMiddleware 继续：
   - request.state.user = user_info
   - 放行请求

5. chat() 函数执行：
   - Depends(get_current_user) 自动调用
   - user = {"user_id": "1", "account": "admin"}
   - 执行业务逻辑

6. 返回结果给客户端
```

---

## 用户信息字段

```python
user = {
    "user_id": "1",           # 用户ID
    "tenant_id": "000000",    # 租户ID
    "account": "admin",       # 账号
    "real_name": "管理员",     # 真实姓名
    "role_name": "administrator"  # 角色名
}
```

---

## 启动命令

```bash
# 开发环境
fastapi dev main.py

# 或者
uvicorn main:app --reload
```

---

## 关键点总结

1. **验证逻辑**：auth_service.py（先缓存，后 Java）
2. **拦截请求**：auth_middleware.py（自动验证所有接口）
3. **注册中间件**：main.py 的 `app.add_middleware(AuthMiddleware)`
4. **使用用户信息**：接口参数加 `user: dict = Depends(get_current_user)`
5. **配置地址**：.env 的 `JAVA_SERVICE_URL`
