"""
粤教服务 - API请求/响应模型
定义所有Pydantic数据模型
"""
from datetime import datetime

from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, Any, Generic, TypeVar, List

# 泛型类型变量，用于响应体模型
T = TypeVar("T")


class BaseSchema(BaseModel):
    """公共基础模型 - 不做任何限制，允许任意字段传入"""
    model_config = ConfigDict(extra="allow")


# ==================== 公共响应体模型 ====================
class ResponseBase(BaseModel, Generic[T]):
    """统一响应体模型"""
    code: int = 200
    message: str = "success"
    data: Optional[T] = None


class PageResult(BaseModel, Generic[T]):
    """分页数据模型"""
    items: List[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 0


class PageResponse(BaseModel, Generic[T]):
    """分页响应体模型"""
    code: int = 200
    message: str = "success"
    data: Optional[PageResult[T]] = None


# ==================== 请求模型 ====================

class UserCreateRequest(BaseModel):
    """用户创建请求"""
    username: str
    password_hash: str
    real_name: str
    user_type: str
    employee_role: Optional[str] = None
    department: Optional[str] = None
    contact_info: Optional[str] = None
    email: Optional[str] = None
    id_card: Optional[str] = None
    country_region: Optional[str] = "中国"


class UserUpdateRequest(BaseModel):
    """用户更新请求"""
    real_name: Optional[str] = None
    user_type: Optional[str] = None
    employee_role: Optional[str] = None
    department: Optional[str] = None
    contact_info: Optional[str] = None
    email: Optional[str] = None
    id_card: Optional[str] = None
    country_region: Optional[str] = None
    avatar: Optional[str] = None
    status: Optional[str] = None


class EventRegisterRequest(BaseModel):
    """活动报名请求"""
    event_id: int
    customer_id: int
    customer_name: str
    contact: Optional[str] = None


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class LeadCreateRequest(BaseModel):
    """意向客户创建请求"""
    customer_name: str
    contact_info: Optional[str] = None
    age: Optional[int] = None
    education: Optional[str] = None
    intended_country: Optional[str] = None
    intended_major: Optional[str] = None
    family_finance: Optional[str] = None
    language_level: Optional[str] = None
    background_info: Optional[str] = None
    status: str = "新增意向"
    source_channel: Optional[str] = None
    score: Optional[int] = 0
    owner_employee_id: Optional[int] = None


class LeadUpdateRequest(BaseModel):
    """意向客户更新请求"""
    customer_name: Optional[str] = None
    contact_info: Optional[str] = None
    age: Optional[int] = None
    education: Optional[str] = None
    intended_country: Optional[str] = None
    intended_major: Optional[str] = None
    family_finance: Optional[str] = None
    language_level: Optional[str] = None
    background_info: Optional[str] = None
    status: Optional[str] = None
    source_channel: Optional[str] = None
    score: Optional[int] = None
    owner_employee_id: Optional[int] = None
    follow_up_history: Optional[str] = None
    next_follow_time: Optional[datetime] = None


class ReportCreateRequest(BaseModel):
    """日报提交请求"""
    employee_id: int
    content: str
    report_date: Optional[str] = None
    work_type: Optional[str] = None


class ScoreCreateRequest(BaseModel):
    """成绩录入请求"""
    student_id: int
    course_name: str
    score: float
    total_score: Optional[float] = None
    pass_score: Optional[float] = 60.0
    exam_type: Optional[str] = None
    exam_time: Optional[datetime] = None
    semester: Optional[str] = None
    teacher_id: Optional[int] = None


class LeaveCreateRequest(BaseModel):
    """请假申请请求"""
    student_id: int
    service_type: str
    leave_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    reason: Optional[str] = None

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        """兼容 '2025-01-01 09:00' 格式的 datetime 字符串"""
        if isinstance(v, str):
            return datetime.strptime(v, "%Y-%m-%d %H:%M")
        return v


class FeedbackCreateRequest(BaseModel):
    """投诉反馈提交请求"""
    student_id: int
    content: str
    detail: Optional[str] = None
    feedback_type: Optional[str] = "咨询"
    urgency_level: Optional[str] = "中"


class RiskLevelEnum(str, Enum):
    """心理预警风险等级"""
    high = "high"
    medium = "medium"
    low = "low"
    none = "none"


class FeedbackResolveRequest(BaseModel):
    """投诉反馈处理请求"""
    solution: str
    handle_user_id: int


class PsychAlertCreateRequest(BaseModel):
    """心理预警提交请求"""
    student_id: int
    trigger_reason: Optional[str] = None
    risk_level: RiskLevelEnum
    alert_source: Optional[str] = "聊天对话"


# ==================== 表1：统一用户表 ====================
class SysUserSchema(BaseSchema):
    id: Optional[int] = None
    username: Optional[str] = None
    password_hash: Optional[str] = None
    real_name: Optional[str] = None
    user_type: Optional[str] = None
    employee_role: Optional[str] = None
    department: Optional[str] = None
    contact_info: Optional[str] = None
    email: Optional[str] = None
    id_card: Optional[str] = None
    avatar: Optional[str] = None
    country_region: Optional[str] = "中国"
    status: Optional[str] = "正常"
    last_login_time: Optional[str] = None
    last_login_ip: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    delete_flag: Optional[int] = 0
    remark: Optional[str] = None


# ==================== 表2：学生行政服务表 ====================
class StudentAdminServiceSchema(BaseSchema):
    id: Optional[int] = None
    student_id: Optional[int] = None
    service_type: Optional[str] = None
    leave_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    reason: Optional[str] = None
    status: Optional[str] = "待审批"
    reject_reason: Optional[str] = None
    approver_id: Optional[int] = None
    related_academic_id: Optional[int] = None
    notify_status: Optional[int] = 0
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    delete_flag: Optional[int] = 0
    remark: Optional[str] = None


# ==================== 表3：心理健康画像表 ====================
class StudentPsychProfileSchema(BaseSchema):
    id: Optional[int] = None
    student_id: Optional[int] = None
    latest_emotion_tag: Optional[str] = None
    emotion_score: Optional[int] = None
    risk_level: Optional[str] = "none"
    total_risk_count: Optional[int] = 0
    teacher_follow_up_status: Optional[str] = "未跟进"
    last_interaction_time: Optional[datetime] = None
    emotion_history: Optional[str] = None
    update_time: Optional[datetime] = None
    delete_flag: Optional[int] = 0
    remark: Optional[str] = None


# ==================== 表4：心理预警记录表 ====================
class StudentPsychAlertSchema(BaseSchema):
    id: Optional[int] = None
    student_id: Optional[int] = None
    trigger_reason: Optional[str] = None
    risk_level: Optional[str] = None
    alert_source: Optional[str] = "聊天对话"
    status: Optional[str] = "未处理"
    teacher_id: Optional[int] = None
    handle_time: Optional[datetime] = None
    handle_content: Optional[str] = None
    create_time: Optional[datetime] = None
    delete_flag: Optional[int] = 0
    remark: Optional[str] = None


# ==================== 表15：组织架构表 ====================
class OrgDepartmentSchema(BaseSchema):
    id: Optional[int] = None
    dept_name: Optional[str] = None
    parent_id: Optional[int] = 0
    dept_level: Optional[int] = 1
    sort_order: Optional[int] = 0
    dept_desc: Optional[str] = None
    manager_id: Optional[int] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    create_time: Optional[datetime] = None
    delete_flag: Optional[int] = 0
    remark: Optional[str] = None


# ==================== 表14：站内通知表 ====================
class NotificationSchema(BaseSchema):
    id: Optional[int] = None
    recipient_id: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None
    notification_type: Optional[str] = None
    related_id: Optional[int] = None
    is_read: Optional[int] = 0
    create_time: Optional[datetime] = None
    delete_flag: Optional[int] = 0
    remark: Optional[str] = None


# ==================== 表5：学生反馈工单表 ====================
class StudentFeedbackTicketSchema(BaseSchema):
    id: Optional[int] = None
    student_id: Optional[int] = None
    feedback_type: Optional[str] = None
    content: Optional[str] = None
    detail: Optional[str] = None
    urgency_level: Optional[str] = "中"
    status: Optional[str] = "待处理"
    solution: Optional[str] = None
    handle_user_id: Optional[int] = None
    handle_time: Optional[datetime] = None
    is_notified: Optional[int] = 0
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    delete_flag: Optional[int] = 0
    remark: Optional[str] = None


# ==================== 表6：意向客户表 ====================
class CrmLeadSchema(BaseSchema):
    id: Optional[int] = None
    customer_name: Optional[str] = None
    contact_info: Optional[str] = None
    age: Optional[int] = None
    education: Optional[str] = None
    intended_country: Optional[str] = None
    intended_major: Optional[str] = None
    family_finance: Optional[str] = None
    language_level: Optional[str] = None
    background_info: Optional[str] = None
    follow_up_history: Optional[str] = None
    status: Optional[str] = "新增意向"
    source_channel: Optional[str] = None
    next_follow_time: Optional[datetime] = None
    score: Optional[int] = 0
    owner_employee_id: Optional[int] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    delete_flag: Optional[int] = 0
    remark: Optional[str] = None


# ==================== 表7：员工日报表 ====================
class EmployeeDailyReportSchema(BaseSchema):
    id: Optional[int] = None
    employee_id: Optional[int] = None
    report_date: Optional[str] = None
    work_type: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    report_status: Optional[str] = "已提交"
    create_time: Optional[datetime] = None
    delete_flag: Optional[int] = 0
    remark: Optional[str] = None


# ==================== 表8：学生成绩表 ====================
class StudentScoreSchema(BaseSchema):
    id: Optional[int] = None
    student_id: Optional[int] = None
    course_name: Optional[str] = None
    score: Optional[float] = None
    total_score: Optional[float] = None
    pass_score: Optional[float] = 60.0
    exam_type: Optional[str] = None
    exam_time: Optional[datetime] = None
    semester: Optional[str] = None
    teacher_id: Optional[int] = None
    create_time: Optional[datetime] = None
    delete_flag: Optional[int] = 0
    remark: Optional[str] = None


# ==================== 表9：课程项目表 ====================
class CourseProjectSchema(BaseSchema):
    id: Optional[int] = None
    project_name: Optional[str] = None
    category: Optional[str] = None
    country: Optional[str] = None
    tuition_fee: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None
    target_audience: Optional[str] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    application_require: Optional[str] = None
    is_recommended: Optional[int] = 0
    sort_order: Optional[int] = 0
    delete_flag: Optional[int] = 0
    remark: Optional[str] = None


# ==================== 表10：活动讲座表 ====================
class EventLectureSchema(BaseSchema):
    id: Optional[int] = None
    event_name: Optional[str] = None
    event_type: Optional[str] = None
    speaker: Optional[str] = None
    cover_image: Optional[str] = None
    start_time: Optional[datetime] = None
    location: Optional[str] = None
    registration_end_time: Optional[datetime] = None
    max_participants: Optional[int] = None
    current_participants: Optional[int] = 0
    event_status: Optional[str] = "未开始"
    creator_id: Optional[int] = None
    create_time: Optional[datetime] = None
    delete_flag: Optional[int] = 0
    remark: Optional[str] = None


# ==================== 表11：活动报名表 ====================
class EventRegistrationSchema(BaseSchema):
    id: Optional[int] = None
    event_id: Optional[int] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    contact: Optional[str] = None
    status: Optional[str] = "已报名"
    check_in_status: Optional[int] = 0
    check_in_time: Optional[datetime] = None
    create_time: Optional[datetime] = None
    delete_flag: Optional[int] = 0
    remark: Optional[str] = None


# ==================== 表12：学生教务信息表 ====================
class StudentAcademicSchema(BaseSchema):
    id: Optional[int] = None
    student_id: Optional[int] = None
    course_name: Optional[str] = None
    academic_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    exam_location: Optional[str] = None
    deadline: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    semester: Optional[str] = None
    ddl_status: Optional[str] = "未完成"
    remind_enabled: Optional[int] = 1
    remind_days_before: Optional[str] = "7,1"
    last_remind_time: Optional[datetime] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    delete_flag: Optional[int] = 0
    remark: Optional[str] = None


class AcademicQueryRequest(BaseModel):
    """教务查询请求"""
    student_id: int
    academic_type: Optional[str] = None  # 考试/论文/作业/项目，不传则查全部


# ==================== 表13：留学业务进度追踪表 ====================
class StudentStudyAbroadProgressSchema(BaseSchema):
    id: Optional[int] = None
    student_id: Optional[int] = None
    target_country: Optional[str] = None
    target_school: Optional[str] = None
    target_major: Optional[str] = None
    degree_level: Optional[str] = None
    stage: Optional[str] = None
    stage_order: Optional[int] = None
    stage_status: Optional[str] = "待开始"
    stage_detail: Optional[str] = None
    handler_name: Optional[str] = None
    handler_contact: Optional[str] = None
    estimated_complete_date: Optional[str] = None
    actual_complete_date: Optional[str] = None
    is_current: Optional[int] = 0
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    delete_flag: Optional[int] = 0
    remark: Optional[str] = None


class StudyAbroadQueryRequest(BaseModel):
    """留学进度查询请求"""
    student_id: int


# ==================== 扩展请求模型 ====================

class StudyAbroadUpdateRequest(BaseModel):
    """留学进度更新请求"""
    target_country: Optional[str] = None
    target_school: Optional[str] = None
    target_major: Optional[str] = None
    degree_level: Optional[str] = None
    stage: Optional[str] = None
    stage_order: Optional[int] = None
    stage_status: Optional[str] = None
    stage_detail: Optional[str] = None
    handler_name: Optional[str] = None
    handler_contact: Optional[str] = None
    estimated_complete_date: Optional[str] = None
    actual_complete_date: Optional[str] = None
    is_current: Optional[int] = None


class EmployeeUpdateRequest(BaseModel):
    """员工信息更新请求"""
    real_name: Optional[str] = None
    department: Optional[str] = None
    employee_role: Optional[str] = None
    contact_info: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None


class ProjectCreateRequest(BaseModel):
    """课程项目创建请求"""
    project_name: str
    category: Optional[str] = ""
    country: Optional[str] = ""
    tuition_fee: Optional[str] = ""
    duration: Optional[str] = ""
    description: Optional[str] = ""
    target_audience: Optional[str] = ""
    application_require: Optional[str] = ""
    is_recommended: Optional[int] = 0
    age_min: Optional[int] = None
    age_max: Optional[int] = None


class ScoreBatchItem(BaseModel):
    """成绩批量导入条目"""
    student_id: int
    course_name: str
    score: float
    total_score: Optional[float] = None
    pass_score: Optional[float] = 60.0
    exam_type: Optional[str] = ""
    exam_time: Optional[str] = None
    semester: Optional[str] = ""
    teacher_id: Optional[int] = None
