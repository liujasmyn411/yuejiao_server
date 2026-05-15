"""
粤教服务 - 企业智能助手 API 路由
处理 CRM 客户管理 / 日报 / 员工查询等
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    LeadCreateRequest, LeadUpdateRequest,
    ReportCreateRequest, ScoreCreateRequest,
)
from crud import (
    UserCRUD, CrmCRUD, ReportCRUD, ScoreCRUD, EmployeeCRUD, DashboardCRUD
)

router = APIRouter(prefix="/api/enterprise", tags=["企业智能助手"])


# ==================== 意向客户管理 ====================

@router.post("/lead")
def create_lead(req: LeadCreateRequest, db: Session = Depends(get_db)):
    """录入新意向客户"""
    lead = CrmCRUD.create(db, **req.model_dump(exclude_none=True))
    db.commit()
    return {"success": True, "lead_id": lead.id, "message": "客户录入成功"}


@router.get("/lead")
def list_leads(status: str = "", db: Session = Depends(get_db)):
    """查询意向客户列表"""
    leads = CrmCRUD.get_all(db, status)
    return {"leads": [
        {
            "id": l.id, "customer_name": l.customer_name,
            "contact_info": l.contact_info, "age": l.age,
            "education": l.education, "intended_country": l.intended_country,
            "intended_major": l.intended_major, "status": l.status,
            "score": l.score, "owner_employee_id": l.owner_employee_id,
            "next_follow_time": str(l.next_follow_time) if l.next_follow_time else None,
            "create_time": str(l.create_time),
        }
        for l in leads
    ]}


@router.put("/lead/{lead_id}")
def update_lead(lead_id: int, req: LeadUpdateRequest, db: Session = Depends(get_db)):
    """更新意向客户信息"""
    lead = CrmCRUD.update(db, lead_id, **req.model_dump(exclude_none=True))
    if not lead:
        raise HTTPException(status_code=404, detail="客户不存在")
    db.commit()
    return {"success": True, "message": "客户信息更新成功"}


# ==================== 员工日报 ====================

@router.post("/report")
def submit_report(req: ReportCreateRequest, db: Session = Depends(get_db)):
    """提交员工日报"""
    data = req.model_dump(exclude_none=True)
    if not data.get("report_date"):
        from datetime import date
        data["report_date"] = date.today().strftime("%Y-%m-%d")
    report = ReportCRUD.create(db, **data)
    db.commit()
    return {"success": True, "report_id": report.id, "message": "日报提交成功"}


@router.get("/report")
def list_reports(employee_id: int = 0, db: Session = Depends(get_db)):
    """查询员工日报列表"""
    reports = ReportCRUD.get_all(db, employee_id)
    return {"reports": [
        {
            "id": r.id, "employee_id": r.employee_id,
            "report_date": str(r.report_date), "work_type": r.work_type,
            "content": r.content, "summary": r.summary,
            "report_status": r.report_status,
        }
        for r in reports
    ]}


# ==================== 学生成绩管理 ====================

@router.post("/score")
def add_score(req: ScoreCreateRequest, db: Session = Depends(get_db)):
    """录入学生成绩"""
    score = ScoreCRUD.create(db, **req.model_dump(exclude_none=True))
    db.commit()
    return {"success": True, "score_id": score.id, "message": "成绩录入成功"}


@router.get("/score")
def list_scores(student_id: int, db: Session = Depends(get_db)):
    """查询学生成绩"""
    scores = ScoreCRUD.get_by_student(db, student_id)
    return {"scores": [
        {
            "id": s.id, "course_name": s.course_name, "score": float(s.score),
            "total_score": float(s.total_score) if s.total_score else None,
            "exam_type": s.exam_type, "semester": s.semester,
            "exam_time": str(s.exam_time) if s.exam_time else None,
        }
        for s in scores
    ]}


# ==================== 员工查询 ====================

@router.get("/employee")
def list_employees(db: Session = Depends(get_db)):
    """查询员工列表"""
    employees = EmployeeCRUD.get_all(db)
    return {"employees": [
        {
            "id": e.id, "real_name": e.real_name,
            "employee_role": e.employee_role, "department": e.department,
            "contact_info": e.contact_info, "email": e.email,
        }
        for e in employees
    ]}


# ==================== 仪表盘 ====================

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    """企业助手仪表盘"""
    return DashboardCRUD.get_stats(db)


# ==================== 企业助手对话接口 ====================

@router.post("/chat")
def enterprise_chat(message: dict, db: Session = Depends(get_db)):
    """企业助手对话接口（支持NL2SQL/日报/CRM等）"""
    from agents.enterprise.agent import EnterpriseAgent
    agent = EnterpriseAgent()
    text = message.get("message", "")
    result = agent.route_intent(text, db=db)
    return result


@router.post("/nl2sql")
def nl2sql_query(message: dict, db: Session = Depends(get_db)):
    """自然语言转SQL查询"""
    from agents.enterprise.agent import EnterpriseAgent
    agent = EnterpriseAgent()
    text = message.get("message", "")
    result = agent.query_database(text, db)
    return result


@router.post("/voice-report")
def voice_to_report(message: dict):
    """口述文本 → 结构化日报"""
    from agents.enterprise.agent import EnterpriseAgent
    agent = EnterpriseAgent()
    text = message.get("message", "")
    report = agent.voice_to_report(text)
    return {"success": True, "report": report}
