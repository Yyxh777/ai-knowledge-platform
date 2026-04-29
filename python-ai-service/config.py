"""
集中配置入口。

职责：
  1. 以 config.py 所在目录（python-ai-service/）定位 .env，无论从哪个工作目录启动都能正确加载。
  2. 将所有环境变量解析为类型明确的常量，统一在此处完成类型转换和默认值处理。
  3. 写入 os.environ，供 LangChain 等依赖 os.environ 的第三方库读取。

其他模块统一 `from config import XXX`，不再各自调用 load_dotenv 或 os.getenv。
"""

import os
import dotenv
import logging
from pathlib import Path

# 以 config.py 自身位置定位 .env，路径与启动目录无关
dotenv.load_dotenv(Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)

# ── LLM / OpenAI Compatible API ──────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")

# LangChain / LangSmith 通过 os.environ 读取这些值，必须显式写入
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["OPENAI_BASE_URL"] = OPENAI_BASE_URL
os.environ["DASHSCOPE_API_KEY"] = DASHSCOPE_API_KEY

# ── Milvus ────────────────────────────────────────────────────────────────────
MILVUS_URI: str = os.getenv("MILVUS_URI", "http://localhost:19530")
MILVUS_COLLECTION_NAME: str = os.getenv("MILVUS_COLLECTION_NAME", "document_collection")

# ── Redis（会话记忆 Checkpointer）─────────────────────────────────────────────
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_TTL_SEC: int = int(os.getenv("REDIS_TTL_SEC", "86400"))  # 默认保留 1 天

# ── Java 服务 ─────────────────────────────────────────────────────────────────
JAVA_SERVICE_URL: str = os.getenv("JAVA_SERVICE_URL", "http://localhost:8081")
# 完整的 token 验证地址：Java 服务地址 + 接口路径
TOKEN_VALIDATE_ENDPOINT: str = f"{JAVA_SERVICE_URL}{os.getenv('TOKEN_VALIDATE_ENDPOINT', '/blade-system/user/info')}"
# HTTP 请求超时时间（秒）
JAVA_SERVICE_TIMEOUT: float = float(os.getenv("JAVA_SERVICE_TIMEOUT", "5.0"))
# BladeX 客户端凭证：格式为 "Basic base64(client_id:client_secret)"
# 默认值 c2FiZXIzOnNhYmVyM19zZWNyZXQ= 是 saber3:saber3_secret 的 Base64 编码
JAVA_CLIENT_CREDENTIALS: str = os.getenv(
    "JAVA_CLIENT_CREDENTIALS",
    "Basic c2FiZXIzOnNhYmVyM19zZWNyZXQ=",
)
# BladeX 专用请求标识头，固定值，但允许通过环境变量覆盖
JAVA_REQUESTED_WITH: str = os.getenv("JAVA_REQUESTED_WITH", "BladeHttpRequest")

# ── 认证配置 ──────────────────────────────────────────────────────────────────
TOKEN_CACHE_TTL: int = int(os.getenv("TOKEN_CACHE_TTL", "300"))
ENABLE_TOKEN_CACHE: bool = os.getenv("ENABLE_TOKEN_CACHE", "true").lower() == "true"

# ── MySQL（个人数据查询）─────────────────────────────────────────────────────
MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "aikp")

# ── 服务启动配置 ──────────────────────────────────────────────────────────────
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))
RELOAD: bool = os.getenv("RELOAD", "false").lower() == "true"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ── 启动时校验关键配置，避免运行到一半才报错 ─────────────────────────────────
_REQUIRED = {
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "OPENAI_BASE_URL": OPENAI_BASE_URL,
    "DASHSCOPE_API_KEY": DASHSCOPE_API_KEY,
    "MILVUS_URI": MILVUS_URI,
}
for _key, _val in _REQUIRED.items():
    if not _val:
        logger.warning("⚠️  配置项 %s 未设置，请检查 .env 文件", _key)
