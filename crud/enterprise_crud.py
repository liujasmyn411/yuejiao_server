"""
粤教服务 - 企业智能助手 CRUD 数据访问层
封装CRM客户管理、员工日报、学生成绩、员工查询、仪表盘的数据库操作
"""

from sqlalchemy.orm import Session
from datetime import datetime

from model import CrmLead, EmployeeDailyReport, StudentScore, SysUser, StudentFeedbackTicket, StudentPsychAlert


class CrmCRUD:
    """意向客户(CRM)数据访问对象"""

    @staticmethod
    def create(db: Session, **kwargs):
        """创建意向客户"""
        lead = CrmLead(**kwargs)
        db.add(lead)
        return lead

    @staticmethod
    def get_by_id(db: Session, lead_id: int):
        """根据ID查询客户"""
        return db.query(CrmLead).filter(
            CrmLead.id == lead_id,
            CrmLead.delete_flag == 0
        ).first()

    @staticmethod
    def get_all(db: Session, status: str = ""):
        """查询客户列表（支持按状态筛选，按创建时间倒序）"""
        query = db.query(CrmLead).filter(CrmLead.delete_flag == 0)
        if status:
            query = query.filter(CrmLead.status == status)
        return query.order_by(CrmLead.create_time.desc()).all()

    @staticmethod
    def update(db: Session, lead_id: int, **kwargs):
        """更新客户信息（仅更新非None字段）"""
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
        """查询日报列表（支持按员工筛选，按日期倒序）"""
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
        """根据学生ID查询成绩（按考试时间倒序）"""
        return db.query(StudentScore).filter(
            StudentScore.student_id == student_id,
            StudentScore.delete_flag == 0
        ).order_by(StudentScore.exam_time.desc()).all()


class EmployeeCRUD:
    """员工数据访问对象"""

    @staticmethod
    def get_all(db: Session):
        """查询所有在职员工列表（user_type=EMPLOYEE 且未删除）"""
        return db.query(SysUser).filter(
            SysUser.user_type == "EMPLOYEE",
            SysUser.delete_flag == 0
        ).all()

    @staticmethod
    def get_by_id(db: Session, employee_id: int):
        """根据ID查询员工"""
        return db.query(SysUser).filter(
            SysUser.id == employee_id,
            SysUser.user_type == "EMPLOYEE",
            SysUser.delete_flag == 0
        ).first()


class DashboardCRUD:
    """仪表盘数据访问对象"""

    @staticmethod
    def get_stats(db: Session):
        """获取企业仪表盘统计数据（客户/投诉/心理预警/日报）"""
        # 客户统计
        total_leads = db.query(CrmLead).filter(CrmLead.delete_flag == 0).count()
        status_counts = {}
        for s in ["新增意向", "跟进中", "已签约", "已流失"]:
            status_counts[s] = db.query(CrmLead).filter(
                CrmLead.status == s,
                CrmLead.delete_flag == 0
            ).count()

        # 投诉统计
        total_tickets = db.query(StudentFeedbackTicket).filter(
            StudentFeedbackTicket.delete_flag == 0
        ).count()
        pending_tickets = db.query(StudentFeedbackTicket).filter(
            StudentFeedbackTicket.status == "待处理",
            StudentFeedbackTicket.delete_flag == 0
        ).count()

        # 心理预警统计
        high_risk = db.query(StudentPsychAlert).filter(
            StudentPsychAlert.risk_level == "high",
            StudentPsychAlert.delete_flag == 0
        ).count()
        medium_risk = db.query(StudentPsychAlert).filter(
            StudentPsychAlert.risk_level == "medium",
            StudentPsychAlert.delete_flag == 0
        ).count()

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
