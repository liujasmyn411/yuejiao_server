"""
文件解析工具
支持 PDF / Excel 文件提取文本，用于客户画像研判
"""
import logging

logger = logging.getLogger("yuejiao.file_parser")


def parse_pdf(file_bytes: bytes) -> str:
    """解析PDF文件，返回纯文本内容"""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        texts = []
        for page in doc:
            texts.append(page.get_text())
        doc.close()
        return "\n".join(texts).strip()
    except ImportError:
        logger.warning("PyMuPDF(fitz)未安装，尝试pdfplumber")
        try:
            import pdfplumber
            import io
            text = ""
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text.strip()
        except ImportError:
            logger.error("PDF解析不可用：PyMuPDF和pdfplumber均未安装")
            return "[PDF解析错误：缺少依赖库(fitz或pdfplumber)]"
    except Exception as e:
        logger.error(f"PDF解析失败: {e}")
        return f"[PDF解析失败: {e}]"


def parse_excel(file_bytes: bytes) -> str:
    """解析Excel文件，返回格式化文本"""
    try:
        import openpyxl
        import io
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        parts = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            parts.append(f"--- 工作表: {sheet_name} ---")
            for row in ws.iter_rows(values_only=True):
                row_text = "\t".join(str(c) if c is not None else "" for c in row)
                if row_text.strip():
                    parts.append(row_text)
        wb.close()
        return "\n".join(parts).strip()
    except ImportError:
        logger.error("Excel解析不可用：openpyxl未安装")
        return "[Excel解析错误：缺少依赖库(openpyxl)]"
    except Exception as e:
        logger.error(f"Excel解析失败: {e}")
        return f"[Excel解析失败: {e}]"


def parse_file(file_bytes: bytes, filename: str) -> dict:
    """根据文件扩展名自动选择解析器，返回解析结果"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        text = parse_pdf(file_bytes)
        return {"filename": filename, "format": "pdf", "text": text, "text_length": len(text)}
    elif ext in ("xlsx", "xls"):
        text = parse_excel(file_bytes)
        return {"filename": filename, "format": "excel", "text": text, "text_length": len(text)}
    elif ext == "txt":
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("gbk", errors="replace")
        return {"filename": filename, "format": "txt", "text": text, "text_length": len(text)}
    else:
        return {"filename": filename, "format": ext, "text": "", "text_length": 0,
                "error": f"不支持的文件格式: .{ext}，支持 pdf/xlsx/xls/txt"}


def extract_profile_from_text(text: str) -> dict:
    """从文本中提取客户画像关键字段（用于PDF/Excel解析后的结构化）"""
    info = {}
    for keyword, fields in _PROFILE_PATTERNS:
        for field, pattern in fields:
            import re
            m = re.search(pattern, text)
            if m:
                info[field] = m.group(1)
                break
    return info


_PROFILE_PATTERNS = [
    ("姓名", [("name", r'姓\s*名[：:]\s*([一-鿿]{2,4})'),
              ("name", r'([一-鿿]{2,4})\s*[，,]\s*(?:男|女)')]),
    ("年龄", [("age", r'年\s*龄[：:]\s*(\d{1,2})'),
              ("age", r'(\d{1,2})\s*岁')]),
    ("学历", [("education", r'学\s*历[：:]\s*(\S+)')]),
    ("意向国家", [("intended_country", r'意向国家[：:]\s*(\S+)'),
                 ("intended_country", r'(新加坡|德国|英国|澳大利亚|美国|加拿大)')]),
    ("联系方式", [("contact", r'(?:电话|手机|联系方式)[：:]\s*(\d{7,15})'),
                 ("contact", r'(1[3-9]\d{9})')]),
]
