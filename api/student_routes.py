"""
粤教服务 - API路由层
处理HTTP请求和响应，调用CRUD层完成业务逻辑
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    LeaveCreateRequest, FeedbackCreateRequest, FeedbackResolveRequest,
    PsychAlertCreateRequest, RiskLevelEnum
)
from crud import (
    UserCRUD, StudentServiceCRUD, FeedbackCRUD, PsychAlertCRUD,
    AcademicCRUD, StudyAbroadCRUD, NotificationCRUD,
)
from utils.auth import get_current_user, require_student
from model import SysUser


# ========== 路由定义 ==========

router = APIRouter(tags=["学生智能助手"])

# ==================== 学生助手接口 ====================

def _validate_student(student_id: int, db: Session):
    """验证学生身份：必须是STUDENT类型且未被软删除"""
    student = UserCRUD.get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"学生不存在或已删除(student_id={student_id})")
    return student


# ---- 根据id查询学生信息 ----
@router.get("/api/student/info")
def get_student_info(student_id: int, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    """根据ID查询学生基本信息"""
    student = _validate_student(student_id, db)
    return {
        "id": student.id,
        "real_name": student.real_name,
        "username": student.username,
        "department": student.department,
        "contact_info": student.contact_info,
        "email": student.email,
        "country_region": student.country_region,
        "status": student.status,
    }


# ---- 请假: 提交 ----
@router.post("/api/student/leave")
def create_leave(req: LeaveCreateRequest, db: Session = Depends(get_db), current_user: SysUser = Depends(require_student)):
    """学生提交请假申请"""
    student = _validate_student(req.student_id, db)
    try:
        leave = StudentServiceCRUD.create_leave(db, req)
        # 预填审批人为班主任
        if student.head_teacher_id:
            leave.approver_id = student.head_teacher_id
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 查班主任联系信息（供邮件通知用）
    teacher_info = {}
    if student.head_teacher_id:
        teacher = db.query(SysUser).filter(
            SysUser.id == student.head_teacher_id,
            SysUser.delete_flag == 0,
        ).first()
        if teacher:
            teacher_info = {
                "teacher_name": teacher.real_name,
                "teacher_email": teacher.email,
                "teacher_contact": teacher.contact_info,
            }

    return {
        "success": True,
        "message": "请假申请已提交，等待班主任审批",
        "leave_id": leave.id,
        "student_name": student.real_name,
        "student_email": student.email,
        "leave_type": req.leave_type,
        "start_time": str(req.start_time) if req.start_time else None,
        "end_time": str(req.end_time) if req.end_time else None,
        "reason": req.reason,
        "teacher": teacher_info,
    }


# ---- 请假: 查询 ----
@router.get("/api/student/leave")
def list_leaves(student_id: int = 0, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    """查询请假记录"""
    if student_id:
        _validate_student(student_id, db)
    leaves = StudentServiceCRUD.get_leaves(db, student_id)
    return {"leaves": [
        {"id": l.id, "student_id": l.student_id, "leave_type": l.leave_type,
         "start": str(l.start_time), "end": str(l.end_time), "reason": l.reason,
         "status": l.status, "reject_reason": l.reject_reason}
        for l in leaves
    ]}


# ---- 投诉反馈: 提交 ----
@router.post("/api/student/feedback")
def create_feedback(req: FeedbackCreateRequest, db: Session = Depends(get_db), current_user: SysUser = Depends(require_student)):
    """学生提交投诉反馈"""
    _validate_student(req.student_id, db)
    ticket = FeedbackCRUD.create(db, req)
    db.commit()
    return {"success": True, "ticket_id": ticket.id, "message": "投诉已提交，我们会尽快处理"}


# ---- 投诉反馈: 查询 ----
@router.get("/api/student/feedback")
def list_feedback(student_id: int = 0, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    """查询投诉反馈列表"""
    if student_id:
        _validate_student(student_id, db)
    tickets = FeedbackCRUD.get_all(db, student_id)
    return {"tickets": [
        {"id": t.id, "student_id": t.student_id, "feedback_type": t.feedback_type,
         "content": t.content, "urgency_level": t.urgency_level,
         "status": t.status, "solution": t.solution}
        for t in tickets
    ]}


# ---- 投诉反馈: 处理 ----
@router.put("/api/student/feedback/{ticket_id}/resolve")
def resolve_feedback(ticket_id: int, req: FeedbackResolveRequest, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    """处理投诉反馈工单（老师/管理员标记已解决）"""
    ticket = FeedbackCRUD.resolve(db, ticket_id, req.solution, req.handle_user_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    NotificationCRUD.create(
        db,
        recipient_id=ticket.student_id,
        title="投诉反馈已处理",
        content=f"您的{ticket.feedback_type}({ticket.content})已处理：{req.solution}",
        notification_type="feedback_resolved",
        related_id=ticket.id,
    )
    db.commit()
    return {"success": True, "ticket_id": ticket.id, "message": "工单已处理"}


# ---- 心理预警: 提交 ----
@router.post("/api/student/psych-alert")
def create_psych_alert(req: PsychAlertCreateRequest, db: Session = Depends(get_db), current_user: SysUser = Depends(require_student)):
    """提交心理预警"""
    _validate_student(req.student_id, db)
    alert = PsychAlertCRUD.create(db, req)
    PsychAlertCRUD.update_profile(db, req.student_id, req.risk_level)
    db.commit()
    return {"success": True, "alert_id": alert.id,
            "message": f"已记录{req.risk_level}风险预警，老师会尽快跟进"}


# ---- 心理预警: 查询 ----
@router.get("/api/student/psych-alert")
def list_psych_alerts(risk_level: RiskLevelEnum = None, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    """查询心理预警列表"""
    alerts = PsychAlertCRUD.get_all(db, risk_level.value if risk_level else "")
    return {"alerts": [
        {"id": a.id, "student_id": a.student_id, "trigger_reason": a.trigger_reason,
         "risk_level": a.risk_level, "alert_source": a.alert_source, "status": a.status,
         "handle_content": a.handle_content}
        for a in alerts
    ]}


# ==================== 学业考务接口 ====================

@router.get("/api/student/academic")
def list_academic(student_id: int, academic_type: str = "", db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    """查询学生教务信息（考试/论文DDL/作业）"""
    _validate_student(student_id, db)
    items = AcademicCRUD.get_by_student(db, student_id, academic_type)
    return {"academics": [
        {
            "id": a.id, "course_name": a.course_name,
            "academic_type": a.academic_type, "title": a.title,
            "description": a.description, "exam_location": a.exam_location,
            "deadline": str(a.deadline), "duration_minutes": a.duration_minutes,
            "semester": a.semester, "ddl_status": a.ddl_status,
            "remind_enabled": a.remind_enabled,
            "remind_days_before": a.remind_days_before,
        }
        for a in items
    ]}


@router.get("/api/student/academic/upcoming")
def list_upcoming_academic(student_id: int, days: int = 14, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    """查询即将到来的DDL（未来N天内的考试/论文/作业）"""
    _validate_student(student_id, db)
    items = AcademicCRUD.get_upcoming(db, student_id, days)
    return {"upcoming": [
        {
            "id": a.id, "course_name": a.course_name,
            "academic_type": a.academic_type, "title": a.title,
            "deadline": str(a.deadline), "ddl_status": a.ddl_status,
            "days_left": (a.deadline - __import__("datetime").datetime.now()).days,
        }
        for a in items
    ]}


# ==================== 留学进度追踪接口 ====================

@router.get("/api/student/study-abroad")
def list_study_abroad_progress(student_id: int, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    """查询学生留学业务全流程进度"""
    _validate_student(student_id, db)
    items = StudyAbroadCRUD.get_by_student(db, student_id)
    if not items:
        return {"progress": [], "message": "暂无留学进度数据"}
    return {"progress": [
        {
            "id": i.id, "target_country": i.target_country,
            "target_school": i.target_school, "target_major": i.target_major,
            "degree_level": i.degree_level,
            "stage": i.stage, "stage_order": i.stage_order,
            "stage_status": i.stage_status, "stage_detail": i.stage_detail,
            "handler_name": i.handler_name, "handler_contact": i.handler_contact,
            "estimated_complete_date": str(i.estimated_complete_date) if i.estimated_complete_date else None,
            "actual_complete_date": str(i.actual_complete_date) if i.actual_complete_date else None,
            "is_current": i.is_current,
        }
        for i in items
    ]}


@router.get("/api/student/study-abroad/current")
def get_current_stage(student_id: int, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    """查询学生当前所处的留学进度阶段"""
    _validate_student(student_id, db)
    stage = StudyAbroadCRUD.get_current_stage(db, student_id)
    if not stage:
        return {"current_stage": None, "message": "暂无进行中的留学进度"}
    return {
        "target_country": stage.target_country,
        "target_school": stage.target_school,
        "target_major": stage.target_major,
        "stage": stage.stage,
        "stage_status": stage.stage_status,
        "stage_detail": stage.stage_detail,
        "handler_name": stage.handler_name,
        "handler_contact": stage.handler_contact,
        "estimated_complete_date": str(stage.estimated_complete_date) if stage.estimated_complete_date else None,
    }


# ==================== 站内通知接口 ====================

@router.get("/api/student/notification")
def list_notifications(recipient_id: int, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    """查询用户通知列表"""
    notifs = NotificationCRUD.get_by_recipient(db, recipient_id)
    return {"notifications": [
        {"id": n.id, "title": n.title, "content": n.content,
         "notification_type": n.notification_type, "related_id": n.related_id,
         "is_read": n.is_read, "create_time": str(n.create_time)}
        for n in notifs
    ]}


@router.get("/api/student/notification/unread-count")
def unread_count(recipient_id: int, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    """查询未读通知数"""
    count = NotificationCRUD.get_unread_count(db, recipient_id)
    return {"recipient_id": recipient_id, "unread_count": count}


@router.put("/api/student/notification/{notif_id}/read")
def mark_notification_read(notif_id: int, recipient_id: int, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    """标记单条通知为已读"""
    notif = NotificationCRUD.mark_read(db, notif_id, recipient_id)
    if not notif:
        raise HTTPException(status_code=404, detail="通知不存在")
    db.commit()
    return {"success": True, "message": "已标记为已读"}


@router.put("/api/student/notification/read-all")
def mark_all_read(recipient_id: int, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    """标记所有通知为已读"""
    NotificationCRUD.mark_all_read(db, recipient_id)
    db.commit()
    return {"success": True, "message": "全部已读"}


# ==================== 学生助手对话接口 ====================

@router.post("/api/student/chat")
def student_chat(message: dict, db: Session = Depends(get_db), current_user: SysUser = Depends(require_student)):
    """学生助手对话接口（支持7种意图）"""
    from agents.student.agent import StudentAgent
    agent = StudentAgent()
    text = message.get("message", "")
    student_id = message.get("student_id")
    result = agent.route_intent(text, student_id=student_id, db=db)
    return result


