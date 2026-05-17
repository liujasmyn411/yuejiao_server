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


def parse_score_file(file_bytes: bytes, filename: str) -> list[dict]:
    """解析成绩批量上传文件（Excel/CSV），返回结构化成绩列表

    支持的列名（中文）：学生ID/学号、课程名称/科目、成绩/分数、总分、及格线、考试类型、考试时间、学期、教师ID
    支持的列名（英文）：student_id、course_name、score、total_score、pass_score、exam_type、exam_time、semester、teacher_id
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in ("xlsx", "xls"):
        text = parse_excel(file_bytes)
    elif ext == "csv":
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("gbk", errors="replace")
    else:
        raise ValueError(f"不支持的文件格式: .{ext}，支持 xlsx/xls/csv")

    if not text.strip():
        return []

    lines = text.strip().split("\n")
    if len(lines) < 2:
        return []

    # 列名映射（中文 → 英文字段名）
    col_map = {
        "学生id": "student_id", "学号": "student_id", "student_id": "student_id",
        "课程名称": "course_name", "科目": "course_name", "course_name": "course_name",
        "成绩": "score", "分数": "score", "score": "score",
        "总分": "total_score", "total_score": "total_score",
        "及格线": "pass_score", "pass_score": "pass_score",
        "考试类型": "exam_type", "exam_type": "exam_type",
        "考试时间": "exam_time", "exam_time": "exam_time",
        "学期": "semester", "semester": "semester",
        "教师id": "teacher_id", "teacher_id": "teacher_id",
    }

    header_line = lines[0]
    headers = [h.strip().lower() for h in header_line.split("\t") if h.strip()]
    if len(headers) <= 1:
        # 尝试逗号分隔（CSV）
        headers = [h.strip().lower() for h in header_line.split(",") if h.strip()]

    field_map = {}
    for i, h in enumerate(headers):
        if h in col_map:
            field_map[col_map[h]] = i

    if "student_id" not in field_map or "course_name" not in field_map or "score" not in field_map:
        raise ValueError("缺少必填列：学生ID/学号、课程名称/科目、成绩/分数")

    scores = []
    for line in lines[1:]:
        if not line.strip():
            continue
        cells = [c.strip() for c in line.split("\t")]
        if len(cells) <= 1:
            cells = [c.strip() for c in line.split(",")]

        row = {}
        for field, idx in field_map.items():
            if idx < len(cells):
                row[field] = cells[idx]

        if not row.get("student_id") or not row.get("course_name") or not row.get("score"):
            continue

        try:
            row["student_id"] = int(row["student_id"])
            row["score"] = float(row["score"])
            if row.get("total_score"):
                row["total_score"] = float(row["total_score"])
            if row.get("pass_score"):
                row["pass_score"] = float(row["pass_score"])
            if row.get("teacher_id"):
                row["teacher_id"] = int(row["teacher_id"])
        except (ValueError, TypeError):
            continue

        scores.append(row)

    return scores


def extract_profile_from_text(text: str) -> dict:
    """从文本中提取客户画像关键字段（用于PDF/Excel解析后的结构化）"""
    import re
    info = {}
    for keyword, fields in _PROFILE_PATTERNS:
        for field, pattern in fields:
            m = re.search(pattern, text)
            if m:
                info[field] = m.group(1).strip()
                break
    return info


def assess_lead_intention(profile: dict) -> dict:
    """根据用户研判规则评估是否为意向客户（需求4 & 需求7 共用）

    参考 knowledge_base/data/用户研判规则/用户画像研判规则.md

    Returns:
        {
            "is_intended": bool,
            "score": int,
            "matched_program": str,
            "reasons": [str, ...],
            "lead_data": {...}  # 可写入 crm_lead 的字段
        }
    """
    reasons = []
    sg_score = 0
    de_score = 0

    age = profile.get("age")
    if isinstance(age, str):
        try:
            age = int(age)
        except ValueError:
            age = None

    education = (profile.get("education") or "").strip()
    intended_country = (profile.get("intended_country") or "").strip()
    language_level = (profile.get("language_level") or "").strip()
    family_finance = (profile.get("family_finance") or "").strip()
    name = (profile.get("name") or "").strip()
    contact = (profile.get("contact") or profile.get("wechat") or "").strip()
    intended_major = (profile.get("intended_major") or "").strip()
    background = (profile.get("remark") or profile.get("background_info") or "").strip()

    # ===== 新加坡项目评估 =====
    sg_reasons = []
    sg_age_match = False
    if age and age > 0:
        if 14 <= age <= 16:
            sg_score += 30
            sg_reasons.append(f"年龄匹配新加坡项目：{age}岁（初中毕业生范围14-16岁）")
            sg_age_match = True
        elif 16 <= age <= 19:
            sg_score += 30
            sg_reasons.append(f"年龄匹配新加坡项目：{age}岁（高中/中职毕业生范围16-19岁）")
            sg_age_match = True
        elif age >= 17 and ("职高" in education or "中专" in education or "中职" in education or "中技" in education):
            sg_score += 25
            sg_reasons.append(f"年龄匹配新加坡就业班：{age}岁（满17岁可报大专就业班）")
            sg_age_match = True
        elif 14 <= age <= 19:
            sg_score += 15
            sg_reasons.append(f"年龄基本匹配新加坡项目：{age}岁")
            sg_age_match = True

    if education:
        if any(kw in education for kw in ["初中"]):
            sg_score += 25
            sg_reasons.append(f"学历匹配：{education}（初中毕业可报2+2/2+2+1项目）")
        elif any(kw in education for kw in ["高中", "职高", "中专", "中职", "中技"]):
            sg_score += 25
            sg_reasons.append(f"学历匹配：{education}（可报0.5/1+2或就业班项目）")
            # 高中学历可推断年龄 16-19，缺年龄时给予部分年龄分
            if not age or age <= 0:
                sg_score += 15
                sg_reasons.append("学历推断年龄范围匹配新加坡项目（高中/中职通常16-19岁）")
                sg_age_match = True
        elif any(kw in education for kw in ["大专", "专科"]):
            sg_score += 20
            sg_reasons.append(f"学历匹配：{education}（可报一年制专升本）")
        elif any(kw in education for kw in ["本科"]):
            sg_score += 20
            sg_reasons.append(f"学历匹配：{education}（可报一年制本升硕）")

    if intended_country and "新加坡" in intended_country:
        sg_score += 15
        sg_reasons.append("意向国家明确为新加坡")

    if family_finance:
        if any(kw in family_finance for kw in ["富裕", "良好", "中等"]):
            sg_score += 10
            sg_reasons.append(f"家庭经济状况良好：{family_finance}")

    if language_level:
        sg_score += 5
        sg_reasons.append(f"有语言水平记录：{language_level}")

    if sg_age_match and education:
        sg_score += 15
        sg_reasons.append("留学意愿评估：基本条件满足新加坡项目")

    # ===== 德国项目评估 =====
    de_reasons = []
    de_age_match = False
    if age and age > 0:
        if 18 <= age <= 35:
            de_score += 25
            de_reasons.append(f"年龄匹配德国项目：{age}岁（范围18-35岁）")
            de_age_match = True
        elif age < 18:
            de_reasons.append(f"年龄不足德国项目要求（需满18岁，当前{age}岁）")
        elif age > 35:
            de_reasons.append(f"年龄超出德国项目要求（上限35岁，当前{age}岁）")

    if education:
        high_edu = any(kw in education for kw in ["大专", "专科", "本科", "硕士", "博士"])
        mid_edu = any(kw in education for kw in ["高中", "职高", "中专", "中职", "中技"])
        if high_edu or mid_edu:
            de_score += 20
            de_reasons.append(f"学历匹配德国项目：{education}（需高中及以上）")
            # 大专/本科及以上可推断年龄 18+，缺年龄时给予部分年龄分
            if high_edu and (not age or age <= 0):
                de_score += 15
                de_reasons.append("学历推断年龄范围匹配德国项目（大专/本科通常18岁以上）")
                de_age_match = True
            elif mid_edu and (not age or age <= 0):
                de_score += 10
                de_reasons.append("学历推断可能匹配德国项目（高中/中职需确认年龄≥18）")
        elif "初中" in education:
            de_reasons.append("学历不满足德国项目要求（需高中及以上）")

    if intended_country and "德国" in intended_country:
        de_score += 15
        de_reasons.append("意向国家明确为德国")

    if language_level:
        if any(kw in language_level.lower() for kw in ["德语", "b1", "b2", "a1", "a2"]):
            de_score += 15
            de_reasons.append(f"德语水平记录：{language_level}")
        else:
            de_score += 5
            de_reasons.append(f"语言水平记录：{language_level}")

    if family_finance:
        if any(kw in family_finance for kw in ["富裕", "良好", "中等"]):
            de_score += 10
            de_reasons.append(f"家庭经济支持：{family_finance}")

    if de_age_match and education:
        de_score += 15
        de_reasons.append("留学意愿评估：基本条件满足德国项目")

    # 如果意向国家明确，优先匹配对应项目
    if "新加坡" in intended_country:
        de_score = 0
    elif "德国" in intended_country:
        sg_score = 0

    # 判定结果
    threshold = 50
    if sg_score >= threshold and sg_score >= de_score:
        reasons = sg_reasons
        lead_data = _build_lead_data(profile, "新加坡国际本硕升学计划", sg_score, name, contact, intended_major, background, education, age, intended_country, language_level, family_finance)
        return {
            "is_intended": True,
            "score": sg_score,
            "matched_program": "新加坡国际本硕升学计划",
            "reasons": reasons,
            "lead_data": lead_data,
        }
    elif de_score >= threshold:
        reasons = de_reasons
        lead_data = _build_lead_data(profile, "中德精英人才共建计划", de_score, name, contact, intended_major, background, education, age, intended_country, language_level, family_finance)
        return {
            "is_intended": True,
            "score": de_score,
            "matched_program": "中德精英人才共建计划",
            "reasons": reasons,
            "lead_data": lead_data,
        }
    else:
        all_reasons = sg_reasons + de_reasons
        if not all_reasons:
            all_reasons = ["缺少足够的客户画像信息（年龄、学历、意向国家等），无法进行有效研判"]
        best_score = max(sg_score, de_score)
        return {
            "is_intended": False,
            "score": best_score,
            "matched_program": "",
            "reasons": all_reasons,
            "lead_data": None,
        }


def _build_lead_data(profile, program, score, name, contact, intended_major, background, education, age, intended_country, language_level, family_finance):
    """构建 CRM lead 数据"""
    return {
        "customer_name": name or "未知",
        "contact_info": contact or "",
        "age": age,
        "education": education or "",
        "intended_country": intended_country or "",
        "intended_major": intended_major or "",
        "family_finance": family_finance or "",
        "language_level": language_level or "",
        "background_info": background or f"通过文件解析自动研判 - 匹配{program}",
        "status": "新增意向",
        "source_channel": "文件解析",
        "score": score,
    }


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
