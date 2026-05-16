"""
粤教服务 AI Agent - Python API服务
客服Agent + 企业助手 + 学生助手 的数据接口
运行方式: python main.py
访问地址: http://localhost:8000
文档地址: http://localhost:8000/docs
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from utils import setup_logging
from utils.scheduler import start_scheduler
from database import get_db, create_tables, SessionLocal
from model import (
    EventLecture, EventRegistration, CourseProject, CrmLead,
    EmployeeDailyReport, StudentAcademic, StudentStudyAbroadProgress,
    OrgDepartment,
)
from api import router
from config import settings

# 初始化日志
logger = setup_logging()


# ========== 创建FastAPI应用 ==========
app = FastAPI(
    title=settings.api_title,
    description="客服Agent + 企业助手 + 学生助手 的数据接口服务",
    version=settings.api_version
)

# 允许跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)


# ==================== 初始化测试数据 ====================

def init_sample_data():
    """启动时自动插入测试数据（仅首次）"""
    from datetime import datetime

    db = SessionLocal()
    try:
        # 检查是否已有数据（任一核心表为空则初始化）
        has_data = (
            db.query(EventLecture).count() > 0 and
            db.query(StudentAcademic).count() > 0 and
            db.query(StudentStudyAbroadProgress).count() > 0 and
            db.query(OrgDepartment).count() > 0
        )
        if not has_data:
            logger.info("正在初始化测试数据...")

            # 示例活动
            events = [
                EventLecture(
                    event_name="新加坡留学线上分享会——如何用3年完成本硕连读",
                    event_type="线上",
                    start_time=datetime(2026, 5, 20, 19, 0),
                    location="腾讯会议（会议号：123-456-789）",
                    max_participants=100, current_participants=67
                ),
                EventLecture(
                    event_name="德国双元制教育线下说明会",
                    event_type="线下",
                    start_time=datetime(2026, 5, 25, 14, 0),
                    location="广州市越秀区东风东路723号高教大厦2楼会议室A",
                    max_participants=50, current_participants=32
                ),
                EventLecture(
                    event_name="留学签证政策解读——2026年最新变化",
                    event_type="线上",
                    start_time=datetime(2026, 6, 1, 20, 0),
                    location="抖音直播间（搜索'粤教服务'）",
                    max_participants=500, current_participants=189
                ),
            ]
            for e in events:
                db.add(e)

            # 示例项目
            projects = [
                CourseProject(
                    project_name="2+2新加坡定向培养本科班",
                    category="新加坡-本科", country="新加坡",
                    description="初中毕业生可通过2+2学制获得本科文凭，国内2年+新加坡2年，总学费约30-31万",
                    target_audience="应往届初中毕业生，年龄14-16岁"
                ),
                CourseProject(
                    project_name="0.5/1+2新加坡定向培养本科班",
                    category="新加坡-本科", country="新加坡",
                    description="高中生可通过0.5/1+2学制快速获得本科文凭，总学费约25-26万",
                    target_audience="高二在读、高中/中职/中技毕业生，年龄16-19岁"
                ),
                CourseProject(
                    project_name="6+6酒店运营大专就业班",
                    category="新加坡-大专", country="新加坡",
                    description="6个月理论+6个月带薪实习，一年获大专文凭，就业薪资15000+/月",
                    target_audience="职高/中专/中职/技校学生，年满17岁"
                ),
                CourseProject(
                    project_name="9+6航空运营大专就业班",
                    category="新加坡-大专", country="新加坡",
                    description="9个月理论+6个月带薪实习，一年获大专文凭，就业薪资15000+/月",
                    target_audience="职高/中专/中职/技校学生，年满17岁"
                ),
                CourseProject(
                    project_name="中德精英人才共建计划",
                    category="德国-双元制", country="德国",
                    description="德国双元制职业教育，免学费享补贴，保就业可移民，平均薪资2100-3500欧/月",
                    target_audience="18-35岁，高中及以上学历"
                ),
            ]
            for p in projects:
                db.add(p)

            # 示例意向客户
            leads = [
                CrmLead(customer_name="张三", contact_info="13800138000",
                        background_info="19岁，高中生，家里经济条件好",
                        status="新增意向", owner_employee_id=1),
                CrmLead(customer_name="李四", contact_info="13900139000",
                        background_info="28岁，本科学历，想移民德国",
                        status="跟进中", owner_employee_id=1),
                CrmLead(customer_name="王五", contact_info="13700137000",
                        background_info="17岁，职高毕业，想找工作",
                        status="新增意向", owner_employee_id=1),
            ]
            for l in leads:
                db.add(l)

            # 示例日报
            reports = [
                EmployeeDailyReport(employee_id=1, report_date="2026-05-12",
                                    content="今天跟进3个客户。张三对新加坡项目意向强烈，已安排下周面试；李四还在考虑费用问题；王五决定不报，已标记流失。"),
                EmployeeDailyReport(employee_id=1, report_date="2026-05-11",
                                    content="参加了新加坡项目培训会，更新了政策知识。新增2个意向客户，都来自线上咨询。"),
            ]
            for r in reports:
                db.add(r)

            # 示例教务数据
            academics = [
                StudentAcademic(student_id=4, course_name="高等数学（下）", academic_type="考试",
                               title="高等数学（下）期末考试", description="涵盖微积分、线性代数，闭卷笔试",
                               exam_location="教学楼A301",
                               deadline=datetime(2026, 6, 20, 9, 0), duration_minutes=120,
                               semester="2025-2026第二学期"),
                StudentAcademic(student_id=4, course_name="Python程序设计", academic_type="项目",
                               title="图书管理系统大作业", description="独立完成一个带GUI的图书管理系统",
                               deadline=datetime(2026, 6, 10, 23, 59),
                               semester="2025-2026第二学期"),
                StudentAcademic(student_id=4, course_name="大学英语", academic_type="论文",
                               title="跨文化交际课程论文", description="3000词英文论文，格式APA",
                               deadline=datetime(2026, 6, 5, 23, 59),
                               semester="2025-2026第二学期"),
                StudentAcademic(student_id=5, course_name="综合英语", academic_type="考试",
                               title="综合英语期末考试", description="听力+阅读+写作+翻译",
                               exam_location="教学楼B102",
                               deadline=datetime(2026, 6, 18, 14, 0), duration_minutes=150,
                               semester="2025-2026第二学期"),
            ]
            for a in academics:
                db.add(a)

            # 示例留学进度
            progresses = [
                StudentStudyAbroadProgress(
                    student_id=4, target_country="英国", target_school="帝国理工学院",
                    target_major="计算机科学", degree_level="硕士",
                    stage="文书准备", stage_order=1, stage_status="已完成",
                    stage_detail="个人陈述初稿已完成，推荐信已联系2位教授",
                    handler_name="王强", handler_contact="wangqiang@yuejiao.edu",
                    estimated_complete_date="2026-05-10", actual_complete_date="2026-05-08",
                    is_current=0),
                StudentStudyAbroadProgress(
                    student_id=4, target_country="英国", target_school="帝国理工学院",
                    target_major="计算机科学", degree_level="硕士",
                    stage="文书审核", stage_order=2, stage_status="已完成",
                    stage_detail="文书老师已完成一审",
                    handler_name="王强", handler_contact="wangqiang@yuejiao.edu",
                    estimated_complete_date="2026-05-15", actual_complete_date="2026-05-14",
                    is_current=0),
                StudentStudyAbroadProgress(
                    student_id=4, target_country="英国", target_school="帝国理工学院",
                    target_major="计算机科学", degree_level="硕士",
                    stage="院校申请", stage_order=3, stage_status="进行中",
                    stage_detail="已提交在线申请表，材料完整待审核",
                    handler_name="王强", handler_contact="wangqiang@yuejiao.edu",
                    estimated_complete_date="2026-05-30", is_current=1),
                StudentStudyAbroadProgress(
                    student_id=5, target_country="新加坡", target_school="新加坡国立大学",
                    target_major="商科", degree_level="本科",
                    stage="文书准备", stage_order=1, stage_status="已完成",
                    stage_detail="个人陈述初稿完成，推荐信1封已到位",
                    handler_name="陈美玲", handler_contact="chenml@yuejiao.edu",
                    estimated_complete_date="2026-05-20", actual_complete_date="2026-05-18",
                    is_current=0),
                StudentStudyAbroadProgress(
                    student_id=5, target_country="新加坡", target_school="新加坡国立大学",
                    target_major="商科", degree_level="本科",
                    stage="文书审核", stage_order=2, stage_status="进行中",
                    stage_detail="文书老师已反馈初稿意见，需补充课外活动经历",
                    handler_name="陈美玲", handler_contact="chenml@yuejiao.edu",
                    estimated_complete_date="2026-05-25", is_current=1),
            ]
            for p in progresses:
                db.add(p)

            # 示例组织架构
            org_depts = [
                OrgDepartment(id=1, dept_name="粤教服务", parent_id=0, dept_level=1, sort_order=1,
                             dept_desc="广东省教育服务有限公司总部", contact_phone="020-37628058",
                             contact_email="info@yuejiao.edu"),
                OrgDepartment(id=2, dept_name="市场部", parent_id=1, dept_level=2, sort_order=1,
                             dept_desc="负责线上线下获客、品牌推广、渠道合作", manager_id=2,
                             contact_phone="020-37628059", contact_email="marketing@yuejiao.edu"),
                OrgDepartment(id=3, dept_name="销售部", parent_id=1, dept_level=2, sort_order=2,
                             dept_desc="负责意向客户跟进、签约转化、客户关系维护", manager_id=1,
                             contact_phone="020-37628060", contact_email="sales@yuejiao.edu"),
                OrgDepartment(id=4, dept_name="教务部", parent_id=1, dept_level=2, sort_order=3,
                             dept_desc="负责课程安排、考试管理、学籍管理、班主任工作", manager_id=3,
                             contact_phone="020-37628061", contact_email="academic@yuejiao.edu"),
                OrgDepartment(id=5, dept_name="留学服务部", parent_id=1, dept_level=2, sort_order=4,
                             dept_desc="负责留学规划、文书辅导、院校申请、签证服务", manager_id=4,
                             contact_phone="020-37628062", contact_email="abroad@yuejiao.edu"),
                OrgDepartment(id=6, dept_name="客服部", parent_id=1, dept_level=2, sort_order=5,
                             dept_desc="负责客户咨询、投诉处理、满意度回访", manager_id=5,
                             contact_phone="020-37628063", contact_email="cs@yuejiao.edu"),
                OrgDepartment(id=7, dept_name="线上咨询组", parent_id=2, dept_level=3, sort_order=1,
                             dept_desc="抖音/公众号/官网等线上渠道咨询转化"),
                OrgDepartment(id=8, dept_name="线下活动组", parent_id=2, dept_level=3, sort_order=2,
                             dept_desc="线下说明会/校园讲座/展会等活动策划与执行"),
                OrgDepartment(id=9, dept_name="新加坡项目组", parent_id=3, dept_level=3, sort_order=1,
                             dept_desc="专注新加坡留学项目的销售转化"),
                OrgDepartment(id=10, dept_name="德国项目组", parent_id=3, dept_level=3, sort_order=2,
                             dept_desc="专注德国双元制项目的销售转化"),
            ]
            for d in org_depts:
                db.add(d)

            db.commit()
            logger.info("测试数据初始化完成")
        else:
            logger.info("数据库已有数据，跳过初始化")
    except Exception as e:
        logger.error(f"初始化数据出错: {e}")
    finally:
        db.close()


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn

    # 启动时创建表+插入测试数据+启动定时任务
    create_tables()
    init_sample_data()
    start_scheduler()

    logger.info("=" * 50)
    logger.info("粤教服务 API 服务启动成功！")
    logger.info("=" * 50)
    logger.info(f"API地址: http://{settings.api_host}:{settings.api_port}")
    logger.info(f"API文档: http://{settings.api_host}:{settings.api_port}/docs")
    logger.info(f"健康检查: http://{settings.api_host}:{settings.api_port}/health")
    logger.info("=" * 50)

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
