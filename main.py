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
from database import get_db, create_tables, SessionLocal
from model import EventLecture, EventRegistration, CourseProject, CrmLead, EmployeeDailyReport
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

# 允许跨域访问（Dify需要调用这个API）
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
        # 检查是否已有数据
        if db.query(EventLecture).count() == 0:
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
                    category="新加坡-本科",
                    description="初中毕业生可通过2+2学制获得本科文凭，国内2年+新加坡2年，总学费约30-31万",
                    target_audience="应往届初中毕业生，年龄14-16岁"
                ),
                CourseProject(
                    project_name="0.5/1+2新加坡定向培养本科班",
                    category="新加坡-本科",
                    description="高中生可通过0.5/1+2学制快速获得本科文凭，总学费约25-26万",
                    target_audience="高二在读、高中/中职/中技毕业生，年龄16-19岁"
                ),
                CourseProject(
                    project_name="6+6酒店运营大专就业班",
                    category="新加坡-大专",
                    description="6个月理论+6个月带薪实习，一年获大专文凭，就业薪资15000+/月",
                    target_audience="职高/中专/中职/技校学生，年满17岁"
                ),
                CourseProject(
                    project_name="9+6航空运营大专就业班",
                    category="新加坡-大专",
                    description="9个月理论+6个月带薪实习，一年获大专文凭，就业薪资15000+/月",
                    target_audience="职高/中专/中职/技校学生，年满17岁"
                ),
                CourseProject(
                    project_name="中德精英人才共建计划",
                    category="德国-双元制",
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

    # 启动时创建表+插入测试数据
    create_tables()
    init_sample_data()

    logger.info("=" * 50)
    logger.info("粤教服务 API 服务启动成功！")
    logger.info("=" * 50)
    logger.info(f"API地址: http://{settings.api_host}:{settings.api_port}")
    logger.info(f"API文档: http://{settings.api_host}:{settings.api_port}/docs")
    logger.info(f"健康检查: http://{settings.api_host}:{settings.api_port}/health")
    logger.info("=" * 50)

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
