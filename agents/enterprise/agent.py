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
        # 短输入预检：≤3字且无明确业务关键词 → 直接闲聊
        biz_keywords = ['客户', '查询', '日报', '审批', '仪表盘', '制度', '数据', '请假', '成绩',
                        '录入', '更新', '修改', '统计', '报告', '架构', '部门', '员工', '项目']
        stripped = user_input.strip()
        if len(stripped) <= 3 and not any(kw in stripped for kw in biz_keywords):
            return {"intent": "chitchat", "response": self._handle_chitchat(stripped, {}, db), "confidence": 0.95}

        result = self.llm.classify_intent(user_input, INTENT_DESCRIPTIONS)
        intent = result.get("intent", "chitchat")

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

        handler = handlers.get(intent, self._handle_chitchat)
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
        try:
            result = self.llm.chat(prompt, user_input)
            if result.startswith("[LLM"):
                return self._local_chitchat(user_input)
            return result
        except Exception:
            return self._local_chitchat(user_input)

    def _local_chitchat(self, user_input: str) -> str:
        """本地闲聊 fallback（LLM不可用时）"""
        # 精确匹配问候语
        greetings = {
            '你好': '你好！我是粤教服务的企业助手，有什么可以帮你的吗？',
            'hi': 'Hi！有什么需要帮忙的吗？',
            '嗨': '嗨！有什么可以帮你的？',
            '早上好': '早上好！新的一天开始了，有什么需要协助的？',
            '晚上好': '晚上好！还在加班吗？辛苦了~',
            '谢谢': '不客气！随时为你效劳~',
            '再见': '再见！祝你工作顺利！',
            '你是谁': '我是粤教服务的企业智能助手，可以帮你管理CRM客户、整理日报、查询数据、处理审批等。有什么需要尽管问我！',
            '你叫什么': '我叫"小粤企"，是粤教服务的企业智能助手，很高兴认识你！',
            '你能做什么': '我可以帮你：\n• 录入/查询/更新意向客户\n• 整理口述日报\n• 自然语言查询数据库\n• 查看仪表盘数据\n• 新人入职指引\n• 审批辅助\n有什么想试试的吗？',
            '在吗': '在的！有什么可以帮你的？',
        }
        for kw, reply in greetings.items():
            if kw in user_input:
                return reply

        # 话题匹配
        topics = {
            '天气': '天气这个话题确实让人关心~ 不过我更擅长帮你处理工作事务，比如CRM管理、日报整理、数据查询等。有工作上的需要吗？',
            '吃饭': '说到吃饭，工作再忙也要按时吃饭哦！需要我帮你快速处理一些工作事务吗？',
            '周末': '周末是放松的好时光！需要我在你休息前帮你整理一下本周的工作数据吗？',
            '旅游': '旅游是个让人开心的话题！不过在工作时间里，有什么CRM客户或数据查询需要我帮忙的吗？',
            '电影': '看来你心情不错~ 工作之余放松一下挺好。有什么工作上的事情需要我协助吗？',
            '音乐': '好品味！音乐能提升工作效率。需要我帮你处理一些日常工作事务吗？',
            '游戏': '游戏是很好的放松方式~ 不过别忘了工作哦！需要我帮你快速完成一些任务吗？',
            '运动': '保持运动习惯很棒！精力充沛才能高效工作。有什么需要我帮忙的吗？',
            '股票': '投资理财是门学问~ 不过我的专长在企业办公协助上，有CRM或数据方面的问题可以问我。',
            '新闻': '世界变化很快~ 不过我更关注你的工作需求。需要我帮你查询什么数据吗？',
            '无聊': '哈哈，无聊的时候可以试试我的功能：查客户、写日报、看仪表盘，说不定会发现有趣的数据！',
            '笑话': '我这里没有笑话库，但我可以帮你查询数据库，看看有没有有趣的客户记录？',
            '故事': '我更擅长讲故事——用数据讲故事！想看看仪表盘数据或者客户分析吗？',
        }
        for kw, reply in topics.items():
            if kw in user_input:
                return reply

        # 问句 → 引导到功能
        if user_input.endswith('?') or user_input.endswith('？') or user_input.endswith('吗'):
            return f"关于「{user_input}」，我主要擅长企业办公协助。你可以试试：\n• 查询所有意向客户\n• 查看仪表盘\n• 帮我写日报\n需要哪方面的帮助？"

        return f"闲聊时间~ 不过说到正事，我可以帮你管理CRM客户、整理日报、查询数据。有什么工作上的需要吗？"

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
