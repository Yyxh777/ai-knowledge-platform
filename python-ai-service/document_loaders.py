# document_loaders.py
from langchain_community.document_loaders import (
    UnstructuredMarkdownLoader,
    UnstructuredHTMLLoader,
    Docx2txtLoader,
)
from langchain_unstructured import UnstructuredLoader
from langchain_core.documents import Document
from typing import List
import os


class DocumentLoaderFactory:
    """文档加载器工厂：根据文件扩展名选择合适的 Loader"""

    # 不同的 Unstructured 处理策略
    # hi_res: 高精度 OCR + 布局检测，适合复杂文档（表格、图片）
    # auto: 自动选择策略，通用场景
    # fast: 快速处理，适合纯文本文档
    STRATEGY_MAP = {
        "technical_manual": "hi_res",   # 技术手册：表格、代码多
        "policy": "hi_res",             # 公司制度：格式复杂
        "faq": "auto",                  # FAQ：简单文本
        "project_doc": "auto",          # 项目文档：格式中等
    }

    # 根据文件类型获取处理器
    @staticmethod
    def get_loader(file_path: str, doc_category: str = "auto") -> object:
        ext = os.path.splitext(file_path)[1].lower() # 获取文件后缀名
        strategy = DocumentLoaderFactory.STRATEGY_MAP.get(doc_category, "auto") # 获取处理策略

        if ext == ".md":
            return UnstructuredMarkdownLoader(
                file_path,
                mode="elements",  # 按语义元素拆分，保留标题/段落/代码块标记
            )
        elif ext == ".pdf":
            return UnstructuredLoader(
                file_path,
                strategy=strategy,
                include_page_breaks=True,  # 保留分页信息
            )
        elif ext == ".docx":
            return Docx2txtLoader(file_path)
        elif ext == ".html":
            return UnstructuredHTMLLoader(file_path)
        else:
            raise ValueError(f"Unsupported format: {ext}")

    # ocr识别返回文档内容
    @staticmethod
    def load_with_ocr(file_path: str) -> List[Document]:
        """
        扫描件 PDF 的 OCR 处理方案。
        优先推荐 MinerU API（云端），备选 PaddleOCR（本地方案）。

        为什么优先 MinerU？
        - MinerU 基于 1.2B VLM，在 OmniDocBench 基准上超越 72B 通用大模型[reference:3]
        - 支持 109 种语言 OCR，自动纠正旋转版面[reference:4]
        - 输出保留完整标题层级和表格结构

        本地备选 PaddleOCR 的优点：
        - 无需 API 调用，数据不出企业内网
        - 中文 OCR 准确率高
        """
        # 方案 A: MinerU API（推荐）
        try:
            from langchain_mineru import MinerULoader
            loader = MinerULoader(source=file_path, mode="precision")
            return loader.load()
        except ImportError:
            pass

        # 方案 B: PaddleOCR（本地备选）
        from paddleocr import PaddleOCR
        import fitz  # PyMuPDF

        ocr = PaddleOCR(use_angle_cls=True, lang="ch")
        documents = []
        pdf_doc = fitz.open(file_path)

        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            # 将 PDF 页面渲染为图片
            pix = page.get_pixmap(dpi=300)
            img_path = f"/tmp/page_{page_num}.png"
            pix.save(img_path)

            # OCR 识别
            result = ocr.ocr(img_path, cls=True)
            text = "\n".join([
                line[1][0] for line in result[0]
            ]) if result[0] else ""

            documents.append(Document(
                page_content=text,
                metadata={
                    "source": file_path,
                    "page": page_num + 1,
                    "total_pages": len(pdf_doc),
                    "ocr_engine": "PaddleOCR",
                }
            ))

        return documents