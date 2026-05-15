"""
智能报告生成器
支持 5 类报告：客户分析/日报汇总/周报汇总/心理周报/投诉周报
"""
from datetime import datetime, date, timedelta
from utils.llm_client import get_llm_client


class ReportGenerator:
    """智能报告生成引擎"""

    def __init__(self):
        self.llm = get_llm_client()

    def generate(self, db, report_type: str, params: dict = None) -> dict:
        """统一报告生成入口

        report_type:
          - customer_analysis: 全域客户经营分析报告（月报）
          - daily_summary: 员工日报汇总（日报）
          - weekly_summary: 员工日报汇总（周报）
          - psych_weekly: 学生心理健康周报
          - complaint_weekly: 投诉处理周报
        """
        params = params or {}
        generators = {
            "customer_analysis": self.generate_customer_analysis,
            "daily_summary": self.generate_daily_summary,
            "weekly_summary": self.generate_weekly_summary,
            "psych_weekly": self.generate_psych_weekly,
            "complaint_weekly": self.generate_complaint_weekly,
        }
        gen = generators.get(report_type)
        if not gen:
            return {"error": f"未知报告类型: {report_type}", "available": list(generators.keys())}
        return gen(db, params)

    # ==================== 1. 客户分析报告（月报） ====================

    def generate_customer_analysis(self, db, params: dict) -> dict:
        """全域客户经营分析报告"""
        from model import CrmLead

        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)

        leads = db.query(CrmLead).filter(
            CrmLead.delete_flag == 0
        ).all()

        # 统计数据
        total = len(leads)
        new_this_month = sum(1 for l in leads if l.create_time and l.create_time >= month_start)
        by_status = {}
        by_country = {}
        by_source = {}
        scores = []

        for l in leads:
            status = l.status or "未知"
            by_status[status] = by_status.get(status, 0) + 1
            country = l.intended_country or "未指定"
            by_country[country] = by_country.get(country, 0) + 1
            source = l.source_channel or "未知"
            by_source[source] = by_source.get(source, 0) + 1
            if l.score:
                scores.append(l.score)

        avg_score = sum(scores) / len(scores) if scores else 0

        # LLM 生成洞察
        data_summary = {
            "报告周期": f"{now.year}年{now.month}月",
            "客户总数": total,
            "本月新增": new_this_month,
            "状态分布": by_status,
            "意向国家分布": by_country,
            "渠道分布": by_source,
            "平均意向评分": round(avg_score, 1),
            "高意向客户数": sum(1 for s in scores if s >= 70),
        }

        ai_insight = self.llm.generate_report("客户经营分析月报", data_summary)

        return {
            "report_type": "customer_analysis",
            "title": f"{now.year}年{now.month}月 客户经营分析报告",
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "data": data_summary,
            "insight": ai_insight,
        }

    # ==================== 2. 日报汇总 ====================

    def generate_daily_summary(self, db, params: dict) -> dict:
        """员工日报汇总（单日）"""
        from model import EmployeeDailyReport

        report_date = params.get("date", date.today().strftime("%Y-%m-%d"))
        employee_id = params.get("employee_id")

        q = db.query(EmployeeDailyReport).filter(
            EmployeeDailyReport.report_date == report_date,
            EmployeeDailyReport.delete_flag == 0,
        )
        if employee_id:
            q = q.filter(EmployeeDailyReport.employee_id == employee_id)

        reports = q.order_by(EmployeeDailyReport.create_time.desc()).all()

        if not reports:
            return {
                "report_type": "daily_summary",
                "title": f"{report_date} 日报汇总",
                "message": "当日无日报提交",
                "data": {"count": 0, "reports": []},
            }

        report_list = [
            {
                "employee_id": r.employee_id,
                "work_type": r.work_type,
                "content": r.content,
                "summary": r.summary,
                "status": r.report_status,
            }
            for r in reports
        ]

        # AI 汇总
        summaries = "\n".join(f"- {r.content[:200]}" for r in reports)
        ai_summary = self.llm.chat(
            f"将以下日报内容汇总为一段简洁的今日工作总结（200字内）：\n{summaries}",
            "请汇总"
        ) if len(reports) > 1 else (reports[0].content or "")

        return {
            "report_type": "daily_summary",
            "title": f"{report_date} 日报汇总",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {
                "date": report_date,
                "count": len(reports),
                "reports": report_list,
            },
            "summary": ai_summary,
        }

    # ==================== 3. 周报汇总 ====================

    def generate_weekly_summary(self, db, params: dict) -> dict:
        """员工日报汇总（周报）"""
        from model import EmployeeDailyReport

        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        reports = db.query(EmployeeDailyReport).filter(
            EmployeeDailyReport.report_date >= week_start,
            EmployeeDailyReport.report_date <= week_end,
            EmployeeDailyReport.delete_flag == 0,
        ).order_by(EmployeeDailyReport.report_date.asc()).all()

        if not reports:
            return {
                "report_type": "weekly_summary",
                "title": f"{week_start} ~ {week_end} 周报汇总",
                "message": "本周无日报提交",
                "data": {"count": 0, "start_date": str(week_start), "end_date": str(week_end)},
            }

        # 按员工分组
        by_employee = {}
        for r in reports:
            eid = r.employee_id
            if eid not in by_employee:
                by_employee[eid] = []
            by_employee[eid].append({
                "date": str(r.report_date),
                "content": r.content,
                "work_type": r.work_type,
            })

        # AI 周报
        all_content = "\n".join(f"[{r.report_date}] {r.content[:200]}" for r in reports[:30])
        ai_weekly = self.llm.chat(
            f"""你是团队负责人。请将以下一周的日报汇总为周报。

要求：
1. 本周核心工作亮点（3-5条）
2. 关键数据（如有）
3. 风险和待解决问题
4. 下周工作建议

日报内容：
{all_content}

请用Markdown格式输出。""",
            "请汇总本周周报"
        )

        return {
            "report_type": "weekly_summary",
            "title": f"{week_start} ~ {week_end} 周报汇总",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {
                "start_date": str(week_start),
                "end_date": str(week_end),
                "total_reports": len(reports),
                "employee_count": len(by_employee),
                "by_employee": {str(k): v for k, v in by_employee.items()},
            },
            "summary": ai_weekly,
        }

    # ==================== 4. 心理健康周报 ====================

    def generate_psych_weekly(self, db, params: dict) -> dict:
        """学生心理健康周报"""
        from model import StudentPsychAlert, StudentPsychProfile

        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        # 本周预警
        alerts = db.query(StudentPsychAlert).filter(
            StudentPsychAlert.create_time >= week_start,
            StudentPsychAlert.delete_flag == 0,
        ).order_by(StudentPsychAlert.create_time.desc()).all()

        # 全局画像
        profiles = db.query(StudentPsychProfile).filter(
            StudentPsychProfile.delete_flag == 0,
            StudentPsychProfile.risk_level != "none",
        ).all()

        high_risk_students = [
            {"student_id": p.student_id, "emotion_tag": p.latest_emotion_tag,
             "score": p.emotion_score, "risk_count": p.total_risk_count}
            for p in profiles if p.risk_level == "high"
        ]

        alert_list = [
            {
                "student_id": a.student_id,
                "risk_level": a.risk_level,
                "trigger_reason": a.trigger_reason,
                "status": a.status,
                "created": str(a.create_time)[:16] if a.create_time else "",
            }
            for a in alerts[:50]
        ]

        # AI 分析
        data_summary = {
            "周期": f"{week_start} ~ {today}",
            "本周预警数": len(alerts),
            "高危预警数": sum(1 for a in alerts if a.risk_level == "high"),
            "中危预警数": sum(1 for a in alerts if a.risk_level == "medium"),
            "高危学生数": len(high_risk_students),
            "全局风险学生数": len(profiles),
        }

        ai_insight = self.llm.generate_report("学生心理健康周报", data_summary)

        return {
            "report_type": "psych_weekly",
            "title": f"{week_start} ~ {today} 学生心理健康周报",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {
                **data_summary,
                "high_risk_students": high_risk_students,
                "alerts": alert_list,
            },
            "insight": ai_insight,
        }

    # ==================== 5. 投诉处理周报 ====================

    def generate_complaint_weekly(self, db, params: dict) -> dict:
        """投诉处理周报"""
        from model import StudentFeedbackTicket

        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        tickets = db.query(StudentFeedbackTicket).filter(
            StudentFeedbackTicket.create_time >= week_start,
            StudentFeedbackTicket.delete_flag == 0,
        ).order_by(StudentFeedbackTicket.create_time.desc()).all()

        if not tickets:
            return {
                "report_type": "complaint_weekly",
                "title": f"{week_start} ~ {today} 投诉处理周报",
                "message": "本周无投诉反馈",
                "data": {"count": 0},
            }

        # 分类统计
        by_type = {}
        by_status = {}
        by_urgency = {}

        for t in tickets:
            ftype = t.feedback_type or "其他"
            by_type[ftype] = by_type.get(ftype, 0) + 1
            status = t.status or "未知"
            by_status[status] = by_status.get(status, 0) + 1
            urgency = t.urgency_level or "中"
            by_urgency[urgency] = by_urgency.get(urgency, 0) + 1

        pending = [t for t in tickets if t.status == "待处理"]

        ticket_list = [
            {
                "id": t.id,
                "student_id": t.student_id,
                "type": t.feedback_type,
                "content": t.content,
                "urgency": t.urgency_level,
                "status": t.status,
                "created": str(t.create_time)[:16] if t.create_time else "",
            }
            for t in tickets[:50]
        ]

        data_summary = {
            "周期": f"{week_start} ~ {today}",
            "总工单数": len(tickets),
            "待处理": len(pending),
            "按类型": by_type,
            "按状态": by_status,
            "按紧急程度": by_urgency,
        }

        ai_insight = self.llm.generate_report("投诉处理周报", data_summary)

        return {
            "report_type": "complaint_weekly",
            "title": f"{week_start} ~ {today} 投诉处理周报",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": data_summary,
            "tickets": ticket_list,
            "insight": ai_insight,
        }
