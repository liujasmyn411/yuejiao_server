"""
粤教服务 - 学生智能助手 CRUD 数据访问层
封装用户管理、请假、投诉反馈、心理预警、教务信息、留学进度的数据库操作
"""

from sqlalchemy.orm import Session
from datetime import datetime

from model import (
    SysUser, StudentAdminService, StudentPsychProfile, StudentPsychAlert,
    StudentFeedbackTicket, StudentAcademic, StudentStudyAbroadProgress,
    Notification,
)
from schemas import (
    LeaveCreateRequest, FeedbackCreateRequest, PsychAlertCreateRequest
)


class UserCRUD:
    """用户数据访问对象"""

    @staticmethod
    def create(db: Session, **kwargs):
        """创建用户"""
        user = SysUser(**kwargs)
        db.add(user)
        return user

    @staticmethod
    def get_by_id(db: Session, user_id: int):
        """根据ID查询用户（未删除）"""
        return db.query(SysUser).filter(
            SysUser.id == user_id,
            SysUser.delete_flag == 0
        ).first()

    @staticmethod
    def get_by_username(db: Session, username: str):
        """根据用户名查询用户（未删除）"""
        return db.query(SysUser).filter(
            SysUser.username == username,
            SysUser.delete_flag == 0
        ).first()

    @staticmethod
    def get_student_by_id(db: Session, student_id: int):
        """根据ID查询学生（user_type=STUDENT 且未删除）"""
        return db.query(SysUser).filter(
            SysUser.id == student_id,
            SysUser.user_type == "STUDENT",
            SysUser.delete_flag == 0
        ).first()

    @staticmethod
    def validate_head_teacher(db: Session, head_teacher_id: int):
        """校验班主任ID：必须存在、未删除、user_type=EMPLOYEE、employee_role='班主任'"""
        if head_teacher_id is None:
            raise ValueError("班主任ID为必填")
        teacher = db.query(SysUser).filter(
            SysUser.id == head_teacher_id,
            SysUser.delete_flag == 0,
            SysUser.user_type == "EMPLOYEE",
            SysUser.employee_role == "班主任"
        ).first()
        if not teacher:
            raise ValueError(f"班主任不存在或无权限(id={head_teacher_id})，须为EMPLOYEE且employee_role='班主任'")
        return teacher

    @staticmethod
    def update(db: Session, user_id: int, **kwargs):
        """更新用户信息（仅更新非None字段）"""
        user = UserCRUD.get_by_id(db, user_id)
        if user:
            for key, value in kwargs.items():
                if value is not None:
                    setattr(user, key, value)
        return user

    @staticmethod
    def delete(db: Session, user_id: int):
        """软删除用户（设置delete_flag=1）"""
        user = UserCRUD.get_by_id(db, user_id)
        if user:
            user.delete_flag = 1
        return user


class StudentServiceCRUD:
    """学生行政服务数据访问对象"""

    @staticmethod
    def create_leave(db: Session, req: LeaveCreateRequest):
        """提交请假申请（含防重复提交检测）"""
        existing = db.query(StudentAdminService).filter(
            StudentAdminService.student_id == req.student_id,
            StudentAdminService.service_type == "请假",
            StudentAdminService.leave_type == req.leave_type,
            StudentAdminService.start_time == req.start_time,
            StudentAdminService.end_time == req.end_time,
            StudentAdminService.reason == req.reason,
            StudentAdminService.delete_flag == 0
        ).first()
        if existing:
            raise ValueError("请勿重复提交")

        data = req.model_dump(exclude_none=True)
        data["status"] = "待审批"
        leave = StudentAdminService(**data)
        db.add(leave)
        return leave

    @staticmethod
    def get_leaves(db: Session, student_id: int = 0):
        """查询请假记录（支持按学生筛选，按创建时间倒序）"""
        query = db.query(StudentAdminService).filter(
            StudentAdminService.service_type == "请假",
            StudentAdminService.delete_flag == 0
        )
        if student_id:
            query = query.filter(StudentAdminService.student_id == student_id)
        return query.order_by(StudentAdminService.create_time.desc()).all()


class FeedbackCRUD:
    """投诉反馈数据访问对象"""

    @staticmethod
    def create(db: Session, req: FeedbackCreateRequest):
        """提交投诉反馈（默认状态：待处理）"""
        data = req.model_dump(exclude_none=True)
        data["status"] = "待处理"
        ticket = StudentFeedbackTicket(**data)
        db.add(ticket)
        return ticket

    @staticmethod
    def get_all(db: Session, student_id: int = 0):
        """查询投诉反馈列表（支持按学生筛选，按创建时间倒序）"""
        query = db.query(StudentFeedbackTicket).filter(
            StudentFeedbackTicket.delete_flag == 0
        )
        if student_id:
            query = query.filter(StudentFeedbackTicket.student_id == student_id)
        return query.order_by(StudentFeedbackTicket.create_time.desc()).all()

    @staticmethod
    def resolve(db: Session, ticket_id: int, solution: str, handle_user_id: int):
        """处理投诉反馈工单"""
        ticket = db.query(StudentFeedbackTicket).filter(
            StudentFeedbackTicket.id == ticket_id,
            StudentFeedbackTicket.delete_flag == 0,
        ).first()
        if not ticket:
            return None
        ticket.status = "已处理"
        ticket.solution = solution
        ticket.handle_user_id = handle_user_id
        ticket.handle_time = datetime.now()
        ticket.is_notified = 1
        return ticket


class PsychAlertCRUD:
    """心理预警数据访问对象"""

    @staticmethod
    def create(db: Session, req: PsychAlertCreateRequest):
        """提交心理预警（默认状态：未处理）"""
        data = req.model_dump(exclude_none=True)
        data["status"] = "未处理"
        alert = StudentPsychAlert(**data)
        db.add(alert)
        return alert

    @staticmethod
    def get_all(db: Session, risk_level: str = ""):
        """查询心理预警列表（支持按风险等级筛选，按创建时间倒序）"""
        query = db.query(StudentPsychAlert).filter(
            StudentPsychAlert.delete_flag == 0
        )
        if risk_level:
            query = query.filter(StudentPsychAlert.risk_level == risk_level)
        return query.order_by(StudentPsychAlert.create_time.desc()).all()

    @staticmethod
    def update_profile(db: Session, student_id: int, risk_level: str):
        """更新学生心理画像（存在则更新，不存在则创建）"""
        profile = db.query(StudentPsychProfile).filter(
            StudentPsychProfile.student_id == student_id,
            StudentPsychProfile.delete_flag == 0
        ).first()

        if profile:
            profile.latest_emotion_tag = risk_level
            profile.risk_level = risk_level if risk_level in ("high", "medium", "low", "none") else "low"
            profile.emotion_score = 20 if risk_level == "high" else (40 if risk_level == "medium" else 60)
            profile.total_risk_count = (profile.total_risk_count or 0) + 1
            profile.teacher_follow_up_status = "未跟进"
            profile.last_interaction_time = datetime.now()
        else:
            new_profile = StudentPsychProfile(
                student_id=student_id,
                latest_emotion_tag=risk_level,
                risk_level=risk_level if risk_level in ("high", "medium", "low", "none") else "low",
                emotion_score=20 if risk_level == "high" else 40,
                total_risk_count=1,
                teacher_follow_up_status="未跟进",
                last_interaction_time=datetime.now()
            )
            db.add(new_profile)


class AcademicCRUD:
    """学生教务信息数据访问对象"""

    @staticmethod
    def get_by_student(db: Session, student_id: int, academic_type: str = ""):
        """查询学生教务信息（支持按类型筛选，按截止时间升序）"""
        query = db.query(StudentAcademic).filter(
            StudentAcademic.student_id == student_id,
            StudentAcademic.delete_flag == 0
        )
        if academic_type:
            query = query.filter(StudentAcademic.academic_type == academic_type)
        return query.order_by(StudentAcademic.deadline.asc()).all()

    @staticmethod
    def get_upcoming(db: Session, student_id: int, days: int = 14):
        """查询未来N天内未完成的DDL（按截止时间升序）"""
        from datetime import timedelta
        now = datetime.now()
        cutoff = now + timedelta(days=days)
        return db.query(StudentAcademic).filter(
            StudentAcademic.student_id == student_id,
            StudentAcademic.deadline >= now,
            StudentAcademic.deadline <= cutoff,
            StudentAcademic.ddl_status == "未完成",
            StudentAcademic.delete_flag == 0
        ).order_by(StudentAcademic.deadline.asc()).all()


class StudyAbroadCRUD:
    """留学业务进度数据访问对象"""

    @staticmethod
    def get_by_student(db: Session, student_id: int):
        """查询学生留学全流程进度（按阶段序号排列）"""
        return db.query(StudentStudyAbroadProgress).filter(
            StudentStudyAbroadProgress.student_id == student_id,
            StudentStudyAbroadProgress.delete_flag == 0
        ).order_by(StudentStudyAbroadProgress.stage_order.asc()).all()

    @staticmethod
    def get_current_stage(db: Session, student_id: int):
        """查询学生当前所处阶段"""
        return db.query(StudentStudyAbroadProgress).filter(
            StudentStudyAbroadProgress.student_id == student_id,
            StudentStudyAbroadProgress.is_current == 1,
            StudentStudyAbroadProgress.delete_flag == 0
        ).first()


class NotificationCRUD:
    """站内通知数据访问对象"""

    @staticmethod
    def create(db: Session, recipient_id: int, title: str, content: str,
               notification_type: str = "system", related_id: int = None):
        """创建通知"""
        notif = Notification(
            recipient_id=recipient_id,
            title=title,
            content=content,
            notification_type=notification_type,
            related_id=related_id,
        )
        db.add(notif)
        return notif

    @staticmethod
    def get_by_recipient(db: Session, recipient_id: int, limit: int = 50):
        """查询用户通知列表（按时间倒序）"""
        return db.query(Notification).filter(
            Notification.recipient_id == recipient_id,
            Notification.delete_flag == 0,
        ).order_by(Notification.create_time.desc()).limit(limit).all()

    @staticmethod
    def get_unread_count(db: Session, recipient_id: int) -> int:
        """查询未读通知数"""
        return db.query(Notification).filter(
            Notification.recipient_id == recipient_id,
            Notification.is_read == 0,
            Notification.delete_flag == 0,
        ).count()

    @staticmethod
    def mark_read(db: Session, notif_id: int, recipient_id: int):
        """标记单条通知为已读"""
        notif = db.query(Notification).filter(
            Notification.id == notif_id,
            Notification.recipient_id == recipient_id,
            Notification.delete_flag == 0,
        ).first()
        if notif:
            notif.is_read = 1
        return notif

    @staticmethod
    def mark_all_read(db: Session, recipient_id: int):
        """标记所有通知为已读"""
        db.query(Notification).filter(
            Notification.recipient_id == recipient_id,
            Notification.is_read == 0,
            Notification.delete_flag == 0,
        ).update({"is_read": 1})
