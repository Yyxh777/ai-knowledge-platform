import config  # 确保 .env 加载并写入 os.environ
from typing import List
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.file_utils import (
    download_file_from_url,
    get_file_extension,
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_text_from_txt,
)
from config import MILVUS_COLLECTION_NAME
from utils.milvus_utils import createCollection, removeData, get_milvus_client

# ── 模块级单例：切片器参数统一在此处管理 ────────────────────────────────────────
# separators 按优先级从高到低排列：
#   1. 双换行（段落边界）2. 单换行  3. 中文句末标点  4. 中文逗号/分号
#   5. 英文句末标点  6. 空格  7. 空字符串（逐字符兜底，一般不会触发）
# chunk_size=500：约合 500 汉字，换算为 ~300~400 token，适合大多数 embedding 模型的上下文窗口
# chunk_overlap=50：10% 重叠，保证跨块语义的连贯性，防止关键句子被切断后两块都检索不到
_text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "！", "？", "；", "，", ".", "!", "?", " ", ""],
)
# ────────────────────────────────────────────────────────────────────────────────


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

        # 2. 按文件类型提取纯文本
        file_ext = get_file_extension(file_url)
        print(f"文件类型: {file_ext}")

        if file_ext == "docx":
            text = extract_text_from_docx(file_content)
        elif file_ext == "pdf":
            text = extract_text_from_pdf(file_content)
        elif file_ext in ("txt", "md"):
            text = extract_text_from_txt(file_content)
        else:
            raise Exception(f"不支持的文件类型: {file_ext}")

        print(f"文本提取成功，长度: {len(text)} 字符")

        # 3. 语义切片
        chunks: List[str] = _text_splitter.split_text(text)
        print(f"文本切片完成，共 {len(chunks)} 个文本块")

        # 4. 确保 Milvus 集合存在
        milvus_client = get_milvus_client()
        if not milvus_client.has_collection(MILVUS_COLLECTION_NAME):
            print(f"集合不存在，正在创建: {MILVUS_COLLECTION_NAME}")
            createCollection(MILVUS_COLLECTION_NAME)

        # 5. 批量向量化（一次 API 调用，性能远优于逐条调用）
        embeddings = DashScopeEmbeddings(model="text-embedding-v4")
        print(f"正在批量生成 {len(chunks)} 个文本块的向量...")
        vectors = embeddings.embed_documents(chunks)

        # 6. 组装数据并写入 Milvus
        print(f"文件记录id: {id}")
        data = [
            {
                "id":           f"{id}_{i}",   # 复合 ID，格式: "{record_id}_{chunk_index}"
                "vector":       vector,
                "text":         chunk,
                "record_id":    id,            # 用于按文件批量删除
                "type":         doc_type,
                "access_level": access_level,
            }
            for i, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]

        print(f"正在写入 Milvus: {MILVUS_COLLECTION_NAME}")
        milvus_client.insert(collection_name=MILVUS_COLLECTION_NAME, data=data)

        return True

    except Exception as e:
        print(f"处理文档失败: {str(e)}")
        raise


def remove_document_data(id: str):
    return removeData(MILVUS_COLLECTION_NAME, id)
