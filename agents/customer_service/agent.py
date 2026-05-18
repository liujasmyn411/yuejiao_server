"""
客服Agent - 对外智能客服
支持 8 种意图识别与路由
"""
import json
import logging

from agents.customer_service.prompts import (
    SYSTEM_PROMPT, INTENT_DESCRIPTIONS, CHITCHAT_PROMPT
)
from knowledge_base.vectorizer import get_rag_engine
from utils.llm_client import get_llm_client
from utils.conversation_state import (
    get_conversation_state_manager, SlotState
)
from crud.customer_crud import EventCRUD
from config import settings

logger = logging.getLogger("yuejiao.customer_service")


class CustomerServiceAgent:
    """粤教服务智能客服"""

    def __init__(self):
        self.llm = get_llm_client()
        self.rag = get_rag_engine()
        self.name = "客服Agent"

    # ==================== 意图路由 ====================

    def route_intent(self, user_input: str, student_id: int = None, db=None,
                      session_id: str = None, user_id: int = None) -> dict:
        """识别意图并路由到对应处理器"""
        result = self.llm.classify_intent(user_input, INTENT_DESCRIPTIONS)
        intent = result.get("intent", "faq")

        handlers = {
            "company_info": self._handle_company_info,
            "business_query": self._handle_business_query,
            "policy_query": self._handle_policy_query,
            "project_recommend": self._handle_project_recommend,
            "event_registration": self._handle_event_registration,
            "faq": self._handle_faq,
            "profile_match": self._handle_profile_match,
            "feedback": self._handle_feedback,
            "chitchat": self._handle_chitchat,
        }

        handler = handlers.get(intent, self._handle_faq)
        extra_kw = {}
        if intent == "event_registration":
            extra_kw = {"session_id": session_id, "user_id": user_id}
        response = handler(user_input, result.get("entities", {}), student_id, db, **extra_kw)
        return {"intent": intent, "response": response, "confidence": result.get("confidence", 0.5)}

    # ==================== 意图处理器 ====================

    def _handle_company_info(self, user_input: str, entities: dict, student_id: int = None, db=None) -> str:
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

    def _handle_business_query(self, user_input: str, entities: dict, student_id: int = None, db=None) -> str:
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

    def _handle_policy_query(self, user_input: str, entities: dict, student_id: int = None, db=None) -> str:
        """政策查询"""
        context = self.rag.retrieve_context(f"签证 政策 入学 费用 留学 {user_input}")
        if context:
            prompt = f"{SYSTEM_PROMPT}\n\n参考以下政策资料：\n{context}\n\n用户问题：{user_input}\n回答时注明政策可能随时变化，建议以官方最新信息为准。"
            return self.llm.chat(prompt, user_input)
        return (
            "关于留学政策方面的问题，建议你提供具体的国家和项目，我可以更精准地帮你查询~\n"
            "目前我们主要支持新加坡和德国的留学政策咨询。你关注的是哪个国家呢？"
        )

    def _handle_project_recommend(self, user_input: str, entities: dict, student_id: int = None, db=None) -> str:
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

    def _handle_event_registration(self, user_input: str, entities: dict, student_id: int = None,
                                     db=None, session_id: str = None, user_id: int = None) -> str:
        """活动报名引导 —— 查询数据库返回真实活动列表，并保存状态等待用户选择"""
        if db is None:
            return "活动功能暂不可用，请稍后再试或联系客服~"

        all_events = EventCRUD.get_all(db)
        events = [e for e in all_events if e.event_status not in ("已结束", "已取消")]
        if not events:
            return "目前暂无进行中的活动，请留意后续通知~\n你可以访问官网活动板块获取最新动态。"

        lines = ["近期有以下活动可以报名哦~\n"]
        for i, e in enumerate(events, 1):
            event_type = e.event_type or "待定"
            start_time = e.start_time.strftime("%m月%d日 %H:%M") if e.start_time else "待定"
            location = e.location or "待定"
            end_time = e.registration_end_time.strftime("%m月%d日 %H:%M") if e.registration_end_time else "待定"
            current = e.current_participants or 0
            total = e.max_participants or "不限"
            lines.append(
                f"{i}. 【{event_type}】{e.event_name}\n"
                f"   时间：{start_time}\n"
                f"   地点：{location}\n"
                f"   报名截止：{end_time} | 已报名：{current}/{total}"
            )
        lines.append(f"\n共 {len(events)} 场活动，回复活动编号（如「1」）即可报名~")

        # 保存会话状态，使用与 chat_routes 一致的 key（student_id + user_id + session_id）
        stm = get_conversation_state_manager()
        state = stm.start(
            intent="event_registration",
            table_name="event_registration",
            agent_type="customer",
            student_id=student_id,
            user_id=user_id,
            session_id=session_id,
        )
        state.extra["_event_ids"] = [e.id for e in events]
        state.extra["_event_names"] = {str(i): e.event_name for i, e in enumerate(events, 1)}
        stm.update(state, student_id=student_id, user_id=user_id, session_id=session_id)

        return "\n".join(lines)

    def handle_event_selection(self, user_input: str, state: "SlotState",
                                student_id: int = None, user_id: int = None,
                                session_id: str = None, db=None) -> dict:
        """处理活动编号选择 —— 多轮对话：选择活动 → 收集信息 → 确认 → 报名"""
        stm = get_conversation_state_manager()
        stripped = user_input.strip()

        # 所有 stm 操作使用一致的 key
        def _clear():
            stm.clear(student_id=student_id, user_id=user_id, session_id=session_id)

        def _update(s):
            stm.update(s, student_id=student_id, user_id=user_id, session_id=session_id)

        # 取消检测
        if SlotState.is_cancel(stripped):
            _clear()
            return {
                "intent": "event_registration",
                "response": "好的，已取消活动报名。如有需要随时找我~",
                "confidence": 0.95,
            }

        event_ids = state.extra.get("_event_ids", [])
        event_names = state.extra.get("_event_names", {})

        # 阶段1：还没选活动 → 尝试从输入中解析编号（支持「1」、【1】、[1] 等）
        if "event_id" not in state.collected:
            import re
            idx = None
            patterns = [
                r"[「【\[\(\"'（(](\d+)[」】\]\"'）)]",
                r"^第?(\d+)[个号位]?[。.]?$",
                r"^(\d+)$",
            ]
            for p in patterns:
                m = re.search(p, stripped)
                if m:
                    idx = int(m.group(1))
                    break

            if idx is None:
                _clear()
                return {
                    "intent": "chitchat",
                    "response": "请回复活动编号（如「1」「2」）来选择活动哦~ 输入「取消」可退出报名。",
                    "confidence": 0.8,
                }

            if idx < 1 or idx > len(event_ids):
                _clear()
                return {
                    "intent": "event_registration",
                    "response": f"活动编号 {idx} 不存在，请输入 1-{len(event_ids)} 之间的编号~ 输入「取消」可退出报名。",
                    "confidence": 0.9,
                }

            event_id = event_ids[idx - 1]
            event_name = event_names.get(str(idx), "")

            # 选中活动后立即检查是否已满
            if db and EventCRUD.is_full(db, event_id):
                _clear()
                return {
                    "intent": "event_registration",
                    "response": f"抱歉，「{event_name}」已满员，请选择其他活动或关注后续安排~",
                    "confidence": 0.9,
                }

            state.collect("event_id", event_id)
            state.collected["_event_name"] = event_name
            state.collected["_event_index"] = idx

            # 已登录学生：自动填入姓名
            if student_id and db:
                from model import SysUser
                user = db.query(SysUser).filter(SysUser.id == student_id).first()
                if user:
                    state.collect("customer_name", user.real_name or user.username)
                    state.collect("contact", user.contact_info or user.email or "")

            if state.is_complete():
                state.phase = "confirming"
                _update(state)
                return {
                    "intent": "event_registration",
                    "response": (
                        f"你选择了「{event_name}」\n\n"
                        f"请确认报名信息：\n"
                        f"  姓名：{state.collected.get('customer_name', '（未填）')}\n"
                        f"  联系方式：{state.collected.get('contact', '（未填）')}\n\n"
                        f"回复「确认」提交报名，或回复「取消」退出~"
                    ),
                    "confidence": 0.9,
                }

            _update(state)
            next_field = state.next_missing_display()
            return {
                "intent": "event_registration",
                "response": (
                    f"你选择了「{event_name}」～\n"
                    f"报名需要提供你的「{next_field}」，请告诉我~"
                ),
                "confidence": 0.9,
            }

        # 阶段2：收集信息（姓名/联系方式）
        if state.phase == "collecting":
            info = self.llm.extract_info(
                stripped, ["姓名", "联系方式"]
            )
            name = info.get("姓名", "") or stripped
            contact = info.get("联系方式", "")

            if "customer_name" in state.missing and name.strip():
                state.collect("customer_name", name.strip()[:30])
            if "contact" in state.missing and contact and contact.strip():
                state.collect("contact", contact.strip()[:20])

            if state.is_complete():
                state.phase = "confirming"
                _update(state)
                return {
                    "intent": "event_registration",
                    "response": (
                        f"请确认报名信息：\n\n"
                        f"  活动：{state.collected.get('_event_name', '')}\n"
                        f"  姓名：{state.collected.get('customer_name', '')}\n"
                        f"  联系方式：{state.collected.get('contact', '')}\n\n"
                        f"回复「确认」提交报名，回复「取消」退出，或继续补充信息~"
                    ),
                    "confidence": 0.9,
                }

            _update(state)
            return {
                "intent": "event_registration",
                "response": f"收到，还需要「{state.next_missing_display()}」，请提供~",
                "confidence": 0.85,
            }

        # 阶段3：确认 → 写入数据库
        if state.phase == "confirming":
            if SlotState.is_confirm(stripped):
                event_id = state.collected["event_id"]
                contact = state.collected.get("contact", "")

                if db:
                    # 1. 满员二次检查
                    if EventCRUD.is_full(db, event_id):
                        _clear()
                        return {
                            "intent": "event_registration",
                            "response": f"抱歉，「{state.collected.get('_event_name', '')}」刚满员了，报名失败。请关注其他活动~",
                            "confidence": 0.95,
                        }

                    # 2. 重复报名检查
                    if EventCRUD.check_duplicate(db, event_id, contact):
                        _clear()
                        return {
                            "intent": "event_registration",
                            "response": "你已经报名过该活动啦，无需重复报名~",
                            "confidence": 0.95,
                        }

                # 3. 确定 customer_id：已登录用户直接用 ID，游客自动创建 CRM 意向客户
                customer_id = student_id or user_id
                if not customer_id and db:
                    try:
                        from crud.enterprise_crud import CrmCRUD
                        lead = CrmCRUD.create(
                            db,
                            customer_name=state.collected.get("customer_name", "游客"),
                            contact_info=contact,
                            source_channel="活动报名-游客",
                            status="新增意向",
                            owner_employee_id=settings.default_crm_owner_id,
                        )
                        db.flush()
                        customer_id = lead.id
                    except Exception as e:
                        logger.error("创建游客CRM意向客户失败: %s", e)
                        _clear()
                        return {
                            "intent": "event_registration",
                            "response": "报名失败：系统暂无法处理游客报名，请稍后重试或联系客服~",
                            "confidence": 0.9,
                        }

                _clear()
                if db:
                    try:
                        registration = EventCRUD.register(
                            db,
                            event_id=event_id,
                            customer_id=customer_id,
                            customer_name=state.collected.get("customer_name", "游客"),
                            contact=contact,
                        )
                        db.commit()
                        event_name = state.collected.get("_event_name", "")
                        return {
                            "intent": "event_registration",
                            "response": (
                                f"报名成功！🎉\n"
                                f"你已成功报名「{event_name}」\n"
                                f"报名编号：{registration.id}\n"
                                f"活动开始前我们会通过你提供的联系方式通知你~"
                            ),
                            "confidence": 0.95,
                        }
                    except Exception as e:
                        logger.error("活动报名失败: %s", e)
                        return {
                            "intent": "event_registration",
                            "response": f"报名失败: {e}，请稍后重试或联系客服~",
                            "confidence": 0.9,
                        }
                return {
                    "intent": "event_registration",
                    "response": "报名接口暂不可用，请稍后重试或联系客服~",
                    "confidence": 0.8,
                }

            # 不是确认 → 当成补充信息
            info = self.llm.extract_info(stripped, ["姓名", "联系方式"])
            name = info.get("姓名", "") or stripped
            contact = info.get("联系方式", "")
            if name.strip():
                state.collect("customer_name", name.strip()[:30])
            if contact and contact.strip():
                state.collect("contact", contact.strip()[:20])
            state.phase = "confirming"
            _update(state)
            return {
                "intent": "event_registration",
                "response": (
                    f"已更新。请再次确认：\n\n"
                    f"  活动：{state.collected.get('_event_name', '')}\n"
                    f"  姓名：{state.collected.get('customer_name', '')}\n"
                    f"  联系方式：{state.collected.get('contact', '')}\n\n"
                    f"回复「确认」提交报名~"
                ),
                "confidence": 0.9,
            }

        _clear()
        return {
            "intent": "chitchat",
            "response": "报名流程已中断，有什么可以帮你的？",
            "confidence": 0.8,
        }

    def _handle_faq(self, user_input: str, entities: dict, student_id: int = None, db=None) -> str:
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

    def _handle_profile_match(self, user_input: str, entities: dict, student_id: int = None, db=None) -> str:
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

    def _handle_chitchat(self, user_input: str, entities: dict, student_id: int = None, db=None) -> str:
        """日常闲聊"""
        try:
            result = self.llm.chat(CHITCHAT_PROMPT, user_input)
            if result.startswith("[LLM"):
                return self._local_chitchat(user_input)
            return result
        except Exception:
            logger.warning("LLM闲聊失败，使用本地fallback")
            return self._local_chitchat(user_input)

    def _handle_feedback(self, user_input: str, entities: dict, student_id: int = None, db=None) -> str:
        """售后反馈 —— 投诉/建议提交（槽位填充：收集所有必填字段后再写入）"""
        stm = get_conversation_state_manager()

        # 第四层：区分「查询投诉进度/记录」和「发起新投诉」
        QUERY_COMPLAINT_KW = [
            "查询投诉", "投诉进度", "投诉状态", "投诉处理", "投诉记录",
            "工单进度", "工单状态", "我的投诉", "我的反馈",
            "反馈进度", "反馈状态", "反馈记录",
        ]
        if any(kw in user_input for kw in QUERY_COMPLAINT_KW):
            if db and student_id:
                try:
                    from crud import FeedbackCRUD
                    tickets = FeedbackCRUD.get_all(db, student_id=student_id)
                    if not tickets:
                        return "你目前没有提交过投诉或反馈工单。"
                    lines = ["📋 你的投诉/反馈记录："]
                    for t in tickets:
                        status_icon = {"待处理": "⏳", "已处理": "✅"}.get(t.status, "")
                        lines.append(
                            f"  {status_icon} [#{t.id}] {t.content[:40]}\n"
                            f"     类型: {t.feedback_type or '投诉'} | 状态: {t.status}"
                        )
                    return "\n".join(lines)
                except Exception as e:
                    logger.error("查询投诉记录失败 (student_id=%s): %s", student_id, e)
                    return f"查询投诉记录失败: {e}"
            return "未能查询投诉记录，请确认已登录后重试。"

        # 1. 从用户输入提取已提供的信息
        info = self.llm.extract_info(
            user_input,
            ["反馈类型", "涉及人员", "详细描述", "期望解决方案"]
        )
        extracted_content = info.get("详细描述", "") or user_input[:200]

        # 2. 判断反馈内容是否充分
        has_content = bool(extracted_content.strip()) and len(extracted_content) > 3
        if not has_content:
            context = {"student_id": student_id} if student_id else {}
            state = stm.start(
                intent="feedback",
                table_name="student_feedback_ticket",
                agent_type="customer",
                student_id=student_id,
                context=context,
            )
            for field_name, value in info.items():
                if value and field_name in state.required_fields:
                    state.collect(field_name, value)
                    if field_name in state.missing:
                        state.missing.remove(field_name)
            stm.update(state, student_id=student_id)
            return (
                f"收到，我来帮你提交反馈。\n"
                f"请详细描述你要投诉/反馈的具体内容，比如涉及哪些人员、发生了什么事、你希望怎么解决？\n"
                f"请一次性告诉我，我会整理后为你创建工单~"
            )

        # 3. 必填字段齐全 → 进入确认阶段（不直接写入）
        if has_content:
            stm = get_conversation_state_manager()
            context = {"student_id": student_id} if student_id else {}
            state = stm.start(
                intent="feedback",
                table_name="student_feedback_ticket",
                agent_type="customer",
                student_id=student_id,
                context=context,
            )
            state.collect("content", extracted_content[:200])
            for field_name, value in info.items():
                if value and field_name in state.missing:
                    state.collect(field_name, value)
            state.phase = "confirming"
            stm.update(state, student_id=student_id)

            return (
                f"📋 已识别到你的反馈信息：\n\n{state.summary()}\n\n"
                f"回复「确认」提交工单，回复「取消」放弃，或继续补充信息~"
            )

    # ==================== 槽位填充 ====================

    def continue_data_collection(self, user_input: str, state: SlotState,
                                 student_id: int = None, db=None) -> dict:
        """通用槽位填充 —— 支持取消 + 确认 + 重新编辑"""
        stm = get_conversation_state_manager()

        # ===== 第三层逃生：交互次数兜底 =====
        state.interaction_count += 1
        if state.interaction_count > SlotState.MAX_INTERACTIONS:
            stm.clear(student_id=student_id)
            return {
                "intent": "chitchat",
                "response": (
                    f"对话轮次较多，已自动结束之前的"
                    f"{'投诉工单' if state.intent == 'feedback' else '申请'}。"
                    f"请问还有什么可以帮你的？"
                ),
                "confidence": 0.8,
            }

        # ===== 取消检测 =====
        if SlotState.is_cancel(user_input):
            stm.clear(student_id=student_id)
            return {
                "intent": "feedback",
                "response": "好的，已取消当前操作。如有需要随时找我~",
                "confidence": 0.95,
            }

        # ===== 确认阶段 =====
        if state.phase == "confirming":
            if SlotState.is_confirm(user_input):
                stm.clear(student_id=student_id)
                if student_id and db:
                    try:
                        from crud import FeedbackCRUD
                        from schemas import FeedbackCreateRequest
                        req = FeedbackCreateRequest(
                            student_id=student_id,
                            content=state.collected.get("content", user_input[:200]),
                            detail=state.collected.get("content", user_input),
                            feedback_type="投诉",
                            urgency_level="中",
                        )
                        ticket = FeedbackCRUD.create(db, req)
                        db.commit()
                        return {
                            "intent": "feedback",
                            "response": f"📋 已为你创建工单 #{ticket.id}，我们会在24小时内响应~",
                            "confidence": 0.95,
                        }
                    except Exception as e:
                        logger.error("创建反馈工单失败 (student_id=%s): %s", student_id, e)
                        return {"intent": "feedback", "response": f"工单创建失败: {e}", "confidence": 0.9}
                return {
                    "intent": "feedback",
                    "response": "📋 信息已确认！提交接口: POST /api/student/feedback",
                    "confidence": 0.95,
                }

            stripped = user_input.strip()

            # 条件A：短输入 → 可能是另起话题
            if len(stripped) <= 5:
                state.confirm_retries += 1
                if state.confirm_retries >= 2:
                    stm.clear(student_id=student_id)
                    return {
                        "intent": "chitchat",
                        "response": "检测到你可能想换个话题。已取消当前操作，有什么可以帮你的？",
                        "confidence": 0.8,
                    }
                stm.update(state, student_id=student_id)
                return {
                    "intent": "feedback",
                    "response": "你有一个待确认的反馈工单。回复「确认」提交，「取消」放弃，或告诉我你想做什么~",
                    "confidence": 0.85,
                }

            # 条件B：话题切换关键词
            if any(kw in stripped for kw in SlotState.SWITCH_TOPIC_KW):
                stm.clear(student_id=student_id)
                return {
                    "intent": "chitchat",
                    "response": "好的，已取消当前操作。请重新描述你的需求，我来帮你处理~",
                    "confidence": 0.85,
                }

            # 条件C：状态已完整 → 不是补充，是另起话题
            # 条件D：状态不完整 → 当成补充信息
            if state.is_complete():
                stm.clear(student_id=student_id)
                return {
                    "intent": "chitchat",
                    "response": "好的，已取消当前操作。请重新描述你的需求，我来帮你处理~",
                    "confidence": 0.85,
                }
            state.confirm_retries = 0
            state.phase = "collecting"
            info = self.llm.extract_info(
                user_input, ["反馈类型", "涉及人员", "详细描述", "期望解决方案"]
            )
            extracted = info.get("详细描述", "") or user_input
            if extracted.strip() and len(extracted) > 3 and "content" in state.missing:
                state.collect("content", extracted[:200])
            if not state.is_complete():
                stm.update(state, student_id=student_id)
                return {
                    "intent": "feedback",
                    "response": f"收到补充。还需要「{state.next_missing_display()}」，请描述~",
                    "confidence": 0.85,
                }
            state.phase = "confirming"
            stm.update(state, student_id=student_id)
            return {
                "intent": "feedback",
                "response": f"已更新，请确认：\n\n{state.summary()}\n\n回复「确认」提交或继续补充~",
                "confidence": 0.9,
            }

        # ===== 收集阶段 =====
        # 第一层逃生：话题切换关键词检测
        stripped = user_input.strip()
        if any(kw in stripped for kw in SlotState.SWITCH_TOPIC_KW):
            stm.clear(student_id=student_id)
            return {
                "intent": "chitchat",
                "response": "好的，已取消当前操作。请重新描述你的需求，我来帮你处理~",
                "confidence": 0.85,
            }

        info = self.llm.extract_info(
            user_input, ["反馈类型", "涉及人员", "详细描述", "期望解决方案"]
        )
        extracted_content = info.get("详细描述", "") or user_input
        if "content" in state.missing and extracted_content.strip() and len(extracted_content) > 3:
            state.collect("content", extracted_content[:200])

        if state.is_complete():
            state.phase = "confirming"
            stm.update(state, student_id=student_id)
            return {
                "intent": "feedback",
                "response": (
                    f"信息已收集完整，请确认：\n\n{state.summary()}\n\n"
                    f"回复「确认」提交，回复「取消」放弃，或继续补充~"
                ),
                "confidence": 0.9,
            }

        stm.update(state, student_id=student_id)
        return {
            "intent": "feedback",
            "response": f"收到，还需要补充「{state.next_missing_display()}」，请描述一下~",
            "confidence": 0.85,
        }

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

    def chat(self, user_input: str, student_id: int = None, db=None) -> str:
        """单次对话，返回回复文本"""
        result = self.route_intent(user_input, student_id, db)
        return result["response"]
