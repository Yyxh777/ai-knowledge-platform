from fastapi import APIRouter, Depends
from models.document import UploadDocumentRequest
from service.document_service import upload_document_data, remove_document_data
from middleware.auth_deps import get_current_user
from typing import Dict

router = APIRouter()

# 上传文档数据
@router.post("/uploadDocument", response_model=bool)
def upload_document(req: UploadDocumentRequest):
    """上传文档到向量数据库（需要登录）"""
    # 记录操作日志：知道是谁在上传
    # print(f"用户 {user['account']}({user['user_id']}) 上传文档: {req.id}")
    
    result = upload_document_data(req.id, req.file_url, req.doc_type, req.access_level)
    return result

# 删除文档数据
@router.delete("/removeDocument", response_model=bool)
def remove_document(id: str, user: Dict = Depends(get_current_user)):
    """删除文档（需要登录）"""
    # 记录操作日志：知道是谁在删除
    print(f"用户 {user['account']}({user['user_id']}) 删除文档: {id}")
    
    result = remove_document_data(id)
    return result
