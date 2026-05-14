def format_response(data: dict) -> dict:
    return {"status": "ok", "data": data}




"""
粤教服务 AI Agent — 公共工具函数库 (utils.py)

供 T1-T6 直接调用，包含：
  1. profile_matcher     画像研判引擎
  2. nl2sql              自然语言转SQL（安全模板版）
  3. voice_to_text       语音转文字（Whisper API）
  4. summarize_daily_report  日报摘要提炼
  5. emotion_analyzer    情绪分析与风险分级
  6. psych_report_generator  心理健康周报生成
  7. customer_insight_report  客户经营分析报告

使用方式:
    from utils import profile_matcher, nl2sql, voice_to_text, ...
"""

import re
import json
import requests
from datetime import datetime, timedelta
from typing import Optional
from database import SessionLocal, CrmLead, StudentPsychProfile, StudentPsychAlert, \
    StudentFeedbackTicket, EmployeeDailyReport, EventLecture, EventRegistration, \
    StudentAdminService, StudentScore, SysUser

# ========== 配置区（实际使用替换为真实Key）==========

LLM_API_KEY = "your-deepseek-api-key-here"
LLM_API_URL = "https://api.deepseek.com/chat/completions"
LLM_MODEL = "deepseek-chat"

WHISPER_API_KEY = "your-whisper-api-key-here"
WHISPER_API_URL = "https://api.openai.com/v1/audio/transcriptions"


# ========== 1. 画像研判引擎 ==========

def profile_matcher(text: str) -> dict:
    """
    客户画像研判引擎
    输入: "姓名张三 男 19岁 家里很有钱 电话1348907728"
    输出: {"customer_name", "matched_product", "recommended_project", "score", "reason", "suggestion"}
    """
    name = _extract_name(text)
    age = _extract_age(text)
    education = _extract_education(text)
    income_level = _extract_income(text)
    intent_germany = _has_germany_intent(text)
    intent_singapore = _has_singapore_intent(text)

    sg_score, sg_project, sg_reason = _match_singapore(age, education, income_level, text)
    de_score, de_project, de_reason = _match_germany(age, education, text, intent_germany)

    if sg_score > de_score and sg_score >= 40:
        return {
            "customer_name": name,
            "matched_product": "新加坡国际本硕升学计划",
            "recommended_project": sg_project,
            "score": min(sg_score, 100),
            "reason": sg_reason,
            "suggestion": _sg_suggestion(sg_project, age, education)
        }
    elif de_score >= 40:
        return {
            "customer_name": name,
            "matched_product": "中德精英人才共建计划",
            "recommended_project": de_project,
            "score": min(de_score, 100),
            "reason": de_reason,
            "suggestion": _de_suggestion(de_project, age, education)
        }
    else:
        return {
            "customer_name": name,
            "matched_product": "暂不匹配",
            "recommended_project": "暂无推荐",
            "score": max(sg_score, de_score),
            "reason": _nomatch_reason(age, education, text),
            "suggestion": "建议深入了解客户真实需求，可推荐咨询人工顾问（电话020-37628058）"
        }


def _extract_name(text: str) -> str:
    patterns = [
        r'姓名[是\s]*([\u4e00-\u9fff]{2,4})',
        r'我叫([\u4e00-\u9fff]{2,4})',
        r'([\u4e00-\u9fff]{2,4})[，,]\s*(?:男|女|\d)',
        r'^([\u4e00-\u9fff]{2,4})\s+'
    ]
    for p in patterns:
        m = re.search(p, text)
        if m: return m.group(1)
    return "未知"


def _extract_age(text: str) -> Optional[int]:
    for p in [r'(\d{1,2})\s*[岁歲]', r'年龄[是\s]*(\d{1,2})']:
        m = re.search(p, text)
        if m: return int(m.group(1))
    return None


def _extract_gender(text: str) -> str:
    if '男' in text: return "男"
    if '女' in text: return "女"
    return "未知"


def _extract_education(text: str) -> str:
    edu_keywords = {
        "初中": ["初中", "初三", "初二", "初一"],
        "高中": ["高中", "高三", "高二", "高一", "普通高中"],
        "中职": ["中职", "中专", "中技", "中专职高", "职高"],
        "大专": ["大专", "专科", "高职", "职业技术学院"],
        "本科": ["本科", "大学本科", "一本", "二本", "三本"],
        "硕士": ["硕士", "研究生", "读研"],
    }
    for edu, keywords in edu_keywords.items():
        for kw in keywords:
            if kw in text: return edu
    return "未知"


def _extract_income(text: str) -> str:
    if any(w in text for w in ["很有钱", "富裕", "中产", "高收入", "条件好", "条件优渥", "优渥", "不差钱"]): return "高"
    if any(w in text for w in ["中等", "工薪", "普通家庭", "一般"]): return "中"
    if any(w in text for w in ["农村", "困难", "拮据", "低"]): return "低"
    return "未知"


def _extract_phone(text: str) -> str:
    m = re.search(r'1[3-9]\d{9}', text)
    return m.group(0) if m else ""


def _has_germany_intent(text: str) -> bool:
    return any(kw in text for kw in ["德国", "德國", "德语", "德文", "双元制", "移民德国", "去德国"])


def _has_singapore_intent(text: str) -> bool:
    return any(kw in text for kw in ["新加坡", "新加玻", "新国", "去新加坡"])


def _match_singapore(age, education, income, text):
    score = 0; project = ""; reasons = []
    if age is not None:
        if 14 <= age <= 16:
            score += 30; project = "2+2新加坡定向培养本科班 / 2+2+1本硕连读"
            reasons.append(f"年龄{age}岁，符合初中毕业生14-16岁画像")
        elif 16 < age <= 19:
            score += 35; project = "0.5/1+2新加坡定向培养本科班 / 0.5/1+2+1本硕连读"
            reasons.append(f"年龄{age}岁，符合高中生16-19岁画像")
        elif 17 <= age <= 20 and education in ["中职", "职高"]:
            score += 25; project = "6+6酒店运营大专就业班 / 9+6航空运营大专就业班"
            reasons.append(f"年龄{age}岁，职高/中专背景，适合大专就业班")
        elif 19 < age <= 25:
            if education == "大专":
                score += 30; project = "一年制专升本"
                reasons.append(f"年龄{age}岁，专科学历，适合一年制专升本")
            elif education == "本科":
                score += 30; project = "一年制本升硕"
                reasons.append(f"年龄{age}岁，本科学历，适合一年制本升硕")
            else:
                score += 15; reasons.append(f"年龄{age}岁，超出主力招生范围，但可考虑升学路径")
        else:
            reasons.append(f"年龄{age}岁，不在新加坡项目主力招生年龄段")
    if education in ["高中", "中职", "大专", "本科"]:
        score += 20; reasons.append(f"{education}学历符合要求")
    elif education == "初中":
        score += 15; reasons.append("初中学历，可报2+2本科班")
    if income == "高":
        score += 15; reasons.append("家庭经济条件好，可承担学费")
    elif income == "中":
        score += 10; reasons.append("家庭经济中等")
    if _has_singapore_intent(text):
        score += 10; reasons.append("明确表达了新加坡留学意向")
    return score, project, "；".join(reasons) if reasons else "暂不符合新加坡项目画像"


def _match_germany(age, education, text, has_intent):
    score = 0; reasons = []
    if age is not None:
        if 18 <= age <= 35:
            score += 30; reasons.append(f"年龄{age}岁，符合18-35岁要求")
        else:
            reasons.append(f"年龄{age}岁，不在18-35岁范围内")
    if education in ["高中", "大专", "本科", "硕士"]:
        score += 25; reasons.append(f"{education}学历达标（高中及以上）")
    elif education in ["中职", "职高"]:
        score += 20; reasons.append("中职/职高学历，可考虑部分专业")
    if any(kw in text for kw in ["动手", "机械", "技术", "工程师", "逻辑", "理科"]):
        score += 15; reasons.append("具备动手/技术能力倾向")
    if has_intent:
        score += 15; reasons.append("明确表达德国/双元制意向")
    if any(kw in text for kw in ["移民", "永居", "留在德国", "定居"]):
        score += 10; reasons.append("有移民倾向，德国项目可升学+可移民")
    project = "中德精英人才共建计划（六大专业：医疗健康/机械制造/商贸会计/电子电器/汽车服务/酒店管理）"
    return score, project, "；".join(reasons) if reasons else "暂不符合德国项目画像"


def _sg_suggestion(project, age, education):
    if "2+2" in project: return "重点推荐2+2本科班，强调国内2年+新加坡2年，总学费30-31万，学历含金量高"
    elif "0.5/1+2" in project: return "重点推荐0.5/1+2本科班，强调学制短（最快3年本科毕业），总学费25-26万"
    elif "大专" in project: return "推荐大专就业班，强调一年获大专文凭+100%推荐就业+月薪15000+"
    elif "专升本" in project: return "推荐一年制专升本，强调弯道超车、学制短、回国认证"
    elif "本升硕" in project: return "推荐一年制本升硕，强调新加坡硕士学历含金量高"
    return "建议安排专业顾问一对一沟通"


def _de_suggestion(project, age, education):
    return "重点介绍双元制免学费+享补贴（880-1030欧/月）+保就业+工作两年可移民的优势，安排德语水平评估"


def _nomatch_reason(age, education, text):
    reasons = []
    if age is not None and (age < 14 or age > 35): reasons.append(f"年龄{age}岁不在两个项目的招生范围内")
    if education == "未知": reasons.append("未明确学历信息")
    if not reasons: reasons.append("综合条件暂不匹配现有项目")
    return "；".join(reasons)


# ========== 2. 自然语言转SQL（安全模板版） ==========

def nl2sql(natural_lang: str, table_schema: str = "") -> dict:
    """
    自然语言转SQL —— 只支持预定义查询模板
    输入: "查一下跟进中的客户"
    输出: {"sql": "...", "type": "SELECT", "params": [], "safe": true}
    """
    text = natural_lang.strip().lower()

    # CRM查询
    if any(kw in text for kw in ["客户", "leads", "意向"]):
        if any(kw in text for kw in ["新增", "新"]):
            return {"sql": "SELECT * FROM crm_lead WHERE status='新增意向' ORDER BY create_time DESC LIMIT 50", "type": "SELECT", "params": [], "safe": True}
        if any(kw in text for kw in ["跟进", "跟进中"]):
            return {"sql": "SELECT * FROM crm_lead WHERE status='跟进中' ORDER BY update_time DESC LIMIT 50", "type": "SELECT", "params": [], "safe": True}
        if any(kw in text for kw in ["已签约", "签约"]):
            return {"sql": "SELECT * FROM crm_lead WHERE status='已签约' ORDER BY create_time DESC LIMIT 50", "type": "SELECT", "params": [], "safe": True}
        if any(kw in text for kw in ["流失", "丢"]):
            return {"sql": "SELECT * FROM crm_lead WHERE status='已流失' ORDER BY create_time DESC LIMIT 50", "type": "SELECT", "params": [], "safe": True}
        name = _extract_name_from_query(text)
        if name:
            return {"sql": f"SELECT * FROM crm_lead WHERE customer_name LIKE '%{name}%' ORDER BY create_time DESC", "type": "SELECT", "params": [], "safe": True}
        return {"sql": "SELECT * FROM crm_lead ORDER BY create_time DESC LIMIT 50", "type": "SELECT", "params": [], "safe": True}

    # 更新客户状态
    if any(kw in text for kw in ["改成", "改为", "更新", "修改状态"]):
        name = _extract_name_from_query(text)
        new_status = _extract_status(text)
        if name and new_status:
            return {"sql": "UPDATE crm_lead SET status=?, update_time=CURRENT_TIMESTAMP WHERE customer_name LIKE ?", "type": "UPDATE", "params": [new_status, f"%{name}%"], "safe": True}
        return {"sql": "", "type": "ERROR", "params": [], "safe": False, "error": "请提供客户姓名和新状态"}

    # 活动查询
    if any(kw in text for kw in ["活动", "讲座", "event", "分享会", "说明会"]):
        return {"sql": "SELECT * FROM event_lecture WHERE start_time > CURRENT_TIMESTAMP ORDER BY start_time LIMIT 10", "type": "SELECT", "params": [], "safe": True}

    # 日报查询
    if any(kw in text for kw in ["日报", "report", "汇报"]):
        if any(kw in text for kw in ["今天", "今日"]):
            today = datetime.now().strftime("%Y-%m-%d")
            return {"sql": f"SELECT * FROM employee_daily_report WHERE report_date='{today}' ORDER BY create_time DESC", "type": "SELECT", "params": [], "safe": True}
        return {"sql": "SELECT * FROM employee_daily_report ORDER BY create_time DESC LIMIT 30", "type": "SELECT", "params": [], "safe": True}

    # 成绩查询
    if any(kw in text for kw in ["成绩", "分数", "score", "考试"]):
        return {"sql": "SELECT * FROM student_score ORDER BY create_time DESC LIMIT 50", "type": "SELECT", "params": [], "safe": True}

    # 请假查询
    if any(kw in text for kw in ["请假", "leave"]):
        return {"sql": "SELECT * FROM student_admin_service WHERE service_type='请假' ORDER BY create_time DESC LIMIT 30", "type": "SELECT", "params": [], "safe": True}

    # 投诉查询
    if any(kw in text for kw in ["投诉", "反馈", "ticket", "工单"]):
        return {"sql": "SELECT * FROM student_feedback_ticket ORDER BY create_time DESC LIMIT 30", "type": "SELECT", "params": [], "safe": True}

    # 心理预警查询
    if any(kw in text for kw in ["预警", "心理", "风险", "alert"]):
        if any(kw in text for kw in ["高危", "高风险", "高"]):
            return {"sql": "SELECT * FROM student_psych_alert WHERE risk_level='高' ORDER BY create_time DESC", "type": "SELECT", "params": [], "safe": True}
        return {"sql": "SELECT * FROM student_psych_alert ORDER BY create_time DESC LIMIT 30", "type": "SELECT", "params": [], "safe": True}

    return {"sql": "", "type": "CLARIFY", "params": [], "safe": True, "error": "未能理解查询意图，请尝试：查客户、查活动、查日报、查成绩、查请假、查投诉、查预警"}


def _extract_name_from_query(text: str) -> str:
    patterns = [
        r'([\u4e00-\u9fff]{2,4})的?(?:客户|跟进|记录|状态|日报|成绩)',
        r'把([\u4e00-\u9fff]{2,4})',
        r'查[一-十]?下?([\u4e00-\u9fff]{2,4})',
        r'([\u4e00-\u9fff]{2,4})[的，]'
    ]
    for p in patterns:
        m = re.search(p, text)
        if m: return m.group(1)
    return ""


def _extract_status(text: str) -> str:
    status_map = {
        "新增意向": ["新增", "新意向"],
        "跟进中": ["跟进", "跟进中"],
        "已签约": ["签约", "已签约", "成交"],
        "已流失": ["流失", "已流失", "丢"]
    }
    for status, keywords in status_map.items():
        for kw in keywords:
            if kw in text: return status
    return ""


# ========== 3. 语音转文字 ==========

def voice_to_text(audio_path: str) -> str:
    """语音转文字 —— 封装 Whisper API"""
    try:
        with open(audio_path, "rb") as audio_file:
            headers = {"Authorization": f"Bearer {WHISPER_API_KEY}"}
            files = {"file": audio_file, "model": (None, "whisper-1")}
            resp = requests.post(WHISPER_API_URL, headers=headers, files=files, timeout=30)
            resp.raise_for_status()
            return resp.json().get("text", "")
    except Exception as e:
        return f"[语音转写失败: {str(e)}]"


# ========== 4. 日报摘要提炼 ==========

def summarize_daily_report(raw_text: str) -> dict:
    """将口语化的工作描述提炼为结构化日报"""
    if LLM_API_KEY and LLM_API_KEY != "your-deepseek-api-key-here":
        try:
            return _summarize_with_llm(raw_text)
        except:
            pass
    return _summarize_with_rules(raw_text)


def _summarize_with_llm(raw_text: str) -> dict:
    prompt = f"""请将以下员工口述的工作描述提炼为结构化日报。
口述内容：{raw_text}
请提取核心进展、关键产出、待办事项。输出JSON格式：
{{"core_progress": ["..."], "key_output": "...", "todo": ["..."]}}"""

    headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": LLM_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3, "max_tokens": 1000}
    resp = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match: return json.loads(json_match.group(0))
    raise ValueError("LLM返回格式不正确")


def _summarize_with_rules(raw_text: str) -> dict:
    progress = []; todos = []
    sentences = re.split(r'[；;。！!]', raw_text)
    for s in sentences:
        s = s.strip()
        if not s: continue
        if any(kw in s for kw in ["客户", "跟进", "沟通", "联系", "回访"]): progress.append(s)
        if any(kw in s for kw in ["明天", "下周", "需要", "计划", "安排"]): todos.append(s.replace("明天", "").replace("下周", "").strip())
    if not progress: progress = [raw_text[:100]]
    return {"core_progress": progress, "key_output": f"完成{len(progress)}项工作进展", "todo": todos if todos else ["继续跟进客户"]}


# ========== 5. 情绪分析与风险分级 ==========

def emotion_analyzer(dialogue_history: str) -> dict:
    """分析学生对话情绪，识别心理风险"""
    text = dialogue_history.lower()

    HIGH_RISK_KEYWORDS = [
        "不想活了", "活着没意思", "想死", "自杀", "自残", "活不下去",
        "没有意义", "绝望", "崩溃", "撑不住了", "结束生命"
    ]
    MEDIUM_RISK_KEYWORDS = [
        "压力很大", "焦虑", "失眠", "睡不着", "害怕", "担心", "紧张",
        "孤独", "没人理解", "好累", "疲惫", "烦躁", "想哭", "郁闷",
        "迷茫", "无助", "想回家", "想爸妈"
    ]
    LOW_POSITIVE = ["还好", "不错", "开心", "高兴", "谢谢", "好的", "嗯嗯"]

    high_triggers = [kw for kw in HIGH_RISK_KEYWORDS if kw in text]
    medium_triggers = [kw for kw in MEDIUM_RISK_KEYWORDS if kw in text]

    if high_triggers:
        score = 10 + max(0, 20 - len(high_triggers) * 5); level = "高"
    elif medium_triggers:
        score = 30 + max(0, 40 - len(medium_triggers) * 5); level = "中" if len(medium_triggers) >= 3 else "低"
    elif any(kw in text for kw in LOW_POSITIVE):
        score = 70 + min(30, len([k for k in LOW_POSITIVE if k in text]) * 10); level = "无"
    else:
        score = 50; level = "低"

    score = max(0, min(100, score))
    if score < 30: tag = "严重焦虑/抑郁"
    elif score < 50: tag = "焦虑"
    elif score < 70: tag = "低落"
    elif score < 85: tag = "平稳"
    else: tag = "积极"

    if level == "高": suggestion = "⚠️ 高危预警：建议老师5分钟内联系学生，必要时启动紧急干预"
    elif level == "中": suggestion = "⚡ 中危关注：建议老师1小时内与学生沟通，了解具体情况"
    elif level == "低": suggestion = "💛 低危观察：建议近期多关注该学生情绪变化"
    else: suggestion = "✅ 情绪状态良好，继续保持关怀"

    return {
        "emotion_tag": tag, "emotion_score": score, "risk_level": level,
        "trigger_words": "、".join(high_triggers + medium_triggers[:3]), "suggestion": suggestion
    }


# ========== 6. 心理健康周报生成 ==========

def psych_report_generator(week_start: str = "", db_session=None) -> dict:
    """生成学生心理健康周报"""
    if not db_session: db_session = SessionLocal()
    if not week_start:
        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    week_end = (datetime.strptime(week_start, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")

    alerts = db_session.query(StudentPsychAlert).filter(
        StudentPsychAlert.create_time >= week_start,
        StudentPsychAlert.create_time <= week_end + " 23:59:59"
    ).all()

    risk_summary = {"高": 0, "中": 0, "低": 0, "无": 0}
    high_risk_list = []
    for alert in alerts:
        risk_summary[alert.risk_level] = risk_summary.get(alert.risk_level, 0) + 1
        if alert.risk_level == "高":
            student = db_session.query(SysUser).filter(SysUser.id == alert.student_id).first()
            high_risk_list.append({"student_id": alert.student_id, "name": student.real_name if student else "未知",
                                   "reason": alert.trigger_reason[:50] + "..." if len(alert.trigger_reason) > 50 else alert.trigger_reason})

    profiles = db_session.query(StudentPsychProfile).all()
    emotion_trend = [p.emotion_score or 50 for p in profiles]

    recommendations = []
    if risk_summary["高"] > 0: recommendations.append(f"本周有{risk_summary['高']}个高危预警，建议立即安排老师一对一跟进")
    if risk_summary["中"] > 0: recommendations.append(f"有{risk_summary['中']}个中危案例，建议在本周内完成沟通")
    avg_score = sum(emotion_trend) / len(emotion_trend) if emotion_trend else 50
    if avg_score < 50: recommendations.append(f"本周平均情绪分{avg_score:.0f}，整体偏低，建议组织集体活动缓解压力")

    return {
        "week": f"{week_start} ~ {week_end}", "total_students": len(profiles),
        "emotion_trend": emotion_trend, "risk_summary": risk_summary,
        "high_risk_list": high_risk_list,
        "recommendations": recommendations if recommendations else ["本周心理状态整体平稳，继续保持关注"]
    }


# ========== 7. 客户经营分析报告 ==========

def customer_insight_report(db_session=None) -> dict:
    """生成全域客户经营分析报告"""
    if not db_session: db_session = SessionLocal()
    leads = db_session.query(CrmLead).all()
    total = len(leads)

    by_status = {"新增意向": 0, "跟进中": 0, "已签约": 0, "已流失": 0}
    for lead in leads: by_status[lead.status] = by_status.get(lead.status, 0) + 1

    conversion_rate = f"{by_status.get('已签约', 0) / total * 100:.1f}%" if total > 0 else "0%"
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    recent_leads = [l for l in leads if l.create_time and l.create_time.strftime("%Y-%m-%d") >= week_ago]

    recommendations = []
    if by_status.get("跟进中", 0) > 3: recommendations.append(f"有{by_status['跟进中']}个客户在跟进中，建议集中资源促进转化")
    if by_status.get("已流失", 0) > 0: recommendations.append(f"有{by_status['已流失']}个流失客户，可尝试回访挽回")
    if by_status.get("新增意向", 0) == 0: recommendations.append("本周无新增意向，建议加强市场推广")

    return {
        "total_customers": total, "by_status": by_status,
        "conversion_rate": conversion_rate,
        "recent_trend": f"本周新增{len(recent_leads)}个意向客户，{by_status.get('已签约', 0)}个签约",
        "recommendations": recommendations if recommendations else ["客户经营状态良好，继续保持跟进节奏"]
    }


if __name__ == "__main__":
    # 快速测试
    print("画像研判:", profile_matcher("张三 19岁 高中 家里有钱"))
    print("NL2SQL:", nl2sql("查跟进中的客户")["type"])
    print("情绪分析:", emotion_analyzer("不想活了")["risk_level"])
