"""

MinerU + LlamaIndex 向量检索示例。



与 rag_graph 对齐：

  - 嵌入：DashScope text-embedding-v4（需 DASHSCOPE_API_KEY，由 config 从 .env 加载）；

  - 问答 LLM：qwen-plus（与 rag_graph 中 ChatOpenAI 一致，需 OPENAI_API_KEY / OPENAI_BASE_URL）。

"""

import sys

from pathlib import Path

_root = Path(__file__).resolve().parent.parent

if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import config  # noqa: F401 — 加载 .env

from langchain_community.embeddings import DashScopeEmbeddings
from llama_index.core import Settings, VectorStoreIndex
from llama_index.embeddings.langchain import LangchainEmbedding
from llama_index.readers.mineru import MinerUReader
from langchain_openai import ChatOpenAI

# 设置llamaIndex默认嵌入和问答模型
Settings.embed_model = LangchainEmbedding(langchain_embeddings=DashScopeEmbeddings(model="text-embedding-v4"))
Settings.llm = ChatOpenAI(model="qwen-plus", temperature=0.7)

# TEST_FILE_PATH = r"D:\MY\ai-knowledge-platform\java-service\src\main\resources\doc\员工手册-宏算科技-2025.pdf"
TEST_FILE_PATH = r"D:\work_data\集中申报\AI审查业务场景.docx"
TOKEN = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiI5NTYwMDYzMSIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc3ODc0Mzk3NSwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiIiwib3BlbklkIjpudWxsLCJ1dWlkIjoiZDA2ZWEwNWEtOWFjYy00NTBlLTkwOTYtNzM1NzkwNjY1YWRjIiwiZW1haWwiOiIiLCJleHAiOjE3ODY1MTk5NzV9.SWmWWvAL2TjQzGc2ZujyvZkgrf64Y0tNi0B1iP3Wd1aV1twCTLBw_OTSF2g86SgJPPPehhbC11wtGBbPHDi0eQ"
reader = MinerUReader()

documents = reader.load_data(TEST_FILE_PATH)

for doc in documents:
    print(f"页码{doc.metadata.get('page')}：内容：{doc.text}")

from llama_index.core.node_parser import SentenceSplitter, MarkdownNodeParser
#
# sentenceSplitter = SentenceSplitter(chunk_size=500,chunk_overlap=50)
# docs_a = sentenceSplitter.get_nodes_from_documents(documents)
# print(len(docs_a))
# for i,doc in enumerate(docs_a,1):
#     print(f"第{i}块内容：{doc.text}\n")
#
# print("-"*50)
markdownNodeParser = MarkdownNodeParser()
docs_b = markdownNodeParser.get_nodes_from_documents(documents)
print(len(docs_b))
# for i,doc in enumerate(docs_b,1):
#     print(f"第{i}块内容：{doc.text}\n")
#     print(f"    metadata: {doc.metadata}")
paths = set()
for node in docs_b:
    paths.add(node.metadata.get("header_path", "无"))
print(f"共 {len(paths)} 种 header_path：")
for p in sorted(paths):
    count = sum(1 for n in docs_b if n.metadata.get("header_path") == p)
    print(f"  '{p}' → {count} 个块")