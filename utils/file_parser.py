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
    # 姓名：标签格式、表头格式、"姓名，性别"组合
    ("姓名", [("name", r'姓\s*名[：:\s=]\s*([^\n\r]{2,20})'),
              ("name", r'[Nn]ame[：:\s=]\s*([^\n\r]{2,20})'),
              ("name", r'([一-鿿]{2,4})\s*[，,]\s*(?:男|女)'),
              ("name", r'客户[：:\s=]\s*([^\n\r]{2,10})')]),
    # 性别
    ("性别", [("gender", r'性\s*别[：:\s=]\s*(男|女)'),
              ("gender", r'[一-鿿]{2,4}\s*[，,]\s*(男|女)')]),
    # 年龄：标签格式、"XX岁"格式
    ("年龄", [("age", r'年\s*龄[：:\s=]\s*(\d{1,3})'),
              ("age", r'[Aa]ge[：:\s=]\s*(\d{1,3})'),
              ("age", r'(\d{1,3})\s*岁')]),
    # 学历
    ("学历", [("education", r'学\s*历[：:\s=]\s*([^\n\r]{2,20})'),
              ("education", r'[Ee]ducation[：:\s=]\s*([^\n\r]{2,20})'),
              ("education", r'(初中|高中|职高|中专|大专|本科|硕士|博士|研究生)')]),
    # 意向国家
    ("意向国家", [("intended_country", r'意向[国]?[家]?[：:\s=]\s*([^\n\r]{2,20})'),
                  ("intended_country", r'目标国家[：:\s=]\s*([^\n\r]{2,20})'),
                  ("intended_country", r'(新加坡|德国|英国|澳大利亚|美国|加拿大|日本|韩国|法国|新西兰|马来西亚)')]),
    # 意向专业
    ("意向专业", [("intended_major", r'意向专业[：:\s=]\s*([^\n\r]{2,30})'),
                  ("intended_major", r'目标专业[：:\s=]\s*([^\n\r]{2,30})'),
                  ("intended_major", r'[Mm]ajor[：:\s=]\s*([^\n\r]{2,30})')]),
    # 电话/手机
    ("联系方式", [("contact", r'(?:电话|手机|联系方式|联系电话|手机号)[：:\s=]\s*([\d\-+()（）\s]{7,20})'),
                  ("contact", r'[Pp]hone[：:\s=]\s*([\d\-+()（）\s]{7,20})'),
                  ("contact", r'(1[3-9]\d{9})')]),
    # 邮箱
    ("邮箱", [("email", r'邮\s*箱[：:\s=]\s*([^\n\r\s]{5,40})'),
              ("email", r'[Ee][-]?[Mm]ail[：:\s=]\s*([^\n\r\s]{5,40})'),
              ("email", r'([\w.\-]+@[\w\-]+\.[\w.]+)')]),
    # 微信
    ("微信", [("wechat", r'微\s*信[：:\s=]\s*([^\n\r]{3,30})'),
              ("wechat", r'[Ww]e[Cc]hat[：:\s=]\s*([^\n\r]{3,30})')]),
    # 语言水平
    ("语言水平", [("language_level", r'(?:语言水平|语言成绩|外语水平)[：:\s=]\s*([^\n\r]{2,20})'),
                  ("language_level", r'(?:雅思|托福|JLPT|TOPIK)[：:\s=]*\s*([\d.]+)'),
                  ("language_level", r'(雅思\s*[\d.]+|托福\s*\d+|CET[- ]?\d)')]),
    # 家庭经济状况
    ("家庭经济", [("family_finance", r'(?:家庭经济|经济状况|家庭收入)[：:\s=]\s*([^\n\r]{2,20})'),
                  ("family_finance", r'(富裕|中等|一般|良好)')]),
    # 毕业/当前学校
    ("学校", [("school", r'(?:学校|毕业院校|在读院校|院校)[：:\s=]\s*([^\n\r]{3,30})'),
              ("school", r'[Ss]chool[：:\s=]\s*([^\n\r]{3,30})')]),
    # 地址
    ("地址", [("address", r'(?:地址|住址|所在地)[：:\s=]\s*([^\n\r]{5,60})'),
              ("address", r'[Aa]ddress[：:\s=]\s*([^\n\r]{5,60})')]),
    # 备注/背景
    ("备注", [("remark", r'(?:备注|背景信息|补充说明|其他)[：:\s=]\s*([^\n\r]{3,100})')]),
]
