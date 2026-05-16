from crud.customer_crud import EventCRUD, ProjectCRUD
from crud.enterprise_crud import CrmCRUD, ReportCRUD, ScoreCRUD, EmployeeCRUD, DashboardCRUD, OrgCRUD
from crud.student_crud import (
    UserCRUD, StudentServiceCRUD, FeedbackCRUD, PsychAlertCRUD,
    AcademicCRUD, StudyAbroadCRUD, NotificationCRUD,
)

__all__ = [
    # 客服智能助手
    "EventCRUD",
    "ProjectCRUD",
    # 企业智能助手
    "CrmCRUD",
    "ReportCRUD",
    "ScoreCRUD",
    "EmployeeCRUD",
    "DashboardCRUD",
    "OrgCRUD",
    # 学生智能助手
    "UserCRUD",
    "StudentServiceCRUD",
    "FeedbackCRUD",
    "PsychAlertCRUD",
    "AcademicCRUD",
    "StudyAbroadCRUD",
    "NotificationCRUD",
]
