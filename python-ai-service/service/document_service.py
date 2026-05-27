import os
from utils.file_utils import (
    download_file_from_url,
    get_file_extension,
    extract_text_from_txt,
    download_to_local
)
from utils.milvus_utils import removeData
from config import (
    MILVUS_URI,
    MILVUS_COLLECTION_NAME,
    MINERU_API_KEY
)

from langchain_community.embeddings import DashScopeEmbeddings
from llama_index.core import Settings
from llama_index.embeddings.langchain import LangchainEmbedding
from llama_index.readers.mineru import MinerUReader
from langchain_openai import ChatOpenAI
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.extractors import TitleExtractor
from llama_index.vector_stores.milvus import MilvusVectorStore

from llama_index.core.ingestion import IngestionPipeline
from llama_index.core import Document
from pymilvus import DataType
from pymilvus import MilvusClient

# 设置llamaIndex默认嵌入和问答模型
Settings.embed_model = LangchainEmbedding(langchain_embeddings=DashScopeEmbeddings(model="text-embedding-v4"))
Settings.llm = ChatOpenAI(model="qwen-plus", temperature=0.7)

# ── 模块级单例 ────────────────────────────────────────
# MinerU解析器
_mineru_reader = MinerUReader(
    mode="precision",
    token=MINERU_API_KEY
)
# 语义切割器
_splitter = SentenceSplitter(chunk_size=500, chunk_overlap=50)
# 标题元数据标签器
_title_extractor = TitleExtractor(nodes=5)
# milvus向量数据库客户端
_vector_store = MilvusVectorStore(
    uri=MILVUS_URI,
    dim=1024,
    overwrite=True,
    enable_dynamic_field=True,
    collection_name=MILVUS_COLLECTION_NAME,
    scalar_field_names=["record_id", "type", "access_level"], # 关键参数：定义独立字段名
    scalar_field_types=[DataType.VARCHAR,DataType.VARCHAR,DataType.VARCHAR], # 关键参数：定义独立字段类型
)


TMP_SAVE_DIR: str = r"D:\MY\ai-knowledge-platform\python-ai-service\temp"

_scalar_indexes_ready = False  # 模块级标记

def _ensure_scalar_indexes():
    global _scalar_indexes_ready
    if _scalar_indexes_ready:
        return  # 已经建过了，跳过
    client = MilvusClient(uri=MILVUS_URI)
    if not client.has_collection(MILVUS_COLLECTION_NAME):
        return  # 集合还不存在
    existing = client.list_indexes(MILVUS_COLLECTION_NAME)
    if "ref_doc_id" in existing:
        _scalar_indexes_ready = True  # 索引已存在，标记完成
        return
    params = client.prepare_index_params()
    params.add_index("record_id", index_type="INVERTED",params={"json_cast_type":"varchar"})
    params.add_index("type", index_type="BITMAP",params={"json_cast_type":"varchar"})
    params.add_index("access_level", index_type="BITMAP",params={"json_cast_type":"varchar"})
    client.create_index(MILVUS_COLLECTION_NAME, params)
    _scalar_indexes_ready = True

def upload_document_data(id: str, file_url: str, doc_type: str, access_level: str):
    """
    下载、解析、切片、向量化并存入 Milvus。

    Args:
        id:           文档记录 ID（对应 Java 服务的主键）
        file_url:     文档下载地址
        doc_type:     文档类型: policy | tech
        access_level: 权限等级: public | internal | hr_only | project
    """
    try:
        # 1. 下载文件
        print(f"正在下载文件: {file_url}")
        file_content = download_file_from_url(file_url)
        print(f"文件下载成功，大小: {len(file_content)} bytes")
        if len(file_content) == 0:
            raise Exception("文件内容为空")

        # 2. 文档解析
        file_ext = get_file_extension(file_url)
        print(f"文件类型: {file_ext}")

        if file_ext == "docx" or file_ext == "pdf":
            file_path = download_to_local(url=file_url, save_dir=TMP_SAVE_DIR)
            try:
                documents = _mineru_reader.load_data(
                    file_path,
                    extra_info={
                        "record_id": id,
                        "type": doc_type,
                        "access_level": access_level,
                    },
                )
            finally:
                if file_path and os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                        print(f"已删除临时文件: {file_path}")
                    except OSError as e:
                        print(f"删除临时文件失败: {file_path}, {e}")
        elif file_ext in ("txt", "md"):
            documents = [Document(
                text=extract_text_from_txt(file_content),
                metadata={"record_id": id, "type": doc_type, "access_level": access_level},
            )]
        else:
            raise Exception(f"不支持的文件类型: {file_ext}")

        print(f"文本提取成功，长度: {len(documents)} 个文档")

        # 3.编排数据处理管线
        pipeline = IngestionPipeline(
            transformations=[
                _splitter,
                _title_extractor,
                Settings.embed_model,
            ],
            vector_store=_vector_store
        )

        # 4.执行管线
        nodes = pipeline.run(documents=documents, show_progress=True)

        if nodes and len(nodes) > 0:
            _ensure_scalar_indexes()
            return True

        return False

    except Exception as e:
        print(f"处理文档失败: {str(e)}")
        raise


def remove_document_data(id: str):
    return removeData(MILVUS_COLLECTION_NAME, id)
