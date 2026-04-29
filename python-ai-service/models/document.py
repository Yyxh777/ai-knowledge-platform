from pydantic import BaseModel


class UploadDocumentRequest(BaseModel):
    id: str            # 文档记录 ID（对应 Java 服务的主键）
    file_url: str      # 文档下载地址
    doc_type: str      # 文档类型: policy（制度类）| tech（技术文档）
    access_level: str  # 权限等级: public | internal | hr_only | project
