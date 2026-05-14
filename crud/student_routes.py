
"""
粤教服务 - CRUD数据访问层
封装所有数据库的增删改查操作
"""

from sqlalchemy.orm import Session
from datetime import datetime

from model import (
    SysUser, EventLecture, EventRegistration, CourseProject,
    CrmLead, EmployeeDailyReport, StudentScore,
    StudentAdminService, StudentPsychProfile, StudentPsychAlert,
    StudentFeedbackTicket
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
        """根据ID查询用户"""
        return db.query(SysUser).filter(SysUser.id == user_id, SysUser.delete_flag == 0).first()

    @staticmethod
    def get_by_username(db: Session, username: str):
        """根据用户名查询用户"""
        return db.query(SysUser).filter(SysUser.username == username, SysUser.delete_flag == 0).first()

    @staticmethod
    def get_student_by_id(db: Session, student_id: int):
        """根据ID查询学生（user_type=STUDENT 且 delete_flag=0）"""
        return db.query(SysUser).filter(
            SysUser.id == student_id,
            SysUser.user_type == "STUDENT",
            SysUser.delete_flag == 0
        ).first()

    @staticmethod
    def update(db: Session, user_id: int, **kwargs):
        """更新用户信息"""
        user = UserCRUD.get_by_id(db, user_id)
        if user:
            for key, value in kwargs.items():
                if value is not None:
                    setattr(user, key, value)
        return user

    @staticmethod
    def delete(db: Session, user_id: int):
        """软删除用户"""
        user = UserCRUD.get_by_id(db, user_id)
        if user:
            user.delete_flag = 1
        return user


class EventCRUD:
    """活动讲座数据访问对象"""

    @staticmethod
    def create(db: Session, **kwargs):
        """创建活动"""
        event = EventLecture(**kwargs)
        db.add(event)
        return event

    @staticmethod
    def get_by_id(db: Session, event_id: int):
        """根据ID查询活动"""
        return db.query(EventLecture).filter(EventLecture.id == event_id, EventLecture.delete_flag == 0).first()

    @staticmethod
    def get_all(db: Session):
        """查询所有活动"""
        return db.query(EventLecture).filter(EventLecture.delete_flag == 0).order_by(EventLecture.start_time.desc()).all()

    @staticmethod
    def register(db: Session, event_id: int, customer_id: int = None, customer_name: str = "", contact: str = ""):
        """活动报名"""
        registration = EventRegistration(
            event_id=event_id,
            customer_id=customer_id,
            customer_name=customer_name,
            contact=contact
        )
        db.add(registration)
        # 更新报名人数
        event = EventCRUD.get_by_id(db, event_id)
        if event:
            event.current_participants = (event.current_participants or 0) + 1
        return registration

    @staticmethod
    def get_registrations(db: Session, event_id: int):
        """查询活动报名列表"""
        return db.query(EventRegistration).filter(
            EventRegistration.event_id == event_id,
            EventRegistration.delete_flag == 0
        ).all()


class ProjectCRUD:
    """课程项目数据访问对象"""

    @staticmethod
    def create(db: Session, **kwargs):
        """创建项目"""
        project = CourseProject(**kwargs)
        db.add(project)
        return project

    @staticmethod
    def get_by_id(db: Session, project_id: int):
        """根据ID查询项目"""
        return db.query(CourseProject).filter(CourseProject.id == project_id, CourseProject.delete_flag == 0).first()

    @staticmethod
    def get_all(db: Session, category: str = ""):
        """查询所有项目"""
        query = db.query(CourseProject).filter(CourseProject.delete_flag == 0)
        if category:
            query = query.filter(CourseProject.category == category)
        return query.order_by(CourseProject.sort_order).all()


class CrmCRUD:
    """意向客户数据访问对象"""

    @staticmethod
    def create(db: Session, **kwargs):
        """创建客户"""
        lead = CrmLead(**kwargs)
        db.add(lead)
        return lead

    @staticmethod
    def get_by_id(db: Session, lead_id: int):
        """根据ID查询客户"""
        return db.query(CrmLead).filter(CrmLead.id == lead_id, CrmLead.delete_flag == 0).first()

    @staticmethod
    def get_all(db: Session, status: str = ""):
        """查询客户列表"""
        query = db.query(CrmLead).filter(CrmLead.delete_flag == 0)
        if status:
            query = query.filter(CrmLead.status == status)
        return query.order_by(CrmLead.create_time.desc()).all()

    @staticmethod
    def update(db: Session, lead_id: int, **kwargs):
        """更新客户信息"""
        lead = CrmCRUD.get_by_id(db, lead_id)
        if lead:
            for key, value in kwargs.items():
                if value is not None:
                    setattr(lead, key, value)
        return lead


class ReportCRUD:
    """员工日报数据访问对象"""

    @staticmethod
    def create(db: Session, **kwargs):
        """提交日报"""
        report = EmployeeDailyReport(**kwargs)
        db.add(report)
        return report

    @staticmethod
    def get_all(db: Session, employee_id: int = 0):
        """查询日报列表"""
        query = db.query(EmployeeDailyReport).filter(EmployeeDailyReport.delete_flag == 0)
        if employee_id:
            query = query.filter(EmployeeDailyReport.employee_id == employee_id)
        return query.order_by(EmployeeDailyReport.report_date.desc()).all()


class ScoreCRUD:
    """学生成绩数据访问对象"""

    @staticmethod
    def create(db: Session, **kwargs):
        """录入成绩"""
        score = StudentScore(**kwargs)
        db.add(score)
        return score

    @staticmethod
    def get_by_student(db: Session, student_id: int):
        """查询学生成绩"""
        return db.query(StudentScore).filter(
            StudentScore.student_id == student_id,
            StudentScore.delete_flag == 0
        ).order_by(StudentScore.exam_time.desc()).all()


class StudentServiceCRUD:
    """学生行政服务数据访问对象"""

    @staticmethod
    def create_leave(db: Session, req: LeaveCreateRequest):
        """提交请假申请"""
        # 防重复检测：同一学生在相同时间段、相同请假类型的申请已存在
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
        """查询请假记录"""
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
        """提交投诉反馈"""
        data = req.model_dump(exclude_none=True)
        data["status"] = "待处理"
        ticket = StudentFeedbackTicket(**data)
        db.add(ticket)
        return ticket

    @staticmethod
    def get_all(db: Session, student_id: int = 0):
        """查询投诉反馈"""
        query = db.query(StudentFeedbackTicket).filter(StudentFeedbackTicket.delete_flag == 0)
        if student_id:
            query = query.filter(StudentFeedbackTicket.student_id == student_id)
        return query.order_by(StudentFeedbackTicket.create_time.desc()).all()


class PsychAlertCRUD:
    """心理预警数据访问对象"""

    @staticmethod
    def create(db: Session, req: PsychAlertCreateRequest):
        """提交心理预警"""
        data = req.model_dump(exclude_none=True)
        data["status"] = "未处理"
        alert = StudentPsychAlert(**data)
        db.add(alert)
        return alert

    @staticmethod
    def get_all(db: Session, risk_level: str = ""):
        """查询心理预警"""
        query = db.query(StudentPsychAlert).filter(StudentPsychAlert.delete_flag == 0)
        if risk_level:
            query = query.filter(StudentPsychAlert.risk_level == risk_level)
        return query.order_by(StudentPsychAlert.create_time.desc()).all()

    @staticmethod
    def update_profile(db: Session, student_id: int, risk_level: str):
        """更新心理画像"""
        profile = db.query(StudentPsychProfile).filter(
            StudentPsychProfile.student_id == student_id,
            StudentPsychProfile.delete_flag == 0
        ).first()

        if profile:
            profile.latest_emotion_tag = risk_level
            profile.risk_level = "high" if risk_level == "高" else ("medium" if risk_level == "中" else "low")
            profile.emotion_score = 20 if risk_level == "高" else (40 if risk_level == "中" else 60)
            profile.total_risk_count = (profile.total_risk_count or 0) + 1
            profile.teacher_follow_up_status = "未跟进"
            profile.last_interaction_time = datetime.now()
        else:
            new_profile = StudentPsychProfile(
                student_id=student_id,
                latest_emotion_tag=risk_level,
                risk_level="high" if risk_level == "高" else ("medium" if risk_level == "中" else "low"),
                emotion_score=20 if risk_level == "高" else 40,
                total_risk_count=1,
                teacher_follow_up_status="未跟进",
                last_interaction_time=datetime.now()
            )
            db.add(new_profile)


class DashboardCRUD:
    """仪表盘数据访问对象"""

    @staticmethod
    def get_stats(db: Session):
        """获取统计数据"""
        # 客户统计
        total_leads = db.query(CrmLead).filter(CrmLead.delete_flag == 0).count()
        status_counts = {}
        for s in ["新增意向", "跟进中", "已签约", "已流失"]:
            status_counts[s] = db.query(CrmLead).filter(CrmLead.status == s, CrmLead.delete_flag == 0).count()

        # 投诉统计
        total_tickets = db.query(StudentFeedbackTicket).filter(StudentFeedbackTicket.delete_flag == 0).count()
        pending_tickets = db.query(StudentFeedbackTicket).filter(
            StudentFeedbackTicket.status == "待处理",
            StudentFeedbackTicket.delete_flag == 0
        ).count()

        # 心理预警统计
        high_risk = db.query(StudentPsychAlert).filter(StudentPsychAlert.risk_level == "高", StudentPsychAlert.delete_flag == 0).count()
        medium_risk = db.query(StudentPsychAlert).filter(StudentPsychAlert.risk_level == "中", StudentPsychAlert.delete_flag == 0).count()

        # 日报统计
        today = datetime.now().strftime("%Y-%m-%d")
        today_reports = db.query(EmployeeDailyReport).filter(
            EmployeeDailyReport.report_date == today,
            EmployeeDailyReport.delete_flag == 0
        ).count()

        return {
            "customers": {"total": total_leads, "by_status": status_counts},
            "feedback": {"total": total_tickets, "pending": pending_tickets},
            "psych_alerts": {"high": high_risk, "medium": medium_risk},
            "daily_reports": {"today": today_reports}
        }
