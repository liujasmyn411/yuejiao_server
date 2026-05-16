"""
粤教服务 - 客服Agent API 路由
处理活动查询/报名 / 项目查询 / 客户画像研判等
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from database import get_db
from schemas import EventRegisterRequest
from crud import EventCRUD, ProjectCRUD
from utils.file_parser import parse_file, extract_profile_from_text

router = APIRouter(prefix="/api/customer", tags=["客服Agent"])


# ==================== 活动讲座 ====================

@router.get("/events")
def list_events(db: Session = Depends(get_db)):
    """查询所有活动讲座"""
    events = EventCRUD.get_all(db)
    return {"events": [
        {
            "id": e.id, "event_name": e.event_name,
            "event_type": e.event_type, "speaker": e.speaker,
            "start_time": str(e.start_time), "location": e.location,
            "max_participants": e.max_participants,
            "current_participants": e.current_participants,
            "event_status": e.event_status,
        }
        for e in events
    ]}


@router.post("/events/register")
def register_event(req: EventRegisterRequest, db: Session = Depends(get_db)):
    """活动报名"""
    event = EventCRUD.get_by_id(db, req.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")
    if event.max_participants and event.current_participants >= event.max_participants:
        raise HTTPException(status_code=400, detail="报名已满")
    reg = EventCRUD.register(
        db, req.event_id,
        customer_id=req.customer_id,
        customer_name=req.customer_name,
        contact=req.contact or ""
    )
    db.commit()
    return {"success": True, "registration_id": reg.id, "message": f"已成功报名「{event.event_name}」"}


@router.get("/events/{event_id}/registrations")
def list_event_registrations(event_id: int, db: Session = Depends(get_db)):
    """查询活动报名列表"""
    regs = EventCRUD.get_registrations(db, event_id)
    return {"registrations": [
        {
            "id": r.id, "customer_name": r.customer_name,
            "contact": r.contact, "status": r.status,
            "check_in_status": r.check_in_status,
            "create_time": str(r.create_time),
        }
        for r in regs
    ]}


# ==================== 课程项目 ====================

@router.get("/projects")
def list_projects(category: str = "", db: Session = Depends(get_db)):
    """查询课程/留学项目列表"""
    projects = ProjectCRUD.get_all(db, category)
    return {"projects": [
        {
            "id": p.id, "project_name": p.project_name,
            "category": p.category, "country": p.country,
            "tuition_fee": p.tuition_fee, "duration": p.duration,
            "description": p.description, "target_audience": p.target_audience,
            "application_require": p.application_require,
            "is_recommended": p.is_recommended,
        }
        for p in projects
    ]}


# ==================== 客户画像研判 ====================

@router.post("/profile-match")
def profile_match(
    age: int = 0,
    education: str = "",
    intended_country: str = "",
    db: Session = Depends(get_db)
):
    """根据客户画像匹配推荐项目

    **参数说明**（均为 query 参数，可选填）:
    - **age**: 客户年龄，例如 20
    - **education**: 学历，可选值 — 初中 / 高中 / 职高 / 中专 / 大专 / 本科 / 硕士 / 博士
    - **intended_country**: 意向国家，可选值 — 新加坡 / 德国 / 英国 / 澳大利亚 / 美国 / 加拿大

    **计分规则**: 国家匹配 +30 / 学历匹配 +20 / 年龄匹配 +25
    """
    projects = ProjectCRUD.get_all(db)
    if not projects:
        return {"matches": [], "message": "暂无项目数据"}

    # 如果指定了意向国家，先滤掉不匹配的项目，避免推荐无关国家
    if intended_country:
        projects = [
            p for p in projects
            if intended_country in ((p.country or "") + (p.category or ""))
        ]
        if not projects:
            return {"matches": [], "message": f"暂无「{intended_country}」相关项目"}

    matched = []
    for p in projects:
        score = 0
        reasons = []

        # 拼接所有可搜索文本（category + name + audience + description）
        search_text = ((p.category or "") + " " + (p.project_name or "") + " " +
                       (p.target_audience or "") + " " + (p.description or "")).lower()

        # 国家匹配加分
        if intended_country:
            country_text = (p.country or "") + (p.category or "")
            if intended_country in country_text:
                score += 30
                reasons.append(f"匹配意向国家：{intended_country}")

        # 学历匹配：搜索 category / project_name / target_audience
        if education:
            edu_lower = education.lower()
            # 学历 → 可能出现在数据中的关键词
            edu_keywords = {
                "初中": ["初中"],
                "高中": ["高中"],
                "职高": ["职高", "中职", "中专", "中技"],
                "中专": ["中专", "中职", "中技"],
                "大专": ["大专", "专科", "专升本", "专升硕"],
                "本科": ["本科"],
                "硕士": ["硕士"],
                "博士": ["博士"],
            }
            keywords = edu_keywords.get(edu_lower, [education])
            if any(kw in search_text for kw in keywords):
                score += 20
                reasons.append(f"学历匹配：{education}")
            # 反向兼容：用户填的学历在项目文本中直接出现
            elif edu_lower in search_text:
                score += 20
                reasons.append(f"学历匹配：{education}")

        # 年龄匹配：优先使用结构化字段 age_min/age_max，其次用正则从文本提取
        if age:
            import re
            matched_age = False

            # 方式1：结构化字段 age_min / age_max
            if p.age_min is not None or p.age_max is not None:
                lo = p.age_min or 0
                hi = p.age_max or 999
                if lo <= age <= hi:
                    score += 25
                    reasons.append(f"年龄匹配：{lo}-{hi}岁")
                    matched_age = True

            # 方式2：正则从 target_audience / description 文本中提取
            if not matched_age:
                search_for_age = (p.target_audience or "") + " " + (p.description or "")
                age_range = re.findall(r'(\d+)[-~](\d+)岁', search_for_age)
                for lo, hi in age_range:
                    if int(lo) <= age <= int(hi):
                        score += 25
                        reasons.append(f"年龄匹配：{lo}-{hi}岁")
                        matched_age = True
                        break
            if not matched_age:
                min_age = re.findall(r'年满(\d+)岁', search_for_age)
                for ma in min_age:
                    if age >= int(ma):
                        score += 25
                        reasons.append(f"年龄匹配：年满{ma}岁")
                        matched_age = True
                        break

        # 只要有任一项匹配就返回
        if score > 0:
            matched.append({
                "project_name": p.project_name,
                "category": p.category,
                "country": p.country,
                "description": p.description,
                "match_score": min(score, 100),
                "match_reasons": reasons,
            })

    matched.sort(key=lambda x: x["match_score"], reverse=True)
    return {"matches": matched[:5]}


# ==================== 文件解析（客户画像研判） ====================

@router.post("/parse-file")
async def parse_customer_file(file: UploadFile = File(...)):
    """上传客户简历/信息文件（PDF/Excel/TXT），解析为文本用于画像研判

    支持格式：pdf / xlsx / xls / txt
    会从文本中自动提取姓名、年龄、学历、意向国家、联系方式等关键字段
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    result = parse_file(content, file.filename)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])

    # 从解析文本中提取画像关键字段
    profile = extract_profile_from_text(result["text"]) if result["text"] else {}

    return {
        "success": True,
        "filename": result["filename"],
        "format": result["format"],
        "text": result["text"],
        "text_length": result["text_length"],
        "extracted_profile": profile,
    }


# ==================== 客服对话接口 ====================

@router.post("/chat")
def customer_chat(message: dict):
    """客服Agent对话接口（支持8种意图）"""
    from agents.customer_service.agent import CustomerServiceAgent
    agent = CustomerServiceAgent()
    text = message.get("message", "")
    result = agent.route_intent(text)
    return result
