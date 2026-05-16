"""
粤教服务 - 数据模型层
定义所有SQLAlchemy ORM模型类
"""

from sqlalchemy import Column, BigInteger, Integer, SmallInteger, String, Text, DateTime, Date, Float, Numeric, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# 基类，所有模型的父类
Base = declarative_base()


# ========== 表1：统一用户表 ==========
class SysUser(Base):
    __tablename__ = "sys_user"
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    username = Column(String(50), nullable=False, unique=True, comment='登录账号')
    password_hash = Column(String(255), nullable=False, comment='加密密码')
    real_name = Column(String(30), nullable=False, comment='真实姓名')
    user_type = Column(String(20), nullable=False, comment='ADMIN/STUDENT/EMPLOYEE')
    employee_role = Column(String(50), comment='员工角色')
    head_teacher_id = Column(BigInteger, comment='班主任ID（STUDENT必填，关联sys_user.id且该用户须为EMPLOYEE+班主任角色）')
    department = Column(String(100), comment='部门/院系')
    contact_info = Column(String(20), comment='手机号')
    email = Column(String(100), comment='邮箱')
    id_card = Column(String(30), comment='身份证')
    avatar = Column(String(255), comment='头像URL')
    country_region = Column(String(30), default='中国', comment='国家/地区')
    status = Column(String(20), default='正常', comment='账号状态')
    last_login_time = Column(DateTime, comment='最后登录时间')
    last_login_ip = Column(String(50), comment='最后登录IP')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    delete_flag = Column(SmallInteger, default=0, comment='软删除 0=正常 1=删除')
    remark = Column(Text, comment='备注')


# ========== 表2：学生行政服务表 ==========
class StudentAdminService(Base):
    __tablename__ = "student_admin_service"
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    student_id = Column(BigInteger, nullable=False, comment='学生ID')
    service_type = Column(String(30), nullable=False, comment='请假/考务')
    leave_type = Column(String(30), comment='病假/事假')
    start_time = Column(DateTime, comment='开始时间')
    end_time = Column(DateTime, comment='结束时间')
    reason = Column(Text, comment='申请原因')
    status = Column(String(20), default='待审批', comment='待审批/已通过/已驳回')
    reject_reason = Column(Text, comment='驳回原因')
    approver_id = Column(BigInteger, comment='审批人ID')
    related_academic_id = Column(BigInteger, comment='关联教务ID')
    notify_status = Column(SmallInteger, default=0, comment='通知状态 0=未通知 1=已通知')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    delete_flag = Column(SmallInteger, default=0, comment='软删除')
    remark = Column(Text, comment='备注')


# ========== 表3：心理健康画像表 ==========
class StudentPsychProfile(Base):
    __tablename__ = "student_psych_profile"
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    student_id = Column(BigInteger, nullable=False, unique=True, comment='学生ID')
    latest_emotion_tag = Column(String(100), comment='最新情绪标签')
    emotion_score = Column(Integer, comment='情绪分数 0-100')
    risk_level = Column(String(20), default='none', comment='high/medium/low/none')
    total_risk_count = Column(Integer, default=0, comment='累计预警次数')
    teacher_follow_up_status = Column(String(20), default='未跟进', comment='老师跟进状态')
    last_interaction_time = Column(DateTime, comment='最后交互时间')
    emotion_history = Column(Text, comment='情绪历史JSON')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    delete_flag = Column(SmallInteger, default=0, comment='软删除')
    remark = Column(Text, comment='备注')


# ========== 表4：心理预警记录表 ==========
class StudentPsychAlert(Base):
    __tablename__ = "student_psych_alert"
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    student_id = Column(BigInteger, nullable=False, comment='学生ID')
    trigger_reason = Column(Text, nullable=False, comment='触发原因')
    risk_level = Column(String(20), nullable=False, comment='high/medium/low/none')
    alert_source = Column(String(50), default='聊天对话', comment='预警来源')
    status = Column(String(20), default='未处理', comment='处理状态')
    teacher_id = Column(BigInteger, comment='负责老师ID')
    handle_time = Column(DateTime, comment='处理时间')
    handle_content = Column(Text, comment='处理记录')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    delete_flag = Column(SmallInteger, default=0, comment='软删除')
    remark = Column(Text, comment='备注')


# ========== 表5：学生反馈工单表 ==========
class StudentFeedbackTicket(Base):
    __tablename__ = "student_feedback_ticket"
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    student_id = Column(BigInteger, nullable=False, comment='学生ID')
    feedback_type = Column(String(30), comment='投诉/建议/咨询')
    content = Column(String(255), nullable=False, comment='反馈摘要')
    detail = Column(Text, comment='反馈详情')
    urgency_level = Column(String(10), default='中', comment='紧急程度')
    status = Column(String(20), default='待处理', comment='处理状态')
    solution = Column(Text, comment='解决方案')
    handle_user_id = Column(BigInteger, comment='处理人ID')
    handle_time = Column(DateTime, comment='处理完成时间')
    is_notified = Column(SmallInteger, default=0, comment='是否通知学生')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    delete_flag = Column(SmallInteger, default=0, comment='软删除')
    remark = Column(Text, comment='备注')


# ========== 表6：意向客户表 ==========
class CrmLead(Base):
    __tablename__ = "crm_lead"
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    customer_name = Column(String(30), nullable=False, comment='客户姓名')
    contact_info = Column(String(20), comment='电话/微信')
    age = Column(Integer, comment='年龄')
    education = Column(String(50), comment='学历')
    intended_country = Column(String(50), comment='意向国家')
    intended_major = Column(String(100), comment='意向专业')
    family_finance = Column(String(50), comment='家庭经济水平')
    language_level = Column(String(50), comment='语言等级')
    background_info = Column(Text, comment='背景信息')
    follow_up_history = Column(Text, comment='跟进记录JSON')
    status = Column(String(30), default='新增意向', comment='客户状态')
    source_channel = Column(String(50), comment='获客渠道')
    next_follow_time = Column(DateTime, comment='下次跟进时间')
    score = Column(Integer, default=0, comment='意向评分 0-100')
    owner_employee_id = Column(BigInteger, nullable=False, comment='归属员工ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    delete_flag = Column(SmallInteger, default=0, comment='软删除')
    remark = Column(Text, comment='备注')


# ========== 表7：员工日报表 ==========
class EmployeeDailyReport(Base):
    __tablename__ = "employee_daily_report"
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    employee_id = Column(BigInteger, nullable=False, comment='员工ID')
    report_date = Column(Date, nullable=False, comment='日报日期')
    work_type = Column(String(50), comment='工作类型')
    content = Column(Text, nullable=False, comment='日报内容')
    summary = Column(Text, comment='AI自动摘要')
    report_status = Column(String(20), default='已提交', comment='提交状态')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    delete_flag = Column(SmallInteger, default=0, comment='软删除')
    remark = Column(Text, comment='备注')


# ========== 表8：学生成绩表 ==========
class StudentScore(Base):
    __tablename__ = "student_score"
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    student_id = Column(BigInteger, nullable=False, comment='学生ID')
    course_name = Column(String(100), nullable=False, comment='课程名称')
    score = Column(Numeric(5, 2), nullable=False, comment='得分')
    total_score = Column(Numeric(5, 2), comment='总分')
    pass_score = Column(Numeric(5, 2), default=60, comment='及格线')
    exam_type = Column(String(30), comment='期中/期末/语言考试')
    exam_time = Column(DateTime, comment='考试时间')
    semester = Column(String(30), comment='学期')
    teacher_id = Column(BigInteger, comment='录入老师ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    delete_flag = Column(SmallInteger, default=0, comment='软删除')
    remark = Column(Text, comment='备注')


# ========== 表9：课程项目表 ==========
class CourseProject(Base):
    __tablename__ = "course_project"
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    project_name = Column(String(100), nullable=False, comment='项目名称')
    category = Column(String(50), comment='项目类别')
    country = Column(String(50), comment='所属国家')
    tuition_fee = Column(String(100), comment='学费')
    duration = Column(String(50), comment='学制')
    description = Column(Text, comment='项目介绍')
    target_audience = Column(String(255), comment='适合人群')
    age_min = Column(Integer, comment='最低年龄要求')
    age_max = Column(Integer, comment='最高年龄要求')
    application_require = Column(Text, comment='申请要求')
    is_recommended = Column(SmallInteger, default=0, comment='是否推荐 0=否 1=是')
    sort_order = Column(Integer, default=0, comment='排序序号')
    delete_flag = Column(SmallInteger, default=0, comment='软删除')
    remark = Column(Text, comment='备注')


# ========== 表10：活动讲座表 ==========
class EventLecture(Base):
    __tablename__ = "event_lecture"
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    event_name = Column(String(100), nullable=False, comment='活动名称')
    event_type = Column(String(20), comment='线上/线下')
    speaker = Column(String(50), comment='主讲人')
    cover_image = Column(String(255), comment='封面图')
    start_time = Column(DateTime, nullable=False, comment='活动开始时间')
    location = Column(String(255), comment='地点/直播链接')
    registration_end_time = Column(DateTime, comment='报名截止时间')
    max_participants = Column(Integer, comment='最大参与人数')
    current_participants = Column(Integer, default=0, comment='当前报名人数')
    event_status = Column(String(20), default='未开始', comment='活动状态')
    creator_id = Column(BigInteger, comment='创建人ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    delete_flag = Column(SmallInteger, default=0, comment='软删除')
    remark = Column(Text, comment='备注')


# ========== 表11：活动报名表 ==========
class EventRegistration(Base):
    __tablename__ = "event_registration"
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    event_id = Column(BigInteger, ForeignKey("event_lecture.id"), nullable=False, comment='活动ID')
    customer_id = Column(BigInteger, nullable=False, comment='客户ID')
    customer_name = Column(String(30), comment='客户姓名')
    contact = Column(String(20), comment='联系方式')
    status = Column(String(20), default='已报名', comment='报名状态')
    check_in_status = Column(SmallInteger, default=0, comment='签到状态 0=未签到 1=已签到')
    check_in_time = Column(DateTime, comment='签到时间')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    delete_flag = Column(SmallInteger, default=0, comment='软删除')
    remark = Column(Text, comment='备注')


# ========== 表12：学生教务信息表 ==========
class StudentAcademic(Base):
    __tablename__ = "student_academic"
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    student_id = Column(BigInteger, nullable=False, comment='学生ID')
    course_name = Column(String(100), nullable=False, comment='课程名称')
    academic_type = Column(String(30), nullable=False, comment='类型：考试/论文/作业/项目')
    title = Column(String(200), nullable=False, comment='考试/作业标题')
    description = Column(Text, comment='详细描述')
    exam_location = Column(String(200), comment='考试地点')
    deadline = Column(DateTime, nullable=False, comment='考试时间/截止日期')
    duration_minutes = Column(Integer, comment='考试时长（分钟）')
    semester = Column(String(30), comment='学期')
    ddl_status = Column(String(20), default='未完成', comment='完成状态：未完成/已完成/已逾期')
    remind_enabled = Column(SmallInteger, default=1, comment='是否开启提醒')
    remind_days_before = Column(String(30), default='7,1', comment='提前提醒天数')
    last_remind_time = Column(DateTime, comment='最近一次提醒时间')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    delete_flag = Column(SmallInteger, default=0, comment='软删除')
    remark = Column(Text, comment='备注')


# ========== 表13：留学业务进度追踪表 ==========
class StudentStudyAbroadProgress(Base):
    __tablename__ = "student_study_abroad_progress"
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    student_id = Column(BigInteger, nullable=False, comment='学生ID')
    target_country = Column(String(50), nullable=False, comment='目标国家')
    target_school = Column(String(200), nullable=False, comment='目标院校')
    target_major = Column(String(200), comment='目标专业')
    degree_level = Column(String(30), comment='学位：本科/硕士/博士')
    stage = Column(String(50), nullable=False, comment='当前阶段')
    stage_order = Column(Integer, nullable=False, comment='阶段序号 1-7')
    stage_status = Column(String(30), default='待开始', comment='阶段状态')
    stage_detail = Column(Text, comment='阶段详情/备注')
    handler_name = Column(String(30), comment='负责人姓名')
    handler_contact = Column(String(50), comment='负责人联系方式')
    estimated_complete_date = Column(Date, comment='预计完成日期')
    actual_complete_date = Column(Date, comment='实际完成日期')
    is_current = Column(SmallInteger, default=0, comment='是否为当前进行中阶段')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    delete_flag = Column(SmallInteger, default=0, comment='软删除')
    remark = Column(Text, comment='备注')
