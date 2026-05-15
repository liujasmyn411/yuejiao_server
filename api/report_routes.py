"""
粤教服务 - 智能报告 API 路由
处理仪表盘、客户分析、日报/周报汇总、心理健康周报、投诉处理周报
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from crud import DashboardCRUD

router = APIRouter(prefix="/api/reports", tags=["智能报告"])


# ==================== 管理仪表盘 ====================

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    """管理仪表盘数据"""
    return DashboardCRUD.get_stats(db)


# ==================== 客户经营分析 ====================

@router.get("/customer")
def customer_report(db: Session = Depends(get_db)):
    """客户经营分析报告（月报）"""
    from reports.report_generator import ReportGenerator
    gen = ReportGenerator()
    return gen.generate(db, "customer_analysis")


# ==================== 员工日报/周报汇总 ====================

@router.get("/daily")
def daily_report(date: str = "", employee_id: int = 0, db: Session = Depends(get_db)):
    """员工日报汇总"""
    from reports.report_generator import ReportGenerator
    gen = ReportGenerator()
    params = {}
    if date:
        params["date"] = date
    if employee_id:
        params["employee_id"] = employee_id
    return gen.generate(db, "daily_summary", params)


@router.get("/weekly")
def weekly_report(db: Session = Depends(get_db)):
    """员工周报汇总"""
    from reports.report_generator import ReportGenerator
    gen = ReportGenerator()
    return gen.generate(db, "weekly_summary")


# ==================== 学生心理健康 / 投诉处理周报 ====================

@router.get("/psych-weekly")
def psych_weekly_report(db: Session = Depends(get_db)):
    """学生心理健康周报"""
    from reports.report_generator import ReportGenerator
    gen = ReportGenerator()
    return gen.generate(db, "psych_weekly")


@router.get("/complaint-weekly")
def complaint_weekly_report(db: Session = Depends(get_db)):
    """投诉处理周报"""
    from reports.report_generator import ReportGenerator
    gen = ReportGenerator()
    return gen.generate(db, "complaint_weekly")
