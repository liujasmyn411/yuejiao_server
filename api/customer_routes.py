"""
粤教服务 - 客服Agent API 路由
处理活动查询/报名 / 项目查询 / 客户画像研判等
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import EventRegisterRequest
from crud import EventCRUD, ProjectCRUD

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
def profile_match(age: int = 0, education: str = "", intended_country: str = "", db: Session = Depends(get_db)):
    """根据客户信息匹配推荐项目"""
    projects = ProjectCRUD.get_all(db)
    matched = []
    for p in projects:
        score = 0
        reasons = []
        # 简单的关键词匹配规则
        if intended_country and intended_country in (p.country or ""):
            score += 30
            reasons.append(f"匹配意向国家：{p.country}")
        if education:
            edu_lower = education.lower()
            audience_lower = (p.target_audience or "").lower()
            if "高中" in edu_lower and ("高中" in audience_lower or "本科" in audience_lower):
                score += 20
                reasons.append("学历匹配")
            elif "本科" in edu_lower and ("本科" in audience_lower or "硕士" in audience_lower):
                score += 20
                reasons.append("学历匹配")
            elif "大专" in edu_lower and "大专" in audience_lower:
                score += 20
                reasons.append("学历匹配")
        if age and p.target_audience:
            import re
            age_range = re.findall(r'(\d+)[-~](\d+)岁', p.target_audience)
            for lo, hi in age_range:
                if int(lo) <= age <= int(hi):
                    score += 25
                    reasons.append(f"年龄匹配：{lo}-{hi}岁")
                    break
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
