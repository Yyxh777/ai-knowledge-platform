import sys
from pathlib import Path

# 直接运行本脚本时，把项目根目录加入 path，才能 import config
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from pymilvus import MilvusClient, Collection, connections, DataType
from config import MILVUS_URI, MILVUS_COLLECTION_NAME

# 模块级单例：进程内复用同一个连接，避免每次函数调用都重新建立 TCP 连接
_milvus_client = MilvusClient(uri=MILVUS_URI)


def get_milvus_client() -> MilvusClient:
    return _milvus_client


def removeDocumentData(id: str):
    return removeData(MILVUS_COLLECTION_NAME, id)


def createCollection(collection_name: str) -> bool:
    milvus_client = get_milvus_client()

    # 幂等：集合已存在则跳过，不抛 duplicate 异常
    if milvus_client.has_collection(collection_name):
        print(f"集合 '{collection_name}' 已存在，跳过创建")
        return True
    # 创建schema
    schema = milvus_client.create_schema(auto_id=False,enable_dynamic_field=False)
    # 定义字段
    schema.add_field("id",          DataType.VARCHAR,is_primary = True,max_length = 128)
    schema.add_field("vector",      DataType.FLOAT_VECTOR,dim=1024)
    schema.add_field("text",        DataType.VARCHAR,max_length = 65535)
    schema.add_field("record_id",   DataType.VARCHAR,max_length = 64)
    schema.add_field("type",        DataType.VARCHAR,max_length = 32)
    schema.add_field("access_level",DataType.VARCHAR,max_length = 32)
    
    # 创建索引（给 type 和 access_level 建标量索引，让 filter 查询不走全表扫描）
    index_params = milvus_client.prepare_index_params()
    index_params.add_index("vector",        metric_type="IP",index_type = "IVF_FLAT", params={"nlist":128})
    index_params.add_index("record_id",     index_type = "INVERTED") # 删除时用
    index_params.add_index("type",          index_type = "BITMAP") # filter 过滤时用
    index_params.add_index("access_level",  index_type = "BITMAP") # 权限 filter 时用

    # 创建集合
    milvus_client.create_collection(
    	collection_name = collection_name,
    	schema = schema,
    	index_params = index_params
    )
    return True


def getAll():
    connections.connect(host="192.168.8.153",port="19530")
    collection = Collection("document_collection")
    iterator = collection.query_iterator(
        output_fields=["id", "record_id","type","access_level"]
    )

    results = []

    while True:
        result = iterator.next()
        if not result:
            iterator.close()
            break

        print(result,end="\n")
        results += result

def removeCollection(collection_name:str):
    milvus_client = get_milvus_client()
    milvus_client.drop_collection(
        collection_name=collection_name
    )

def removeAllData(collection_name:str)->bool:
    milvus_client = get_milvus_client()
    # id 字段为 VARCHAR，需用字符串表达式；id != "" 匹配所有非空 id 的记录
    result = milvus_client.delete(collection_name=collection_name, filter='id != ""')
    return result.get('delete_count', 0) >= 0 if isinstance(result, dict) else True


def removeData(collection_name:str,record_id:str)->bool:
    milvus_client = get_milvus_client()
    result = milvus_client.delete(collection_name=collection_name,filter=f"record_id == '{record_id}'")
    # 检查删除结果，返回布尔值
    return result.get('delete_count', 0) >= 0 if isinstance(result, dict) else True


if __name__ == "__main__":
    print(getAll())
