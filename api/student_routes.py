"""
粤教服务 - API路由层
处理HTTP请求和响应，调用DAO层完成业务逻辑
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from schemas import (
    EventRegisterRequest, LeadCreateRequest, LeadUpdateRequest,
    ReportCreateRequest, ScoreCreateRequest, LeaveCreateRequest,
    FeedbackCreateRequest, PsychAlertCreateRequest,
    UserCreateRequest, UserUpdateRequest
)
from dao import (
    UserDAO, EventDAO, ProjectDAO, CrmDAO, ReportDAO, ScoreDAO,
    StudentServiceDAO, FeedbackDAO, PsychAlertDAO, DashboardDAO
)


# ========== 路由定义 ==========

router = APIRouter()


# ---------- 根路径 ----------
@router.get("/")
def root():
    return {"msg": "粤教服务AI Agent API运行中", "status": "ok"}


# ---------- 健康检查 ----------
@router.get("/health")
def health_check():
    return {"status": "healthy", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# ==================== 学生助手接口 ====================
# ---- 根据id查询学生信息 ----


# ---- 请假: 提交 ----
@router.post("/api/student/leave")
def create_leave(req: LeaveCreateRequest, db: Session = Depends(get_db)):
    """学生提交请假申请"""
    StudentServiceDAO.create_leave(
        db, req.student_id, req.service_type,
        datetime.strptime(req.start_time, "%Y-%m-%d %H:%M"),
        datetime.strptime(req.end_time, "%Y-%m-%d %H:%M"),
        req.reason,
        leave_type=req.leave_type
    )
    db.commit()
    return {"success": True, "message": "请假申请已提交，等待审批"}


# ---- 请假: 查询 ----
@router.get("/api/student/leave")
def list_leaves(student_id: int = 0, db: Session = Depends(get_db)):
    """查询请假记录"""
    leaves = StudentServiceDAO.get_leaves(db, student_id)
    return {"leaves": [
        {"id": l.id, "student_id": l.student_id, "leave_type": l.leave_type,
         "start": str(l.start_time), "end": str(l.end_time), "reason": l.reason,
         "status": l.status, "reject_reason": l.reject_reason}
        for l in leaves
    ]}


# ---- 投诉反馈: 提交 ----
@router.post("/api/student/feedback")
def create_feedback(req: FeedbackCreateRequest, db: Session = Depends(get_db)):
    """学生提交投诉反馈"""
    ticket = FeedbackDAO.create(
        db, req.student_id, req.content, req.detail,
        feedback_type=req.feedback_type, urgency_level=req.urgency_level
    )
    db.commit()
    return {"success": True, "ticket_id": ticket.id, "message": "投诉已提交，我们会尽快处理"}


# ---- 投诉反馈: 查询 ----
@router.get("/api/student/feedback")
def list_feedback(student_id: int = 0, db: Session = Depends(get_db)):
    """查询投诉反馈列表"""
    tickets = FeedbackDAO.get_all(db, student_id)
    return {"tickets": [
        {"id": t.id, "student_id": t.student_id, "feedback_type": t.feedback_type,
         "content": t.content, "urgency_level": t.urgency_level,
         "status": t.status, "solution": t.solution}
        for t in tickets
    ]}


# ---- 心理预警: 提交 ----
@router.post("/api/student/psych-alert")
def create_psych_alert(req: PsychAlertCreateRequest, db: Session = Depends(get_db)):
    """提交心理预警"""
    alert = PsychAlertDAO.create(db, req.student_id, req.trigger_reason, req.risk_level, req.alert_source)
    PsychAlertDAO.update_profile(db, req.student_id, req.risk_level)
    db.commit()
    return {"success": True, "alert_id": alert.id,
            "message": f"已记录{req.risk_level}风险预警，老师会尽快跟进"}


# ---- 心理预警: 查询 ----
@router.get("/api/student/psych-alert")
def list_psych_alerts(risk_level: str = "", db: Session = Depends(get_db)):
    """查询心理预警列表"""
    alerts = PsychAlertDAO.get_all(db, risk_level)
    return {"alerts": [
        {"id": a.id, "student_id": a.student_id, "trigger_reason": a.trigger_reason,
         "risk_level": a.risk_level, "alert_source": a.alert_source, "status": a.status,
         "handle_content": a.handle_content}
        for a in alerts
    ]}


# ==================== 智能报告接口 ====================

@router.get("/api/reports/dashboard")
def dashboard(db: Session = Depends(get_db)):
    """管理仪表盘数据"""
    return DashboardDAO.get_stats(db)
