import sys

from pathlib import Path

_root = Path(__file__).resolve().parent.parent

if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import config  # noqa: F401 — 加载 .env
from config import (
    MILVUS_URI,
)

from langchain_community.embeddings import DashScopeEmbeddings
from llama_index.core import Settings, VectorStoreIndex
from llama_index.embeddings.langchain import LangchainEmbedding
from llama_index.readers.mineru import MinerUReader
from langchain_openai import ChatOpenAI
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.extractors import TitleExtractor, QuestionsAnsweredExtractor
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.core import VectorStoreIndex
from llama_index.core.ingestion import IngestionPipeline


# 设置llamaIndex默认嵌入和问答模型
Settings.embed_model = LangchainEmbedding(langchain_embeddings=DashScopeEmbeddings(model="text-embedding-v4"))
Settings.llm = ChatOpenAI(model="qwen-plus", temperature=0.7)

# TEST_FILE_PATH = r"D:\MY\ai-knowledge-platform\java-service\src\main\resources\doc\员工手册-宏算科技-2025.pdf"
TEST_FILE_PATH = r"D:\MY\ai-knowledge-platform\java-service\src\main\resources\doc\bladeX-Lombok.md"
TOKEN = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiI5NTYwMDYzMSIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc3ODc0Mzk3NSwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiIiwib3BlbklkIjpudWxsLCJ1dWlkIjoiZDA2ZWEwNWEtOWFjYy00NTBlLTkwOTYtNzM1NzkwNjY1YWRjIiwiZW1haWwiOiIiLCJleHAiOjE3ODY1MTk5NzV9.SWmWWvAL2TjQzGc2ZujyvZkgrf64Y0tNi0B1iP3Wd1aV1twCTLBw_OTSF2g86SgJPPPehhbC11wtGBbPHDi0eQ"


# 1. 文档解析（已有）
documents = MinerUReader(
    mode="precision",
    token=TOKEN,
).load_data(TEST_FILE_PATH)
print("minerU解析结束")

# 2. 数据清洗（最简版：去掉空白/过短的文档）
documents = [d for d in documents if len(d.text.strip()) > 50]

# 3. 切块（最简版：SentenceSplitter）
splitter = SentenceSplitter(chunk_size=500, chunk_overlap=50)

# 4. 元数据标签（最简版：TitleExtractor，用 LLM 自动提取标题）
title_extractor = TitleExtractor(nodes=5)
# qa_extractor = QuestionsAnsweredExtractor(questions=3)

# 5. 入 Milvus（用 LlamaIndex 的 MilvusVectorStore）
vector_store = MilvusVectorStore(uri=MILVUS_URI, dim=1024, overwrite=True)

pipeline = IngestionPipeline(
    transformations=[
        splitter,
        title_extractor,
        Settings.embed_model
    ],
    vector_store=vector_store
)
nodes = pipeline.run(
    documents=documents,
    show_progress=True,
)

for i, node in enumerate(nodes[:3]):
    print(f"=== 块{i+1} ===")
    for k, v in node.metadata.items():
        print(f"  {k}: {v}")


index = VectorStoreIndex.from_vector_store(vector_store)
query_engine = index.as_query_engine(similarity_top_k=5)
print(query_engine.query("电力行业的市场风险是什么？"))