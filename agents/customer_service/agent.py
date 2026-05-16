"""
客服Agent - 对外智能客服
支持 8 种意图识别与路由
"""
import json
from agents.customer_service.prompts import (
    SYSTEM_PROMPT, INTENT_DESCRIPTIONS, CHITCHAT_PROMPT
)
from knowledge_base.vectorizer import get_rag_engine
from utils.llm_client import get_llm_client


class CustomerServiceAgent:
    """粤教服务智能客服"""

    def __init__(self):
        self.llm = get_llm_client()
        self.rag = get_rag_engine()
        self.name = "客服Agent"

    # ==================== 意图路由 ====================

    def route_intent(self, user_input: str) -> dict:
        """识别意图并路由到对应处理器"""
        # 先用 LLM 做意图分类
        result = self.llm.classify_intent(user_input, INTENT_DESCRIPTIONS)
        intent = result.get("intent", "faq")

        # 路由到处理器
        handlers = {
            "company_info": self._handle_company_info,
            "business_query": self._handle_business_query,
            "policy_query": self._handle_policy_query,
            "project_recommend": self._handle_project_recommend,
            "event_registration": self._handle_event_registration,
            "faq": self._handle_faq,
            "profile_match": self._handle_profile_match,
            "chitchat": self._handle_chitchat,
        }

        handler = handlers.get(intent, self._handle_faq)
        response = handler(user_input, result.get("entities", {}))
        return {"intent": intent, "response": response, "confidence": result.get("confidence", 0.5)}

    # ==================== 意图处理器 ====================

    def _handle_company_info(self, user_input: str, entities: dict) -> str:
        """公司信息咨询"""
        context = self.rag.retrieve_context(f"粤教服务 公司 介绍 联系方式 {user_input}")
        if context:
            prompt = f"{SYSTEM_PROMPT}\n\n参考以下资料回答用户问题：\n{context}\n\n用户问题：{user_input}"
            return self.llm.chat(prompt, user_input)
        return (
            "粤教服务（广东省教育服务有限公司）成立于1981年，是省属国有教育服务企业。\n"
            "核心业务涵盖国际教育、智慧教育、素质教育等板块，主打新加坡国际本硕升学计划和中德精英人才共建计划。\n"
            "如需了解更多，可以访问官网或拨打咨询热线~"
        )

    def _handle_business_query(self, user_input: str, entities: dict) -> str:
        """业务/项目查询"""
        context = self.rag.retrieve_context(f"留学 项目 课程 新加坡 德国 {user_input}")
        if context:
            prompt = f"{SYSTEM_PROMPT}\n\n参考以下项目资料：\n{context}\n\n用户问题：{user_input}\n请详细介绍相关项目信息。"
            return self.llm.chat(prompt, user_input)
        return (
            "我们目前主打两大项目哦~\n"
            "1. 新加坡国际本硕升学计划：2+2本科班、0.5/1+2本科班、酒店/航空大专就业班\n"
            "2. 中德精英人才共建计划：德国双元制职业教育，免学费享补贴\n"
            "你对哪个项目比较感兴趣？我可以详细给你介绍~"
        )

    def _handle_policy_query(self, user_input: str, entities: dict) -> str:
        """政策查询"""
        context = self.rag.retrieve_context(f"签证 政策 入学 费用 留学 {user_input}")
        if context:
            prompt = f"{SYSTEM_PROMPT}\n\n参考以下政策资料：\n{context}\n\n用户问题：{user_input}\n回答时注明政策可能随时变化，建议以官方最新信息为准。"
            return self.llm.chat(prompt, user_input)
        return (
            "关于留学政策方面的问题，建议你提供具体的国家和项目，我可以更精准地帮你查询~\n"
            "目前我们主要支持新加坡和德国的留学政策咨询。你关注的是哪个国家呢？"
        )

    def _handle_project_recommend(self, user_input: str, entities: dict) -> str:
        """项目推荐"""
        # 提取用户信息
        info = self.llm.extract_info(user_input, ["年龄", "学历", "意向国家", "预算"])
        context = self.rag.retrieve_context(
            f"留学 项目 {info.get('意向国家', '')} {info.get('学历', '')} {info.get('年龄', '')}"
        )
        prompt = f"""{SYSTEM_PROMPT}

用户画像：{json.dumps(info, ensure_ascii=False)}
参考项目：{context}

请根据用户画像推荐最匹配的留学项目，说明推荐理由，并引导用户进一步咨询。"""
        return self.llm.chat(prompt, user_input)

    def _handle_event_registration(self, user_input: str, entities: dict) -> str:
        """活动报名引导"""
        return (
            "我们定期会举办留学分享会和政策解读讲座哦~\n"
            "你可以通过以下方式查看和报名活动：\n"
            "1. 访问官网活动板块\n"
            "2. 回复「活动」查看近期的活动列表\n"
            "3. 直接告诉我你想参加什么类型的活动，我帮你查~"
        )

    def _handle_faq(self, user_input: str, entities: dict) -> str:
        """FAQ 检索"""
        context = self.rag.retrieve_context(user_input)
        if context and "FAQ" in context[:20]:
            # 精准匹配到了问答对
            lines = context.split("\n")
            answer_lines = [l for l in lines if l.startswith("A:")]
            if answer_lines:
                return answer_lines[0].replace("A:", "").strip()

        if context:
            prompt = f"{SYSTEM_PROMPT}\n\n参考资料：\n{context}\n\n用户问题：{user_input}\n请简洁回答。"
            return self.llm.chat(prompt, user_input)
        return (
            "抱歉，我暂时没有找到相关的答案。\n"
            "你可以换个方式提问，或者输入「人工」转接专业顾问为你解答~"
        )

    def _handle_profile_match(self, user_input: str, entities: dict) -> str:
        """客户画像研判"""
        info = self.llm.extract_info(
            user_input,
            ["姓名", "年龄", "学历", "意向国家", "语言水平", "家庭经济", "备注"]
        )
        prompt = f"""{SYSTEM_PROMPT}

用户信息：{json.dumps(info, ensure_ascii=False)}

请根据用户信息进行画像研判，格式如下：
- 匹配产品：推荐最合适的留学项目
- 匹配依据：说明理由
- 画像评分：预估意向分数（0-100）
- 建议跟进：下一步行动建议"""
        return self.llm.chat(prompt, user_input)

    def _handle_chitchat(self, user_input: str, entities: dict) -> str:
        """日常闲聊"""
        try:
            result = self.llm.chat(CHITCHAT_PROMPT, user_input)
            if result.startswith("[LLM"):
                return self._local_chitchat(user_input)
            return result
        except Exception:
            return self._local_chitchat(user_input)

    def _local_chitchat(self, user_input: str) -> str:
        greetings = {
            '你好': '您好！我是粤教服务的客服助手，很高兴为您服务。有什么关于留学、课程的问题都可以问我~',
            'hi': 'Hi！欢迎来到粤教服务，有什么可以帮您的吗？',
            '嗨': '嗨！有什么留学相关问题想了解的吗？',
            '早上好': '早上好！欢迎咨询粤教服务~',
            '谢谢': '不客气！如有其他问题随时找我~',
            '再见': '再见！祝您生活愉快！',
        }
        for kw, reply in greetings.items():
            if kw in user_input:
                return reply
        return f"收到您的消息~ 关于「{user_input}」，有什么具体想了解的吗？我们的留学项目、课程服务和活动讲座都可以咨询哦~"

    # ==================== 便捷入口 ====================

    def chat(self, user_input: str) -> str:
        """单次对话，返回回复文本"""
        result = self.route_intent(user_input)
        return result["response"]
