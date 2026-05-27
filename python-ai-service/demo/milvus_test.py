from config import (
    MILVUS_URI,
)
from llama_index.vector_stores.milvus import MilvusVectorStore
print(MILVUS_URI)
vector_store = MilvusVectorStore(uri=MILVUS_URI, dim=1024, overwrite=True)
print("vector_store")