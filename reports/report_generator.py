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

    @staticmethod
    def _is_llm_error(text: str) -> bool:
        return isinstance(text, str) and (
            text.startswith("__LLM_ERROR__") or text.startswith("[LLM")
        )

    def _fallback_psych_insight(self, data: dict) -> str:
        """心理周报本地兜底洞察"""
        lines = [
            "## 本周心理态势概述",
            f"本周共产生 **{data.get('本周预警数', 0)}** 条心理预警，其中高危 **{data.get('高危预警数', 0)}** 条、中危 **{data.get('中危预警数', 0)}** 条。",
            f"全局风险学生共 **{data.get('全局风险学生数', 0)}** 人，高危学生 **{data.get('高危学生数', 0)}** 人。",
            "",
            "## 情绪分布与风险识别",
        ]
        emotion_tags = data.get("情绪标签分布", {})
        if emotion_tags:
            lines.append("| 情绪标签 | 人数 |")
            lines.append("|---------|------|")
            for tag, count in emotion_tags.items():
                lines.append(f"| {tag} | {count} |")
        else:
            lines.append("本周暂无情绪标签数据。")
        lines.append("")
        sub_risks = data.get("细分风险", {})
        lines.append("**细分风险统计：**")
        for k, v in sub_risks.items():
            lines.append(f"- {k}：**{v}** 人")
        cycle = data.get("周期节点", "")
        if cycle:
            lines.extend(["", "## 周期节点提示", cycle])
        lines.extend([
            "",
            "## 行动建议",
            "1. 对高危学生优先安排一对一访谈或心理老师介入。",
            "2. 针对学业焦虑学生，组织学习小组或考前辅导。",
            "3. 关注孤独感学生的社交融入，推荐参加社团或集体活动。",
            "4. 结合当前周期节点，提前调配心理疏导资源。",
            "",
            "> ⚠️ 注：AI 深度分析服务暂时不可用，以上为基于数据的自动摘要。",
        ])
        return "\n".join(lines)

    def _fallback_customer_insight(self, data: dict) -> str:
        """客户分析本地兜底洞察"""
        lines = [
            "## 客户经营概况",
            f"报告周期：**{data.get('报告周期', '本月')}**",
            f"客户总数：**{data.get('客户总数', 0)}** 人",
            f"本月新增：**{data.get('本月新增', 0)}** 人（上月 {data.get('上月新增', 0)} 人）",
            f"高意向客户(≥70分)：**{data.get('高意向客户数(≥70分)', 0)}** 人",
            f"成交客户数：**{data.get('成交客户数', 0)}** 人",
            "",
            "## 渠道与分布",
        ]
        by_source = data.get("渠道分布", {})
        if by_source:
            lines.append("| 渠道 | 数量 |")
            lines.append("|------|------|")
            for k, v in by_source.items():
                lines.append(f"| {k} | {v} |")
        lines.append("")
        risk = data.get("流失风险", {})
        lines.extend([
            "## 流失风险",
            f"- 高风险：**{risk.get('高风险', 0)}** 人",
            f"- 中风险：**{risk.get('中风险', 0)}** 人",
            f"- 低风险：**{risk.get('低风险', 0)}** 人",
            "",
            "## 建议",
            "1. 对高风险客户尽快安排回访，了解流失原因。",
            "2. 针对高意向客户推进签约转化。",
            "3. 优化本月表现较好的获客渠道投放。",
            "",
            "> ⚠️ 注：AI 深度分析服务暂时不可用，以上为基于数据的自动摘要。",
        ])
        return "\n".join(lines)

    def _fallback_daily_summary(self, data: dict) -> str:
        """日报汇总本地兜底洞察"""
        reports = data.get("reports", [])
        risk_flags = data.get("risk_flags", [])
        lines = [
            "## 日报概览",
            f"共汇总 **{data.get('count', 0)}** 份日报。",
            "",
            "## 核心工作",
        ]
        work_types = {}
        for r in reports:
            wt = r.get("work_type") or "未分类"
            work_types[wt] = work_types.get(wt, 0) + 1
        for wt, cnt in work_types.items():
            lines.append(f"- {wt}：**{cnt}** 人")
        if risk_flags:
            lines.extend(["", "## 潜在风险", "以下日报中识别到风险关键词："])
            for rf in risk_flags[:10]:
                lines.append(f"- {rf}")
        else:
            lines.extend(["", "## 潜在风险", "今日暂无明显的风险关键词。"])
        lines.extend([
            "",
            "## 明日建议",
            "1. 关注风险日报中提到的阻塞点，及时协调资源。",
            "2. 对延迟/未解决事项设置明确的完成时限。",
            "",
            "> ⚠️ 注：AI 深度分析服务暂时不可用，以上为基于数据的自动摘要。",
        ])
        return "\n".join(lines)

    def _fallback_weekly_summary(self, data: dict) -> str:
        """周报汇总本地兜底洞察"""
        risk_flags = data.get("risk_flags", [])
        lines = [
            "## 本周概览",
            f"本周共提交 **{data.get('total_reports', 0)}** 份日报，涉及 **{data.get('employee_count', 0)}** 位员工。",
            f"时间范围：{data.get('start_date', '')} ~ {data.get('end_date', '')}",
            "",
            "## 潜在风险",
        ]
        if risk_flags:
            for rf in risk_flags[:15]:
                lines.append(f"- {rf}")
        else:
            lines.append("本周暂无明显的风险关键词。")
        lines.extend([
            "",
            "## 下周建议",
            "1. 对多次出现风险关键词的员工进行一对一沟通。",
            "2. 梳理本周阻塞事项，制定下周排期与资源计划。",
            "3. 总结本周关键产出，在周会上同步给相关方。",
            "",
            "> ⚠️ 注：AI 深度分析服务暂时不可用，以上为基于数据的自动摘要。",
        ])
        return "\n".join(lines)

    def _fallback_complaint_insight(self, data: dict) -> str:
        """投诉周报本地兜底洞察"""
        lines = [
            "## 投诉概况",
            f"周期：**{data.get('周期', '本周')}**",
            f"总工单数：**{data.get('总工单数', 0)}** 条",
            f"上周工单数：**{data.get('上周工单数', 0)}** 条",
            f"环比变化：**{data.get('环比变化', 'N/A')}**",
            f"待处理：**{data.get('待处理', 0)}** 条",
            "",
            "## 分类统计",
        ]
        by_type = data.get("按类型", {})
        if by_type:
            lines.append("| 类型 | 数量 |")
            lines.append("|------|------|")
            for k, v in by_type.items():
                lines.append(f"| {k} | {v} |")
        lines.append("")
        by_urgency = data.get("按紧急程度", {})
        if by_urgency:
            lines.append("**按紧急程度：**")
            for k, v in by_urgency.items():
                lines.append(f"- {k}：**{v}** 条")
        lines.extend([
            "",
            "## 改进建议",
            "1. 优先处理高紧急度与待处理工单，避免超时升级。",
            "2. 对占比最高的投诉类型进行根因复盘。",
            "3. 若环比上升明显，需排查近期服务流程或服务政策变更。",
            "",
            "> ⚠️ 注：AI 深度分析服务暂时不可用，以上为基于数据的自动摘要。",
        ])
        return "\n".join(lines)

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
        """全域客户经营分析报告 —— 覆盖意向/成交/流失三大客群"""
        from model import CrmLead
        from sqlalchemy import func

        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)
        # 上月
        last_month_end = month_start - timedelta(seconds=1)
        last_month_start = datetime(last_month_end.year, last_month_end.month, 1)
        # 去年同期
        last_year_start = datetime(now.year - 1, now.month, 1)
        last_year_end = datetime(now.year - 1, now.month + 1, 1) if now.month < 12 else datetime(now.year, 1, 1)

        leads = db.query(CrmLead).filter(CrmLead.delete_flag == 0).all()

        # 基础统计
        total = len(leads)
        new_this_month = sum(1 for l in leads if l.create_time and l.create_time >= month_start)
        new_last_month = sum(1 for l in leads if l.create_time and last_month_start <= l.create_time <= last_month_end)
        new_last_year = sum(1 for l in leads if l.create_time and last_year_start <= l.create_time < last_year_end)

        by_status = {}
        by_country = {}
        by_source = {}
        by_education = {}
        scores = []
        deal_leads = []
        at_risk = []

        for l in leads:
            status = l.status or "未知"
            by_status[status] = by_status.get(status, 0) + 1
            by_country[l.intended_country or "未指定"] = by_country.get(l.intended_country or "未指定", 0) + 1
            by_source[l.source_channel or "未知"] = by_source.get(l.source_channel or "未知", 0) + 1
            by_education[l.education or "未知"] = by_education.get(l.education or "未知", 0) + 1
            if l.score:
                scores.append(l.score)
            # 成交客户（状态包含成交/签约）
            if status in ("已成交", "已签约", "成交", "签约"):
                deal_leads.append(l)
            # 流失风险：30天未更新 或 next_follow_time 已过期
            if l.update_time and (now - l.update_time).days > 30:
                at_risk.append({"id": l.id, "name": l.customer_name, "days": (now - l.update_time).days, "score": l.score or 0})
            elif l.next_follow_time and l.next_follow_time < now:
                at_risk.append({"id": l.id, "name": l.customer_name, "days": (now - l.next_follow_time).days, "score": l.score or 0})

        avg_score = sum(scores) / len(scores) if scores else 0

        # 特征聚类：学历 × 国家 TOP5
        cluster = {}
        for l in leads:
            key = f"{l.education or '未知'}|{l.intended_country or '未指定'}"
            cluster[key] = cluster.get(key, 0) + 1
        top_clusters = sorted(cluster.items(), key=lambda x: x[1], reverse=True)[:5]

        # 流失风险分层
        high_risk = [r for r in at_risk if r["days"] > 60 or (r["score"] and r["score"] < 30)]
        medium_risk = [r for r in at_risk if 30 < r["days"] <= 60 and (not r["score"] or r["score"] >= 30)]
        low_risk = [r for r in at_risk if r["days"] <= 30]

        data_summary = {
            "报告周期": f"{now.year}年{now.month}月",
            "客户总数": total,
            "本月新增": new_this_month,
            "上月新增": new_last_month,
            "去年同期新增": new_last_year,
            "状态分布": by_status,
            "意向国家分布": by_country,
            "渠道分布": by_source,
            "学历分布": by_education,
            "平均意向评分": round(avg_score, 1),
            "高意向客户数(≥70分)": sum(1 for s in scores if s >= 70),
            "成交客户数": len(deal_leads),
            "特征聚类TOP5": [{"画像": k, "数量": v} for k, v in top_clusters],
            "流失风险": {
                "高风险": len(high_risk),
                "中风险": len(medium_risk),
                "低风险": len(low_risk),
                "风险客户明细": high_risk[:10],
            },
        }

        prompt = f"""你是资深教育行业数据分析师。请基于以下客户经营数据，输出专业洞察：

1. 意向客户分析：新增趋势解读（同环比）、特征聚类洞察、高潜客群建议
2. 成交客户分析：成交客户画像、转化路径推断（基于创建时间与当前状态）
3. 流失风险分析：风险归因、挽回策略建议
4.  actionable 建议：下月获客、转化、挽回的具体动作

数据：{data_summary}
"""
        ai_insight = self.llm.chat(prompt, "请生成客户经营分析报告")
        if self._is_llm_error(ai_insight):
            ai_insight = self._fallback_customer_insight(data_summary)

        return {
            "report_type": "customer_analysis",
            "title": f"{now.year}年{now.month}月 全域客户经营分析报告",
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "data": data_summary,
            "insight": ai_insight,
        }

    # ==================== 2. 日报汇总 ====================

    def generate_daily_summary(self, db, params: dict) -> dict:
        """员工日报智能汇总（单日）"""
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

        # AI 智能汇总
        summaries = "\n".join(f"- {r.content[:200]}" for r in reports)
        risk_keywords = ["延迟", "阻塞", "客户不满", "投诉", "风险", "问题", "困难", "未解决"]
        risk_flags = []
        for r in reports:
            for kw in risk_keywords:
                if kw in (r.content or ""):
                    risk_flags.append(f"员工{r.employee_id}: {kw}")
                    break

        ai_prompt = f"""你是团队管理助手。请将以下日报内容提炼为结构化简报：

1. 核心工作进展（3-5条）
2. 关键产出
3. 潜在风险与待解决问题
4. 明日工作建议

日报内容：
{summaries}

请用Markdown格式输出，控制在300字内。"""

        ai_summary = self.llm.chat(ai_prompt, "请汇总日报") if len(reports) > 1 else (reports[0].content or "")
        if len(reports) > 1 and self._is_llm_error(ai_summary):
            ai_summary = self._fallback_daily_summary({
                "date": report_date,
                "count": len(reports),
                "reports": report_list,
                "risk_flags": risk_flags,
            })

        return {
            "report_type": "daily_summary",
            "title": f"{report_date} 员工日报智能汇总",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {
                "date": report_date,
                "count": len(reports),
                "reports": report_list,
                "risk_flags": risk_flags,
            },
            "summary": ai_summary,
        }

    # ==================== 3. 周报汇总 ====================

    def generate_weekly_summary(self, db, params: dict) -> dict:
        """员工日报智能汇总（周报）"""
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

        # AI 智能周报
        all_content = "\n".join(f"[{r.report_date}] {r.content[:200]}" for r in reports[:30])
        risk_keywords = ["延迟", "阻塞", "客户不满", "投诉", "风险", "问题", "困难", "未解决"]
        risk_flags = []
        for r in reports:
            for kw in risk_keywords:
                if kw in (r.content or ""):
                    risk_flags.append(f"员工{r.employee_id}({r.report_date}): {kw}")
                    break

        ai_prompt = f"""你是团队负责人。请将以下一周的日报汇总为结构化周报。

要求：
1. 本周核心工作亮点（3-5条）
2. 关键产出与数据
3. 潜在风险与待解决问题
4. 下周工作建议与资源调配

日报内容：
{all_content}

请用Markdown格式输出，控制在500字内。"""

        ai_weekly = self.llm.chat(ai_prompt, "请汇总本周周报")
        if self._is_llm_error(ai_weekly):
            ai_weekly = self._fallback_weekly_summary({
                "start_date": str(week_start),
                "end_date": str(week_end),
                "total_reports": len(reports),
                "employee_count": len(by_employee),
                "by_employee": {str(k): v for k, v in by_employee.items()},
                "risk_flags": risk_flags,
            })

        return {
            "report_type": "weekly_summary",
            "title": f"{week_start} ~ {week_end} 员工日报智能汇总（周报）",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {
                "start_date": str(week_start),
                "end_date": str(week_end),
                "total_reports": len(reports),
                "employee_count": len(by_employee),
                "by_employee": {str(k): v for k, v in by_employee.items()},
                "risk_flags": risk_flags,
            },
            "summary": ai_weekly,
        }

    # ==================== 4. 心理健康周报 ====================

    def generate_psych_weekly(self, db, params: dict) -> dict:
        """学生心理健康周报 —— 情绪聚类 + 周期节点 + 疏导方案"""
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

        # 情绪标签聚类
        emotion_tags = {}
        for p in profiles:
            tag = p.latest_emotion_tag or "未标注"
            emotion_tags[tag] = emotion_tags.get(tag, 0) + 1

        # 细分风险识别（基于关键词）
        loneliness = [p for p in profiles if p.latest_emotion_tag and any(kw in p.latest_emotion_tag for kw in ["孤独", "孤单", "寂寞", "想家"])]
        anxiety = [p for p in profiles if p.latest_emotion_tag and any(kw in p.latest_emotion_tag for kw in ["焦虑", "紧张", "压力", "担心", "害怕"])]
        culture = [p for p in profiles if p.latest_emotion_tag and any(kw in p.latest_emotion_tag for kw in ["文化", "适应", "冲突", "歧视", "语言"])]

        # 留学周期节点判断（简化版：1/6/7/12月视为特殊节点）
        cycle_note = ""
        if today.month in (1, 6):
            cycle_note = "当前处于考试周附近，需重点关注学业焦虑"
        elif today.month in (7, 8):
            cycle_note = "当前处于暑假期间，需关注孤独感与社交缺失"
        elif today.month in (12, 2):
            cycle_note = "当前处于节假日期间，需关注思乡情绪与文化适应"

        data_summary = {
            "周期": f"{week_start} ~ {today}",
            "本周预警数": len(alerts),
            "高危预警数": sum(1 for a in alerts if a.risk_level == "high"),
            "中危预警数": sum(1 for a in alerts if a.risk_level == "medium"),
            "高危学生数": len(high_risk_students),
            "全局风险学生数": len(profiles),
            "情绪标签分布": emotion_tags,
            "细分风险": {
                "孤独感": len(loneliness),
                "学业焦虑": len(anxiety),
                "文化冲突": len(culture),
            },
            "周期节点": cycle_note,
        }

        ai_prompt = f"""你是海外留学生心理健康专家。请基于以下数据生成心理健康周报：

1. 本周整体心理态势概述
2. 精准识别风险群体（孤独感/学业焦虑/文化冲突）及具体表现
3. 结合留学周期节点（如考试周、假期）分析情绪波动趋势
4. 为每类风险群体推荐个性化心理疏导方案与社群支持建议
5. 需要班主任重点跟进的学生清单及建议话术

数据：{data_summary}
"""
        ai_insight = self.llm.chat(ai_prompt, "请生成心理健康周报")
        if self._is_llm_error(ai_insight):
            ai_insight = self._fallback_psych_insight(data_summary)

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
        """投诉处理周报 —— AI智能分类 + 同环比 + 热点TOP3"""
        from model import StudentFeedbackTicket

        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        last_week_start = week_start - timedelta(days=7)

        # 本周工单
        tickets = db.query(StudentFeedbackTicket).filter(
            StudentFeedbackTicket.create_time >= week_start,
            StudentFeedbackTicket.delete_flag == 0,
        ).order_by(StudentFeedbackTicket.create_time.desc()).all()

        # 上周工单（用于同环比）
        last_week_tickets = db.query(StudentFeedbackTicket).filter(
            StudentFeedbackTicket.create_time >= last_week_start,
            StudentFeedbackTicket.create_time < week_start,
            StudentFeedbackTicket.delete_flag == 0,
        ).count()

        if not tickets:
            return {
                "report_type": "complaint_weekly",
                "title": f"{week_start} ~ {today} 投诉处理周报",
                "message": "本周无投诉反馈",
                "data": {
                    "count": 0,
                    "上周工单数": last_week_tickets,
                    "环比变化": f"-100%（上周{last_week_tickets}条）" if last_week_tickets else "持平",
                },
            }

        # 基础统计
        by_type = {}
        by_status = {}
        by_urgency = {}
        for t in tickets:
            ftype = t.feedback_type or "其他"
            by_type[ftype] = by_type.get(ftype, 0) + 1
            by_status[t.status or "未知"] = by_status.get(t.status or "未知", 0) + 1
            by_urgency[t.urgency_level or "中"] = by_urgency.get(t.urgency_level or "中", 0) + 1

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

        # AI 智能分类：将投诉内容分类为预设类别
        contents = [t.content or "" for t in tickets[:20]]
        ai_classify_prompt = f"""请将以下投诉/反馈内容分类到最匹配的类别中。类别选项：签证办理、院校申请、生活服务、教学质量、费用问题、住宿问题、其他。

投诉内容：
"""
        for i, c in enumerate(contents, 1):
            ai_classify_prompt += f"{i}. {c[:60]}...\n"
        ai_classify_prompt += "\n请返回JSON格式：{{'1': '类别名', '2': '类别名', ...}}"

        try:
            ai_classify_result = self.llm.chat(ai_classify_prompt, "请分类投诉内容")
            # 简单解析：按行找 "数字. 类别" 或统计关键词出现次数做 fallback
            ai_categories = {}
            for line in ai_classify_result.split("\n"):
                for cat in ["签证办理", "院校申请", "生活服务", "教学质量", "费用问题", "住宿问题", "其他"]:
                    if cat in line:
                        ai_categories[cat] = ai_categories.get(cat, 0) + 1
        except Exception:
            ai_categories = {}

        # 同环比
        week_change = ((len(tickets) - last_week_tickets) / max(last_week_tickets, 1)) * 100
        change_str = f"{'+' if week_change >= 0 else ''}{week_change:.0f}%"

        data_summary = {
            "周期": f"{week_start} ~ {today}",
            "总工单数": len(tickets),
            "上周工单数": last_week_tickets,
            "环比变化": change_str,
            "待处理": len(pending),
            "按类型": by_type,
            "按状态": by_status,
            "按紧急程度": by_urgency,
            "AI智能分类": ai_categories,
        }

        ai_prompt = f"""你是客户服务分析专家。请基于以下投诉周报数据生成洞察：

1. 本周投诉总量及环比趋势解读
2. AI智能分类后的热点问题TOP3及根因分析
3. 按紧急程度的风险评估
4. 具体改进建议与预防措施
5. 下周需要重点跟进的事项

数据：{data_summary}
"""
        ai_insight = self.llm.chat(ai_prompt, "请生成投诉处理周报")
        if self._is_llm_error(ai_insight):
            ai_insight = self._fallback_complaint_insight(data_summary)

        return {
            "report_type": "complaint_weekly",
            "title": f"{week_start} ~ {today} 投诉处理周报",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": data_summary,
            "tickets": ticket_list,
            "insight": ai_insight,
        }
