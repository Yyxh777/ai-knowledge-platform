from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.chat import router as chat_router
from api.conversation import router as conversation_router
from api.document import router as document_router
from middleware.auth_middleware import AuthMiddleware
from service.rag_service import startup as rag_startup, shutdown as rag_shutdown


@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理应用生命周期：启动时初始化 PostgreSQL checkpoint 池与 LangGraph，关闭时释放。"""
    await rag_startup()
    yield
    await rag_shutdown()


app = FastAPI(lifespan=lifespan)

# 配置 CORS（允许跨域）- 必须在认证中间件之前
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8081", "http://localhost:8080", "*"],  # 明确指定允许的源
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # 明确包含 OPTIONS
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # 预检请求缓存时间（秒）
)

# 添加认证中间件（重要！）
# app.add_middleware(AuthMiddleware)

# 注册路由
app.include_router(chat_router, prefix="/ai")
app.include_router(conversation_router, prefix="/ai")
app.include_router(document_router, prefix="/ai")

# 健康检查接口（不需要认证）
@app.get("/health")
def health_check():
    return {"status": "ok"}