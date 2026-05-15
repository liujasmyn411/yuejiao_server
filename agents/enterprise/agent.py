"""
企业助手 Agent - 对内智能办公助手
支持 NL2SQL / 日报 / CRM / 新人指引 等
"""
import json
from agents.enterprise.prompts import (
    SYSTEM_PROMPT, INTENT_DESCRIPTIONS, GUIDE_PROMPT
)
from agents.enterprise.nl2sql import NL2SQL
from agents.enterprise.voice_processor import VoiceProcessor
from knowledge_base.vectorizer import get_rag_engine
from utils.llm_client import get_llm_client


class EnterpriseAgent:
    """粤教服务企业智能助手"""

    def __init__(self):
        self.llm = get_llm_client()
        self.rag = get_rag_engine()
        self.nl2sql = NL2SQL()
        self.voice = VoiceProcessor()
        self.name = "企业智能助手"

    # ==================== 意图路由 ====================

    def route_intent(self, user_input: str, db=None) -> dict:
        """识别意图并路由到对应处理器"""
        result = self.llm.classify_intent(user_input, INTENT_DESCRIPTIONS)
        intent = result.get("intent", "data_query")

        handlers = {
            "lead_create": self._handle_lead_create,
            "lead_query": self._handle_lead_query,
            "lead_update": self._handle_lead_update,
            "daily_report": self._handle_daily_report,
            "report_query": self._handle_report_query,
            "data_query": self._handle_data_query,
            "company_guide": self._handle_company_guide,
            "approval": self._handle_approval,
            "dashboard": self._handle_dashboard,
            "chitchat": self._handle_chitchat,
        }

        handler = handlers.get(intent, self._handle_data_query)
        response = handler(user_input, result.get("entities", {}), db)
        return {"intent": intent, "response": response, "confidence": result.get("confidence", 0.5)}

    # ==================== 意图处理器 ====================

    def _handle_lead_create(self, user_input: str, entities: dict, db) -> str:
        """录入意向客户 —— 提取信息后引导确认"""
        info = self.llm.extract_info(
            user_input,
            ["姓名", "年龄", "学历", "意向国家", "意向专业", "联系方式", "背景信息"]
        )
        if not info.get("姓名"):
            return "请提供客户的基本信息，至少需要姓名哦~ 比如：'录入新客户张三，19岁，高中生，想去新加坡读本科'"

        return (
            f"已识别到客户信息，请确认：\n"
            + "\n".join(f"  • {k}: {v}" for k, v in info.items() if v)
            + "\n\n确认无误后可通过 POST /api/enterprise/lead 接口录入系统。"
        )

    def _handle_lead_query(self, user_input: str, entities: dict, db) -> str:
        """查询意向客户"""
        if not db:
            return "数据库连接不可用，请稍后重试"
        try:
            result = self.nl2sql.query(db, user_input)
            if "error" in result:
                return f"查询失败: {result['error']}\n请尝试更具体的描述，如'查询所有意向为新加坡的客户'"

            data = result.get("data", [])
            if not data:
                return "没有找到符合条件的客户记录。"

            lines = [f"共找到 {len(data)} 条客户记录："]
            for i, row in enumerate(data[:10], 1):
                name = row.get("customer_name", "未知")
                status = row.get("status", "")
                country = row.get("intended_country", "")
                score = row.get("score", "")
                lines.append(f"  {i}. {name} | {status} | 意向: {country} | 评分: {score}")
            if len(data) > 10:
                lines.append(f"  ... 还有 {len(data) - 10} 条记录")
            return "\n".join(lines)
        except Exception as e:
            return f"查询出错: {e}"

    def _handle_lead_update(self, user_input: str, entities: dict, db) -> str:
        """更新意向客户状态"""
        info = self.llm.extract_info(
            user_input,
            ["客户姓名", "新状态", "跟进备注", "意向评分"]
        )
        name = info.get("客户姓名", "")
        if not name:
            return "请说明要更新哪位客户的信息，如'把张三的状态更新为已签约'"

        return (
            f"已识别到更新请求：\n"
            f"  客户: {name}\n"
            f"  新状态: {info.get('新状态', '未指定')}\n"
            f"  备注: {info.get('跟进备注', '无')}\n"
            f"  评分: {info.get('意向评分', '未变')}\n\n"
            f"请通过 PUT /api/enterprise/lead/{{id}} 接口完成更新。"
        )

    def _handle_daily_report(self, user_input: str, entities: dict, db) -> str:
        """口述日报 → 结构化整理"""
        report = self.voice.text_to_report(user_input)
        lines = [
            "📋 日报已整理如下：",
            f"日期: {report.get('report_date', '')}",
            f"类型: {report.get('work_type', '')}",
            "",
            "核心内容:",
            report.get("summary", ""),
        ]
        todos = report.get("todos", "")
        if todos and todos != "None":
            lines.append(f"\n待办: {todos}")
        lines.append("\n确认无误后可通过 POST /api/enterprise/report 提交。")
        return "\n".join(lines)

    def _handle_report_query(self, user_input: str, entities: dict, db) -> str:
        """查询日报数据"""
        if not db:
            return "数据库连接不可用"
        try:
            result = self.nl2sql.query(db, user_input)
            if "error" in result:
                return f"查询失败: {result['error']}"
            data = result.get("data", [])
            if not data:
                return "没有找到相关日报记录。"
            lines = [f"共 {len(data)} 条日报："]
            for i, row in enumerate(data[:10], 1):
                lines.append(f"  {i}. [{row.get('report_date', '')}] {str(row.get('content', ''))[:80]}...")
            return "\n".join(lines)
        except Exception as e:
            return f"查询出错: {e}"

    def _handle_data_query(self, user_input: str, entities: dict, db) -> str:
        """NL2SQL 通用数据查询"""
        if not db:
            return (
                "数据库连接不可用。\n"
                "你可以尝试以下查询：\n"
                "  • '查询所有新加坡意向的客户'\n"
                "  • '查询学生张三的成绩'\n"
                "  • '查询待审批的请假申请'\n"
                "  • '查询本周的日报'"
            )
        try:
            result = self.nl2sql.query(db, user_input)
            if "error" in result:
                return f"查询失败: {result['error']}\n请尝试更具体的描述。"

            data = result.get("data", [])
            sql = result.get("sql", "")
            explanation = result.get("explanation", "")

            lines = [f"{explanation}\n执行SQL: `{sql}`\n"]
            if not data:
                lines.append("查询结果为空。")
            else:
                lines.append(f"共 {len(data)} 条记录：")
                for i, row in enumerate(data[:15], 1):
                    values = ", ".join(f"{k}={v}" for k, v in list(row.items())[:5])
                    lines.append(f"  {i}. {values}")
                if len(data) > 15:
                    lines.append(f"  ... 还有 {len(data) - 15} 条")
            return "\n".join(lines)
        except Exception as e:
            return f"查询出错: {e}"

    def _handle_company_guide(self, user_input: str, entities: dict, db) -> str:
        """公司新人指南 RAG 问答"""
        context = self.rag.retrieve_context(f"公司 入职 制度 办公 部门 {user_input}")
        if context:
            prompt = GUIDE_PROMPT.format(context=context, user_input=user_input)
            return self.llm.chat(prompt, user_input)
        return (
            "关于公司制度方面的问题，建议你：\n"
            "1. 查看公司新人指南文档\n"
            "2. 联系HR部门获取最新制度文件\n"
            "3. 直接询问你的直属上级\n\n"
            "如果你有具体问题，我也可以帮你查询~"
        )

    def _handle_approval(self, user_input: str, entities: dict, db) -> str:
        """审批辅助"""
        info = self.llm.extract_info(
            user_input,
            ["审批类型", "申请编号", "审批决定", "审批意见"]
        )
        return (
            f"审批操作指引：\n"
            f"  类型: {info.get('审批类型', '未知')}\n"
            f"  编号: {info.get('申请编号', '未知')}\n"
            f"  决定: {info.get('审批决定', '未指定')}\n\n"
            f"审批操作请通过对应的API接口完成：\n"
            f"  • 请假审批: PUT /api/student/leave/{{id}}/approve\n"
            f"  • 投诉处理: PUT /api/student/feedback/{{id}}/resolve"
        )

    def _handle_dashboard(self, user_input: str, entities: dict, db) -> str:
        """仪表盘概览"""
        if not db:
            return "数据库连接不可用"
        try:
            from crud import DashboardCRUD
            stats = DashboardCRUD.get_stats(db)
            return (
                "📊 粤教服务数据概览\n"
                f"  • 意向客户总数: {stats.get('lead_total', 0)}\n"
                f"  • 本月新增客户: {stats.get('lead_new_this_month', 0)}\n"
                f"  • 在册学生数: {stats.get('student_total', 0)}\n"
                f"  • 进行中活动: {stats.get('active_events', 0)}\n"
                f"  • 待处理工单: {stats.get('pending_tickets', 0)}\n"
                f"  • 待审批请假: {stats.get('pending_leaves', 0)}\n"
                f"  • 高危预警: {stats.get('high_risk_alerts', 0)}"
            )
        except Exception as e:
            return f"获取仪表盘数据失败: {e}"

    def _handle_chitchat(self, user_input: str, entities: dict, db) -> str:
        """日常闲聊"""
        prompt = "你是粤教服务的企业助手，用轻松专业的语气和同事聊天。回复控制在2-3句话。"
        return self.llm.chat(prompt, user_input)

    # ==================== 便捷入口 ====================

    def chat(self, user_input: str, db=None) -> str:
        """单次对话"""
        result = self.route_intent(user_input, db)
        return result["response"]

    def voice_to_report(self, oral_text: str) -> dict:
        """口述文本 → 结构化日报"""
        return self.voice.text_to_report(oral_text)

    def query_database(self, question: str, db) -> dict:
        """自然语言查询数据库"""
        return self.nl2sql.query(db, question)
