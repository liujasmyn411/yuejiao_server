"""
学生助手 Agent - 对内留学生全周期服务
支持 7 种意图：行政/心理/反馈/学业/进度/生活/增值转化
"""
import json
from agents.student.prompts import (
    SYSTEM_PROMPT, INTENT_DESCRIPTIONS, LIFE_SUPPORT_PROMPT, UPGRADE_PROMPT,
    NL2SQL_STUDENT_PROMPT,
)
from agents.student.psych_monitor import PsychMonitor
from agents.student.approval_flow import ApprovalFlow
from agents.enterprise.nl2sql import NL2SQL
from knowledge_base.vectorizer import get_rag_engine
from utils.llm_client import get_llm_client
from utils.conversation_state import (
    get_conversation_state_manager, SlotState
)
from utils.date_parser import normalize_datetime

STUDENT_TABLES = [
    "student_score", "student_admin_service", "student_feedback_ticket",
    "student_academic", "student_study_abroad_progress",
]


class StudentAgent:
    """粤教服务学生智能助手"""

    def __init__(self):
        self.llm = get_llm_client()
        self.rag = get_rag_engine()
        self.psych = PsychMonitor()
        self.approval = ApprovalFlow()
        self.nl2sql = NL2SQL(
            table_allowlist=STUDENT_TABLES,
            prompt_template=NL2SQL_STUDENT_PROMPT,
            update_whitelist={},
        )
        self.name = "学生助手Agent"

    # ==================== 意图路由 ====================

    def route_intent(self, user_input: str, student_id: int = None, db=None) -> dict:
        """识别意图并路由到对应处理器"""
        result = self.llm.classify_intent(user_input, INTENT_DESCRIPTIONS)
        intent = result.get("intent", "chitchat")

        handlers = {
            "admin_service": self._handle_admin_service,
            "psych_care": self._handle_psych_care,
            "feedback": self._handle_feedback,
            "academic_query": self._handle_academic_query,
            "progress_track": self._handle_progress_track,
            "life_support": self._handle_life_support,
            "upgrade_intent": self._handle_upgrade_intent,
            "data_query": self._handle_data_query,
            "chitchat": self._handle_chitchat,
        }

        handler = handlers.get(intent, self._handle_chitchat)
        response = handler(user_input, result.get("entities", {}), student_id, db)

        # 附加心理评估结果（非心理关怀意图也做轻量评估）
        psych_eval = None
        if intent != "psych_care":
            psych_eval = self.psych.evaluate(user_input)

        output = {"intent": intent, "response": response, "confidence": result.get("confidence", 0.5)}
        if psych_eval and self.psych.should_alert(psych_eval):
            output["psych_alert"] = psych_eval
        return output

    # ==================== 意图处理器 ====================

    def _handle_admin_service(self, user_input: str, entities: dict,
                              student_id: int, db) -> str:
        """行政服务 —— 请假申请/查询（槽位填充）"""
        # 查询审批状态
        QUERY_KW = ["查询", "状态", "进度", "审批", "通过", "查看", "看看",
                     "记录", "历史", "申请"]
        if any(w in user_input for w in QUERY_KW) and not any(
            w in user_input for w in ["请假", "申请", "提交", "想请"]
        ):
            # 如果已有 student_id → 直接查询（需要 db）
            if student_id:
                if db:
                    try:
                        from crud import StudentServiceCRUD
                        leaves = StudentServiceCRUD.get_leaves(db, student_id)
                        if not leaves:
                            return "你目前没有请假记录。"
                        lines = ["📋 你的请假记录："]
                        for l in leaves:
                            status_icon = {"待审批": "⏳", "已通过": "✅", "已驳回": "❌"}.get(l.status, "")
                            start = str(l.start_time)[:16] if l.start_time else "未知"
                            end = str(l.end_time)[:16] if l.end_time else "未知"
                            lines.append(
                                f"  {status_icon} [{l.leave_type}] {start} ~ {end}\n"
                                f"     原因: {l.reason or '无'} | 状态: {l.status}"
                            )
                        return "\n".join(lines)
                    except Exception as e:
                        return f"查询请假记录失败: {e}"
                else:
                    return (
                        "你可以通过以下方式查询审批状态：\n"
                        f"  • GET /api/student/leave?student_id={student_id}\n"
                        "  • 在浏览器中打开上述地址即可查看"
                    )

            # 没有 student_id → 启动查询会话，等用户提供 ID
            stm = get_conversation_state_manager()
            state = stm.start(
                intent="admin_query",
                table_name="",
                agent_type="student",
                student_id=student_id,
                context={},
            )
            state.required_fields = {"student_id": "学生ID"}
            state.missing = ["student_id"]
            stm.update(state, student_id=student_id)
            return (
                "我来帮你查询请假记录。请提供你的学生ID（直接发数字即可）~"
            )

        # 请假提交 → 槽位填充
        LEAVE_KW = ["请假", "申请", "提交", "想请", "生病", "不舒服", "感冒", "发烧",
                     "头疼", "肚子", "休息", "病假", "事假", "旷", "缺"]
        if any(w in user_input for w in LEAVE_KW):
            stm = get_conversation_state_manager()
            info = self.approval.extract_leave_info(user_input)
            context = {"student_id": student_id, "service_type": "请假"}

            # 判断用户是否提供了足够的请假信息
            has_leave_type = bool(info.get("leave_type"))
            has_start = bool(info.get("start_time"))
            has_end = bool(info.get("end_time"))
            has_reason = bool(info.get("reason")) and len(str(info.get("reason", ""))) > 2

            if has_leave_type and has_start and has_end and has_reason and student_id and db:
                # 信息齐全 → 进入确认阶段（不直接写入）
                stm = get_conversation_state_manager()
                context = {"student_id": student_id, "service_type": "请假"}
                state = stm.start(
                    intent="admin_service",
                    table_name="student_admin_service",
                    agent_type="student",
                    student_id=student_id,
                    context=context,
                )
                for field_name, value in info.items():
                    if value and field_name in state.missing:
                        state.collect(field_name, value)
                state.phase = "confirming"
                stm.update(state, student_id=student_id)

                return (
                    f"📝 请假信息已识别：\n\n{state.summary()}\n\n"
                    f"回复「确认」提交申请，回复「取消」放弃，或继续修改~"
                )

            # 信息不完整 → 启动槽位填充
            state = stm.start(
                intent="admin_service",
                table_name="student_admin_service",
                agent_type="student",
                student_id=student_id,
                context=context,
            )
            for field_name, value in info.items():
                if value and field_name in state.missing:
                    state.collect(field_name, value)
            stm.update(state, student_id=student_id)

            missing_parts = []
            if not has_leave_type:
                missing_parts.append("请假类型（病假/事假）")
            if not has_start:
                missing_parts.append("开始时间")
            if not has_end:
                missing_parts.append("结束时间")
            if not has_reason:
                missing_parts.append("请假原因")

            return (
                f"📝 我来帮你提交请假申请。还需要补充以下信息：\n"
                + "\n".join(f"  • {m}" for m in missing_parts)
                + f"\n\n已识别: {info.get('leave_type', '?')} | "
                  f"{info.get('start_time', '?')} ~ {info.get('end_time', '?')} | "
                  f"{info.get('reason', '?')}\n"
                f"请一次性告诉我缺少的信息~"
            )

        return "请问你是要提交请假申请，还是查询审批状态呢？"

    def _handle_psych_care(self, user_input: str, entities: dict,
                           student_id: int, db) -> str:
        """心理关怀 —— 情绪评估 + 温暖回复 + 预警"""
        evaluation = self.psych.evaluate(user_input)
        reply = self.psych.generate_reply(user_input, evaluation)

        # 触发预警
        if self.psych.should_alert(evaluation) and student_id:
            self._record_alert(student_id, evaluation, db)

        return reply

    # 投诉强信号词 —— 出现这些词才判定为"真投诉内容"
    STRONG_COMPLAINT_KW = [
        "投诉", "举报", "差劲", "太烂", "坑人", "骗", "退款", "赔偿",
        "态度恶劣", "不负责", "敷衍", "糊弄", "乱收费", "虚假", "劣质",
        "欺负", "霸凌", "歧视", "不公平", "抗议", "维权", "曝光",
    ]

    def _has_real_feedback_content(self, user_input: str, info: dict) -> bool:
        """判断用户输入是否包含真正的投诉/反馈内容（而非闲聊中含建议/反馈等词）"""
        # 条件1：LLM明确提取到了"详细描述"且长度≥8字
        detail = info.get("详细描述", "")
        if detail and len(detail.strip()) >= 8:
            return True
        # 条件2：包含投诉强信号词
        if any(kw in user_input for kw in self.STRONG_COMPLAINT_KW):
            return True
        # 条件3：整体输入较长（≥15字）且含负面语义
        if len(user_input) >= 15 and any(
            w in user_input for w in ["不满", "不好", "不行", "不对", "生气", "失望",
                                        "问题", "麻烦", "糟糕", "难受", "受不了"]
        ):
            return True
        return False

    def _handle_feedback(self, user_input: str, entities: dict,
                         student_id: int, db) -> str:
        """售后反馈 —— 投诉/建议提交（槽位填充：收集所有必填字段后再写入）"""
        stm = get_conversation_state_manager()

        # 0. 如果已有活跃的 feedback 状态 → 不要新建，交给 continue_data_collection
        existing = stm.get(student_id=student_id)
        if existing and existing.intent == "feedback":
            # 由 chat_routes 步骤0 路由到 continue_data_collection，
            # 但如果走到这里说明路由没生效，直接返回提示
            return "你有一个待确认的反馈工单，请先处理（回复「确认」或「取消」）~"

        # 1. 从用户输入提取已提供的信息
        info = self.llm.extract_info(
            user_input,
            ["反馈类型", "涉及人员", "详细描述", "期望解决方案"]
        )

        # 2. 判断是否为真投诉内容（Fix 1：提高门槛）
        context = {"student_id": student_id} if student_id else {}
        has_real_content = self._has_real_feedback_content(user_input, info)

        if not has_real_content:
            # 可能是闲聊混入了"建议""反馈"等词，或者只是"我要投诉"没有细节
            detail = info.get("详细描述", "")
            if detail and len(detail.strip()) >= 4:
                # LLM提取到了一点内容但不够充分 → 追问
                pass
            elif "投诉" in user_input or "反馈" in user_input or "建议" in user_input:
                # 用户确实表达了投诉意图但没给细节
                pass
            else:
                # 应该不是真的想投诉，直接走闲聊兜底
                return self._handle_chitchat(user_input, entities, student_id, db)

            # 用户表达了投诉意图但内容不充分 → 启动收集
            state = stm.start(
                intent="feedback",
                table_name="student_feedback_ticket",
                agent_type="student",
                student_id=student_id,
                context=context,
            )
            for field_name, value in info.items():
                if value and field_name in state.required_fields:
                    state.collect(field_name, value)
            stm.update(state, student_id=student_id)

            return (
                f"收到，我来帮你提交反馈。\n"
                f"请详细描述你要投诉/反馈的具体内容，比如：\n"
                f"  • 涉及哪些人员？\n"
                f"  • 发生了什么事情？\n"
                f"  • 你希望怎么解决？\n\n"
                f"请一次性告诉我，我会整理后为你创建工单~"
            )

        # 3. 真投诉内容 → 进入确认阶段
        extracted_content = info.get("详细描述", "") or user_input[:200]
        state = stm.start(
            intent="feedback",
            table_name="student_feedback_ticket",
            agent_type="student",
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

    def continue_data_collection(self, user_input: str, state: SlotState,
                                 student_id: int = None, db=None) -> dict:
        """通用槽位填充 —— 支持取消 + 确认 + 重新编辑 + 查询"""
        stm = get_conversation_state_manager()

        # ===== 查询类意图（无需插入，只查数据） =====
        if state.intent == "admin_query":
            if SlotState.is_cancel(user_input):
                stm.clear(student_id=student_id)
                return {"intent": "admin_query", "response": "好的，已取消查询。", "confidence": 0.95}

            # 尝试从输入中提取学生ID（纯数字）
            import re
            id_match = re.search(r'\b(\d+)\b', user_input)
            queried_id = int(id_match.group(1)) if id_match else None

            if not queried_id:
                stm.update(state, student_id=student_id)
                return {
                    "intent": "admin_query",
                    "response": "请提供一个有效的学生ID（纯数字），比如直接发「7」~",
                    "confidence": 0.85,
                }

            # 拿到了学生ID → 查询
            stm.clear(student_id=student_id)
            if db:
                try:
                    from crud import StudentServiceCRUD
                    leaves = StudentServiceCRUD.get_leaves(db, queried_id)
                    if not leaves:
                        return {
                            "intent": "admin_query",
                            "response": f"学生 {queried_id} 目前没有请假记录。",
                            "confidence": 0.9,
                        }
                    lines = [f"📋 学生 {queried_id} 的请假记录："]
                    for l in leaves:
                        status_icon = {"待审批": "⏳", "已通过": "✅", "已驳回": "❌"}.get(l.status, "")
                        start = str(l.start_time)[:16] if l.start_time else "未知"
                        end = str(l.end_time)[:16] if l.end_time else "未知"
                        lines.append(
                            f"  {status_icon} [{l.leave_type}] {start} ~ {end}\n"
                            f"     原因: {l.reason or '无'} | 状态: {l.status}"
                        )
                    return {"intent": "admin_query", "response": "\n".join(lines), "confidence": 0.9}
                except Exception as e:
                    return {"intent": "admin_query", "response": f"查询失败: {e}", "confidence": 0.9}
            return {
                "intent": "admin_query",
                "response": f"数据库不可用。可通过 GET /api/student/leave?student_id={queried_id} 查询。",
                "confidence": 0.9,
            }

        # ===== 取消检测（所有阶段） =====
        if SlotState.is_cancel(user_input):
            stm.clear(student_id=student_id)
            return {
                "intent": state.intent,
                "response": "好的，已取消当前操作。如有需要随时找我~",
                "confidence": 0.95,
            }

        # ===== 确认阶段 =====
        if state.phase == "confirming":
            if SlotState.is_confirm(user_input):
                stm.clear(student_id=student_id)
                return self._commit_collected(
                    state, user_input,
                    self._extract_for_intent(user_input, state.intent),
                    student_id, db
                )

            # 用户没说确认 → 判断是否想另起话题
            stripped = user_input.strip()

            # 条件A：输入很短（≤5字）且明显不是补充投诉内容 → 不是补充，是另起话题
            if len(stripped) <= 5:
                state.confirm_retries += 1
                if state.confirm_retries >= 2:
                    # 多次短输入 → 主动帮用户做选择
                    stm.clear(student_id=student_id)
                    return {
                        "intent": "chitchat",
                        "response": (
                            f"检测到你可能想换个话题。已取消之前的{'投诉' if state.intent == 'feedback' else ''}操作。\n"
                            f"有什么可以帮你的？"
                        ),
                        "confidence": 0.8,
                    }
                stm.update(state, student_id=student_id)
                return {
                    "intent": state.intent,
                    "response": (
                        f"你有一个待确认的{'投诉工单' if state.intent == 'feedback' else '申请'}。\n"
                        f"回复「确认」提交，「取消」放弃。\n"
                        f"或者告诉我你想做什么，我帮你处理~"
                    ),
                    "confidence": 0.85,
                }

            # 条件B：输入包含"切换话题"关键词 → 用户明显想干别的事
            if any(kw in stripped for kw in SlotState.SWITCH_TOPIC_KW):
                stm.clear(student_id=student_id)
                return {
                    "intent": "chitchat",
                    "response": (
                        f"好的，已取消当前操作。请重新描述你的需求，我来帮你处理~"
                    ),
                    "confidence": 0.85,
                }

            # 条件C：正常情况 → 当成补充信息
            state.confirm_retries = 0  # 确实在补充内容，重置计数
            state.phase = "collecting"
            info = self._extract_for_intent(user_input, state.intent)
            self._merge_collected(state, info, user_input)
            if not state.is_complete():
                stm.update(state, student_id=student_id)
                return {
                    "intent": state.intent,
                    "response": f"收到补充信息。还需要「{state.next_missing_display()}」，请描述一下~",
                    "confidence": 0.85,
                }
            state.phase = "confirming"
            stm.update(state, student_id=student_id)
            return {
                "intent": state.intent,
                "response": (
                    f"好的，已更新信息。请确认以下内容：\n\n{state.summary()}\n\n"
                    f"回复「确认」提交，或继续补充其他信息~"
                ),
                "confidence": 0.9,
            }

        # ===== 收集阶段 =====
        info = self._extract_for_intent(user_input, state.intent)
        self._merge_collected(state, info, user_input)

        if state.is_complete():
            # 收集完整 → 进入确认阶段
            state.phase = "confirming"
            stm.update(state, student_id=student_id)
            return {
                "intent": state.intent,
                "response": (
                    f"信息已收集完整，请确认以下内容：\n\n{state.summary()}\n\n"
                    f"回复「确认」提交，回复「取消」放弃，或继续补充信息~"
                ),
                "confidence": 0.9,
            }

        # 还有缺失 → 继续追问
        stm.update(state, student_id=student_id)
        return {
            "intent": state.intent,
            "response": (
                f"收到，已记录你提供的信息。\n"
                f"还需要补充「{state.next_missing_display()}」，请描述一下~"
            ),
            "confidence": 0.85,
        }

    def _extract_for_intent(self, user_input: str, intent: str) -> dict:
        """根据意图提取对应的结构化信息"""
        extractors = {
            "feedback": ["反馈类型", "涉及人员", "详细描述", "期望解决方案"],
            "admin_service": ["leave_type", "start_time", "end_time", "reason"],
        }
        fields = extractors.get(intent, ["content"])
        return self.llm.extract_info(user_input, fields)

    def _merge_collected(self, state: SlotState, info: dict, user_input: str) -> None:
        """将提取到的信息合并到槽位状态中"""
        # 通用 content 字段
        if "content" in state.missing:
            extracted = info.get("详细描述", "") or info.get("reason", "") or user_input
            if extracted.strip() and len(extracted) > 3:
                state.collect("content", extracted[:200])

        # 请假相关字段（自动解析相对日期）
        for f in ["leave_type", "reason", "service_type"]:
            if f in state.missing and info.get(f):
                state.collect(f, info[f])
        for f in ["start_time", "end_time"]:
            if f in state.missing and info.get(f):
                val = info[f]
                if isinstance(val, str):
                    normalized = normalize_datetime(val)
                    state.collect(f, normalized if normalized else val)
                else:
                    state.collect(f, val)

        # 其他提取到的字段
        for field_name, value in info.items():
            if value and field_name in state.missing:
                state.collect(field_name, value)

    def _commit_collected(self, state: SlotState, user_input: str,
                          info: dict, student_id: int, db) -> dict:
        """所有必填字段收集完毕 → 写入数据库"""
        if not db:
            return {
                "intent": state.intent,
                "response": f"📋 信息已收集完整！请通过对应 API 接口提交。",
                "confidence": 0.9,
            }

        try:
            if state.intent == "feedback":
                from crud import FeedbackCRUD
                from schemas import FeedbackCreateRequest
                req = FeedbackCreateRequest(
                    student_id=student_id,
                    content=state.collected.get("content", user_input[:200]),
                    detail=info.get("详细描述", user_input),
                    feedback_type=info.get("反馈类型", "投诉"),
                    urgency_level="中",
                )
                ticket = FeedbackCRUD.create(db, req)
                db.commit()
                return {
                    "intent": "feedback",
                    "response": f"📋 已为你创建工单 #{ticket.id}，我们会在24小时内响应~",
                    "confidence": 0.9,
                }

            elif state.intent == "admin_service":
                from crud import StudentServiceCRUD
                from schemas import LeaveCreateRequest
                start_val = state.collected.get("start_time")
                end_val = state.collected.get("end_time")
                # 将相对日期（明天/后天等）转为标准 datetime
                if isinstance(start_val, str):
                    start_val = normalize_datetime(start_val) or start_val
                if isinstance(end_val, str):
                    end_val = normalize_datetime(end_val) or end_val
                req = LeaveCreateRequest(
                    student_id=student_id,
                    service_type="请假",
                    leave_type=state.collected.get("leave_type", "事假"),
                    start_time=start_val,
                    end_time=end_val,
                    reason=state.collected.get("reason", user_input[:100]),
                )
                leave = StudentServiceCRUD.create_leave(db, req)
                db.commit()
                return {
                    "intent": "admin_service",
                    "response": (
                        f"📝 请假申请已提交 (ID: {leave.id})\n"
                        f"  类型: {state.collected.get('leave_type', '事假')}\n"
                        f"  时间: {state.collected.get('start_time', '')} ~ {state.collected.get('end_time', '')}\n"
                        f"  原因: {state.collected.get('reason', '')}\n\n"
                        f"等待审批中，请留意通知~"
                    ),
                    "confidence": 0.9,
                }

            return {
                "intent": state.intent,
                "response": "数据已收集完整，请通过对应接口提交。",
                "confidence": 0.9,
            }
        except Exception as e:
            return {"intent": state.intent, "response": f"提交失败: {e}", "confidence": 0.9}

    def _handle_academic_query(self, user_input: str, entities: dict,
                               student_id: int, db) -> str:
        """学业考务查询 —— 考试/DDL查询"""
        if not db or not student_id:
            return self._fallback_academic_response(user_input)

        try:
            from crud import AcademicCRUD
            from model import StudentAcademic

            # 提取可能的过滤条件
            info = self.llm.extract_info(
                user_input,
                ["学术类型", "课程名称", "时间范围", "是否紧急"]
            )
            acad_type = info.get("学术类型", "")
            course_name = info.get("课程名称", "")

            # 查询
            items = AcademicCRUD.get_by_student(db, student_id, acad_type)

            if not items:
                return "没有找到你的教务信息。请确认教务数据已录入系统。如有疑问请联系班主任。"

            # 过滤
            if course_name:
                items = [i for i in items if course_name in (i.course_name or "")]

            lines = ["📚 你的教务信息："]
            for a in items:
                deadline = str(a.deadline)[:16] if a.deadline else "未知"
                status_icon = {"未完成": "⏳", "已完成": "✅", "已逾期": "⚠️"}.get(a.ddl_status, "")
                lines.append(
                    f"  {status_icon} [{a.academic_type}] {a.title}\n"
                    f"     课程: {a.course_name} | 截止: {deadline} | 状态: {a.ddl_status}"
                )

            # 获取即将到期的
            upcoming = AcademicCRUD.get_upcoming(db, student_id, days=14)
            if upcoming:
                lines.append(f"\n⚠️ 未来14天内有 {len(upcoming)} 项即将到期，请注意时间安排！")

            return "\n".join(lines)
        except Exception as e:
            return f"查询教务信息失败: {e}"

    def _handle_progress_track(self, user_input: str, entities: dict,
                               student_id: int, db) -> str:
        """留学进度追踪"""
        if not db or not student_id:
            return self._fallback_progress_response(user_input)

        try:
            from crud import StudyAbroadCRUD

            items = StudyAbroadCRUD.get_by_student(db, student_id)
            if not items:
                return "暂无你的留学进度数据。请联系你的留学顾问了解最新进展。"

            # 找当前阶段
            current = StudyAbroadCRUD.get_current_stage(db, student_id)

            lines = ["🎓 你的留学进度："]
            stage_icons = {1: "📝", 2: "🔍", 3: "📤", 4: "📨", 5: "🎉", 6: "✈️", 7: "🧳"}
            progress_bar = []

            for item in items:
                icon = stage_icons.get(item.stage_order, "•")
                status_mark = "✅" if item.stage_status == "已完成" else "🔄" if item.stage_status == "进行中" else "⏸️"
                is_cur = " ← 当前" if item.is_current else ""
                lines.append(
                    f"  {icon} {item.stage} [{item.stage_status}] {status_mark}{is_cur}\n"
                    f"     {item.stage_detail or ''}"
                )
                progress_bar.append("🟢" if item.stage_status == "已完成" else "🔵" if item.is_current else "⚪")

            if current:
                lines.append(f"\n📍 当前在「{current.stage}」阶段")
                lines.append(f"   负责人: {current.handler_name or '待分配'}")
                if current.estimated_complete_date:
                    lines.append(f"   预计完成: {current.estimated_complete_date}")
                lines.append("".join(progress_bar))

            return "\n".join(lines)
        except Exception as e:
            return f"查询进度失败: {e}"

    def _handle_life_support(self, user_input: str, entities: dict,
                             student_id: int, db) -> str:
        """海外生活支持 —— RAG 检索"""
        context = self.rag.retrieve_context(
            f"海外 生活 医疗 交通 安全 住宿 银行 {user_input}"
        )
        if context:
            prompt = LIFE_SUPPORT_PROMPT.format(context=context, user_input=user_input)
            return self.llm.chat(prompt, user_input)

        # 无知识库匹配时给出通用建议
        keywords_map = {
            "医生": "如需要就医，可以联系学校国际学生办公室协助预约，或查找附近的General Practitioner (GP)。",
            "感冒": "轻微感冒可以去当地药房(Pharmacy)购买非处方药。如症状严重，建议预约GP就诊。",
            "报警": "紧急情况请拨打报警电话。新加坡: 999，德国: 110，英国: 999。",
            "大使馆": "可访问中国驻当地大使馆官网获取领事保护与服务，或拨打外交部全球领事保护热线12308。",
            "交通": "建议办理当地学生交通卡，享受学生优惠。地铁/公交是最经济的出行方式。",
            "银行": "凭护照和学生签证/录取通知书即可在当地银行开户。建议选择有学生账户套餐的银行。",
            "手机": "当地主要运营商提供预付费和学生套餐。携带护照和住址证明即可办理。",
        }
        for kw, tip in keywords_map.items():
            if kw in user_input:
                return f"💡 {tip}\n\n如需更详细的信息，建议查阅海外生活指南或咨询学校国际学生办公室~"

        return (
            "关于海外生活的问题，我目前的知识库可能还不够全面。\n"
            "建议你：\n"
            "1. 咨询学校的国际学生办公室\n"
            "2. 加入当地中国留学生群获取经验分享\n"
            "3. 也可以更具体地描述你的问题，我尽力帮你查找~"
        )

    def _handle_upgrade_intent(self, user_input: str, entities: dict,
                               student_id: int, db) -> str:
        """增值转化 —— 识别升学意向，推荐项目"""
        # 提取学生信息和意向
        info = self.llm.extract_info(
            user_input,
            ["当前学历", "意向国家", "意向专业", "意向学位", "预算"]
        )

        # 从数据库获取可推荐项目
        projects_text = ""
        if db:
            try:
                from model import CourseProject
                projects = db.query(CourseProject).filter(
                    CourseProject.delete_flag == 0
                ).all()
                projects_text = "\n".join(
                    f"- {p.project_name}: {p.description or ''} ({p.target_audience or ''})"
                    for p in projects
                )
            except Exception:
                pass

        if not projects_text:
            projects_text = (
                "- 新加坡国际本硕升学计划: 2+2本科班、0.5/1+2本科班等\n"
                "- 中德精英人才共建计划: 德国双元制职业教育\n"
                "- 硕士进阶项目: 本硕连读通道"
            )

        student_info = json.dumps(info, ensure_ascii=False)
        prompt = UPGRADE_PROMPT.format(
            student_info=student_info,
            projects=projects_text,
            user_input=user_input,
        )
        reply = self.llm.chat(prompt, user_input)

        # 记录转化线索
        if student_id and db:
            self._record_upgrade_lead(student_id, info, db)

        return reply

    def _handle_data_query(self, user_input: str, entities: dict,
                           student_id: int, db) -> str:
        """NL2SQL 数据查询 —— 仅限学生本人数据"""
        if not db:
            return (
                "数据库连接不可用。\n"
                "你可以尝试以下查询：\n"
                "  • '查询我的成绩'\n"
                "  • '我的请假记录'\n"
                "  • '我的教务DDL'\n"
                "  • '我的留学进度'"
            )
        if not student_id:
            return "未能识别你的学生身份，请先登录后再试。"
        try:
            result = self.nl2sql.query(db, user_input, student_scope=student_id)
            if "error" in result:
                return f"查询失败: {result['error']}\n请尝试更具体的描述，如'查询我的成绩'或'我的请假记录'。"

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

    def _handle_chitchat(self, user_input: str, entities: dict,
                         student_id: int, db) -> str:
        """日常闲聊（附带轻量心理评估）"""
        prompt = "你是粤教服务的学生助手小粤，用温暖轻松的语气和学生聊天。回复2-3句话，可以适当鼓励。"
        try:
            result = self.llm.chat(prompt, user_input)
            if result.startswith("[LLM"):
                return self._local_chitchat(user_input)
            return result
        except Exception:
            return self._local_chitchat(user_input)

    def _local_chitchat(self, user_input: str) -> str:
        greetings = {
            '你好': '你好呀！我是小粤，有什么可以帮你的吗？学习、生活、留学方面的问题都可以问我~',
            'hi': 'Hi！有什么需要帮忙的吗？',
            '嗨': '嗨！最近怎么样？有什么想问我的吗？',
            '早上好': '早上好！新的一天，一起加油！',
            '谢谢': '不客气！希望你一切顺利~',
            '再见': '再见！照顾好自己哦~',
        }
        for kw, reply in greetings.items():
            if kw in user_input:
                return reply
        return f"嗯嗯，关于「{user_input}」，你想聊什么呢？我随时在这陪你~"

    # ==================== 辅助方法 ====================

    def _record_alert(self, student_id: int, evaluation: dict, db) -> None:
        """记录心理预警到数据库"""
        if not db:
            return
        try:
            from model import StudentPsychAlert
            alert = StudentPsychAlert(
                student_id=student_id,
                trigger_reason=evaluation.get("trigger_reason", "情绪评估触发"),
                risk_level=self.psych.get_alert_level(evaluation),
                alert_source="聊天对话",
                status="未处理",
            )
            db.add(alert)
            # 更新心理画像
            from model import StudentPsychProfile
            profile = db.query(StudentPsychProfile).filter(
                StudentPsychProfile.student_id == student_id
            ).first()
            if profile:
                profile.latest_emotion_tag = evaluation.get("emotion_tag", "")
                profile.emotion_score = evaluation.get("emotion_score", 50)
                profile.risk_level = evaluation.get("risk_level", "none")
                profile.last_interaction_time = __import__("datetime").datetime.now()
            db.flush()
        except Exception:
            pass

    def _record_upgrade_lead(self, student_id: int, info: dict, db) -> None:
        """记录增值转化线索到CRM"""
        if not db:
            return
        try:
            from model import CrmLead, SysUser
            student = db.query(SysUser).filter(
                SysUser.id == student_id, SysUser.delete_flag == 0
            ).first()
            if not student:
                return
            lead = CrmLead(
                customer_name=student.real_name,
                contact_info=student.contact_info,
                education=info.get("当前学历", ""),
                intended_country=info.get("意向国家", ""),
                intended_major=info.get("意向专业", ""),
                status="新增意向",
                source_channel="学生助手-增值转化",
                background_info=f"存量学生转化, 意向学位: {info.get('意向学位', '')}",
                owner_employee_id=1,
            )
            db.add(lead)
            db.flush()
        except Exception:
            pass

    def _fallback_academic_response(self, user_input: str) -> str:
        """无数据库时的学业查询兜底回复"""
        return (
            "学业考务查询需要连接数据库。\n"
            "你可以通过以下接口查询：\n"
            "  • GET /api/student/academic?student_id=你的ID\n"
            "  • GET /api/student/academic/upcoming?student_id=你的ID&days=14\n\n"
            "请提供你的学生ID，或直接调用上述接口~"
        )

    def _fallback_progress_response(self, user_input: str) -> str:
        """无数据库时的进度查询兜底回复"""
        return (
            "留学进度查询需要连接数据库。\n"
            "你可以通过以下接口查询：\n"
            "  • GET /api/student/study-abroad?student_id=你的ID\n"
            "  • GET /api/student/study-abroad/current?student_id=你的ID\n\n"
            "请提供你的学生ID，或直接调用上述接口~"
        )

    # ==================== 便捷入口 ====================

    def chat(self, user_input: str, student_id: int = None, db=None) -> str:
        """单次对话"""
        result = self.route_intent(user_input, student_id, db)
        return result["response"]

    def process_message(self, text: str) -> dict:
        """处理学生消息（兼容旧接口），返回完整结果"""
        result = self.route_intent(text)
        return {"reply": result["response"], "intent": result["intent"]}
