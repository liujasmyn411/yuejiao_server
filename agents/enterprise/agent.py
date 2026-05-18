"""
企业助手 Agent - 对内智能办公助手
支持 NL2SQL / 日报 / CRM / 新人指引 等
"""
import json
import re
from agents.enterprise.prompts import (
    SYSTEM_PROMPT, INTENT_DESCRIPTIONS, GUIDE_PROMPT, LEAD_PROFILE_PROMPT
)
from agents.enterprise.nl2sql import NL2SQL
from agents.enterprise.voice_processor import VoiceProcessor
from knowledge_base.vectorizer import get_rag_engine
from utils.llm_client import get_llm_client
from utils.conversation_state import (
    get_conversation_state_manager, SlotState
)


class EnterpriseAgent:
    """粤教服务企业智能助手"""

    def __init__(self):
        self.llm = get_llm_client()
        self.rag = get_rag_engine()
        self.nl2sql = NL2SQL()
        self.voice = VoiceProcessor()
        self.name = "企业智能助手"

    # ==================== 意图路由 ====================

    def route_intent(self, user_input: str, db=None, user_id: int = None) -> dict:
        """识别意图并路由到对应处理器"""
        stm = get_conversation_state_manager()
        state = stm.get(user_id=user_id)

        # 0. 如果有等待列表选择的状态，优先处理序号输入（如「第1条」「1」）
        if state and state.extra.get("_awaiting_selection"):
            idx = self._extract_ordinal_index(user_input)
            if idx is not None:
                return self._handle_selection_input(user_input, state, db, user_id)
            # 用户没有回复有效序号，清除状态继续正常流程
            stm.clear(user_id=user_id)

        # 短输入预检：≤3字且无明确业务关键词 → 直接闲聊
        # （等待选择状态已在上面处理，不会走到这里）
        biz_keywords = ['客户', '查询', '日报', '审批', '仪表盘', '制度', '数据', '请假', '成绩',
                        '录入', '更新', '修改', '统计', '报告', '架构', '部门', '员工', '项目',
                        '姓名', '年龄', '学历', '画像', '研判', '意向', '家庭']
        stripped = user_input.strip()
        if len(stripped) <= 3 and not any(kw in stripped for kw in biz_keywords):
            return {"intent": "chitchat", "response": self._handle_chitchat(stripped, {}, db, user_id), "confidence": 0.95}

        # 学生专属操作拦截：管理员/员工试图执行仅学生可做的操作时，礼貌引导
        blocked = self._block_student_action(stripped)
        if blocked:
            return {"intent": "blocked_student_action", "response": blocked, "confidence": 0.95}

        # 关键词快速路由：对明确模式的输入直接路由，绕过 LLM 歧义
        quick = self._quick_route(stripped, db, user_id)
        if quick:
            intent, response = quick
            return {"intent": intent, "response": response, "confidence": 0.95}

        result = self.llm.classify_intent(user_input, INTENT_DESCRIPTIONS)
        intent = result.get("intent", "chitchat")

        handlers = {
            "lead_create": self._handle_lead_create,
            "lead_query": self._handle_lead_query,
            "lead_update": self._handle_lead_update,
            "daily_report": self._handle_daily_report,
            "data_query": self._handle_data_query,
            "company_guide": self._handle_company_guide,
            "approval": self._handle_approval,
            "ticket_update": self._handle_ticket_update,
            "dashboard": self._handle_dashboard,
            "lead_profile": self._handle_lead_profile,
            "chitchat": self._handle_chitchat,
        }

        handler = handlers.get(intent, self._handle_chitchat)
        if intent in ("approval", "chitchat", "ticket_update", "daily_report"):
            response = handler(user_input, result.get("entities", {}), db, user_id)
        else:
            response = handler(user_input, result.get("entities", {}), db)
        return {"intent": intent, "response": response, "confidence": result.get("confidence", 0.5)}

    def _block_student_action(self, user_input: str) -> str | None:
        """检测学生专属操作，返回礼貌引导语；不属于学生操作则返回 None"""
        # 学生专属操作的关键词模式
        student_only_patterns = [
            "请假", "我要请假", "我想请假", "提交请假", "申请请假",
            "我要投诉", "我想投诉", "提交投诉", "我要反馈", "提交反馈",
            "我的成绩", "我的学业", "我的教务", "我的留学", "我的进度",
            "我的心理", "我不开心", "我很焦虑", "我有压力",
        ]
        # 企业可处理的关键词（即使包含"请假""投诉"也不拦截）
        enterprise_allow = ["审批", "查询", "所有", "全部", "列表", "记录", "统计", "处理", "解决"]

        msg = user_input.strip()

        # 检查是否命中学生专属模式
        hit_pattern = None
        for pat in student_only_patterns:
            if pat in msg:
                hit_pattern = pat
                break

        if not hit_pattern:
            return None

        # 如果包含企业允许的关键词，放行（如"查询请假记录""审批请假"）
        if any(kw in msg for kw in enterprise_allow):
            return None

        # 生成礼貌引导语
        guides = {
            "请假": "您是管理员/员工，无法直接提交请假申请。我可以帮您：\n  • 审批学生请假\n  • 查询请假记录\n  • 查看仪表盘数据",
            "投诉": "您是管理员/员工，无法直接提交投诉。我可以帮您：\n  • 处理学生投诉工单\n  • 查询反馈记录",
            "反馈": "您是管理员/员工，无法直接提交反馈。我可以帮您：\n  • 处理学生反馈工单\n  • 查询反馈记录",
            "成绩": "您是管理员/员工，无法查询个人成绩。我可以帮您：\n  • 查询所有学生成绩\n  • 按条件筛选学生分数\n  • 录入/更新学生成绩",
            "学业": "您是管理员/员工，无法查询个人学业信息。我可以帮您：\n  • 查询所有学生教务数据\n  • 管理学生DDL提醒",
            "教务": "您是管理员/员工，无法查询个人教务信息。我可以帮您：\n  • 查询所有学生教务数据",
            "留学": "您是管理员/员工，无法查询个人留学进度。我可以帮您：\n  • 查询所有学生留学进度\n  • 更新学生进度状态",
            "进度": "您是管理员/员工，无法查询个人进度。我可以帮您：\n  • 查询所有学生留学进度",
            "心理": "您是管理员/员工，心理关怀仅对学生开放。我可以帮您：\n  • 查看学生心理预警\n  • 处理高危预警",
            "焦虑": "您是管理员/员工，心理关怀仅对学生开放。我可以帮您：\n  • 查看学生心理评估报告",
            "压力": "您是管理员/员工，心理关怀仅对学生开放。我可以帮您：\n  • 查看学生心理评估报告",
        }

        # 匹配最相关的引导语
        for kw, guide in guides.items():
            if kw in hit_pattern:
                return f"{guide}\n\n请描述具体需求~"

        return f"该操作仅限学生用户使用。作为管理员/员工，您可以查询数据、处理审批、管理客户。请描述具体需求~"

    def _quick_route(self, user_input: str, db=None, user_id: int = None) -> tuple | None:
        """关键词快速路由，绕过 LLM 意图分类歧义。返回 (intent, response) 或 None"""
        msg = user_input.strip()

        # 查询动作词（能独立表明这是一个查询操作）
        query_actions = ["查询", "记录", "列表", "历史", "数据", "统计", "日报", "周报", "报表"]
        # 审批动作词（含同义词扩展）
        approve_actions = ["审批", "通过", "驳回", "同意", "拒绝", "处理", "解决", "批准", "准予", "不批准", "不同意", "打回"]
        # 业务对象
        biz_objects = ["请假", "投诉", "反馈", "成绩", "教务", "客户", "留学", "学生", "进度",
                       "工单", "报"]
        # 非查询动作词（提交/录入/写等 → 走 LLM 分类到 lead_create/daily_report 等）
        non_query_actions = ["提交", "录入", "写下", "口述", "新增", "创建", "添加"]

        has_query_action = any(kw in msg for kw in query_actions)
        has_approve_action = any(kw in msg for kw in approve_actions)
        has_biz = any(kw in msg for kw in biz_objects)
        has_non_query = any(kw in msg for kw in non_query_actions)

        # ===== 快捷处理待办 =====
        # 处理投诉/跟进投诉/处理反馈 → 列出待处理投诉工单
        if any(kw in msg for kw in ["处理投诉", "跟进投诉", "处理反馈", "跟进反馈", "处理工单", "跟进工单"]):
            resp = self._handle_approval(user_input, {}, db, user_id)
            return ("approval", resp)
        # 审批请假/处理请假/查看请假 → 列出待审批请假
        if any(kw in msg for kw in ["审批请假", "处理请假", "查看请假", "查看待审批"]):
            resp = self._handle_approval(user_input, {}, db, user_id)
            return ("approval", resp)

        # ===== 工单状态更新 =====
        if any(kw in msg for kw in ["更新", "修改", "设置", "改为"]) and any(kw in msg for kw in ["投诉", "反馈", "工单"]) and any(kw in msg for kw in ["状态", "为"]):
            resp = self._handle_ticket_update(user_input, {}, db, user_id)
            return ("ticket_update", resp)

        # 审批操作：审批动词 + 请假/投诉/反馈 对象
        if has_approve_action and any(kw in msg for kw in ["请假", "投诉", "反馈"]):
            resp = self._handle_approval(user_input, {}, db, user_id)
            return ("approval", resp)

        # 数据查询：查询动作词存在，且没有提交/录入等非查询动作
        if has_query_action and not has_non_query:
            resp = self._handle_data_query(user_input, {}, db)
            return ("data_query", resp)

        # 数据查询补充：业务对象 + 记录/列表/历史等隐含查询词
        implicit_query = ["记录", "列表", "历史"]
        if has_biz and any(kw in msg for kw in implicit_query) and not has_non_query:
            resp = self._handle_data_query(user_input, {}, db)
            return ("data_query", resp)

        # 客户画像研判：包含画像/研判/意向客户等关键词
        profile_kw = ["画像", "研判", "意向客户", "是不是意向", "能不能成", "评估一下", "分析一下",
                      "匹配项目", "帮我看看", "这个客户"]
        if any(kw in msg for kw in profile_kw) and any(kw in msg for kw in ["年龄", "学历", "岁", "国家", "姓名"]):
            resp = self._handle_lead_profile(user_input, {}, db)
            return ("lead_profile", resp)

        return None

    # ==================== 意图处理器 ====================

    def _handle_lead_create(self, user_input: str, entities: dict, db) -> str:
        """录入意向客户 —— 槽位填充，收集必填字段后写入"""
        stm = get_conversation_state_manager()
        info = self.llm.extract_info(
            user_input,
            ["姓名", "年龄", "学历", "意向国家", "意向专业", "联系方式", "背景信息"]
        )

        customer_name = info.get("姓名", "")
        # 必填字段：customer_name（需要通过 user_id 获取 employee_id）
        if not customer_name:
            state = stm.start(
                intent="lead_create",
                table_name="crm_lead",
                agent_type="enterprise",
                user_id=None,
                context={},
            )
            for field_name, value in info.items():
                if value and field_name in state.missing:
                    state.collect(field_name, value)
            stm.update(state, user_id=None)
            return (
                f"请提供客户的基本信息，至少需要姓名哦~\n"
                f"比如：'录入新客户张三，19岁，高中生，想去新加坡读本科'"
            )

        # 有姓名，但可能缺 owner_employee_id → 需要告知 API 提交
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
                import logging
                logging.getLogger(__name__).error(
                    "NL2SQL查询失败(lead) | 输入: %s | 错误: %s | SQL: %s",
                    user_input, result["error"], result.get("sql", "")
                )
                return "查询失败，请尝试更具体的描述，如'查询所有意向为新加坡的客户'"

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
            import logging
            logging.getLogger(__name__).error("NL2SQL查询异常(lead) | 输入: %s | 异常: %s", user_input, str(e))
            return "查询时遇到问题，请换个方式描述你的需求。"

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

    def _handle_lead_profile(self, user_input: str, entities: dict, db) -> str:
        """客户画像研判 —— 输入非结构化用户信息，按研判规则评估是否为意向客户并自动录入"""
        from utils.file_parser import assess_lead_intention

        # Step 1: LLM 提取结构化信息
        profile = self._extract_profile(user_input)

        name = profile.get("姓名", "")
        age = profile.get("年龄", 0) or 0
        education = profile.get("学历", "")
        country = profile.get("意向国家", "")
        finance = profile.get("家庭经济水平", "")
        language = profile.get("语言能力", "")
        contact = profile.get("联系方式", "")
        background = profile.get("背景信息", "")
        gender = profile.get("性别", "")
        intended_major = profile.get("意向专业", "")

        if not name:
            return (
                "未识别到客户姓名。请提供包含姓名的客户信息，例如：\n"
                "「姓名 张三 性别 男 年龄 19岁 高中毕业 想去新加坡 家里经济良好」"
            )

        # Step 2: 调用统一研判函数（与文件解析共用同一套规则）
        assessment = assess_lead_intention({
            "name": name,
            "age": age,
            "education": education,
            "intended_country": country,
            "family_finance": finance,
            "language_level": language,
            "intended_major": intended_major,
            "contact": contact,
            "background_info": f"{'性别:' + gender + ' ' if gender else ''}{background or ''}".strip(),
        })

        matched = assessment["is_intended"]
        programs = [assessment["matched_program"]] if assessment["matched_program"] else []
        reasons = assessment["reasons"]
        score = assessment["score"]

        # Step 3: 构建研判结果摘要
        lines = [
            f"## 客户画像研判",
            f"",
            f"**客户姓名**: {name}",
        ]
        if gender:
            lines.append(f"**性别**: {gender}")
        if age:
            lines.append(f"**年龄**: {age}岁")
        if education:
            lines.append(f"**学历**: {education}")
        if country:
            lines.append(f"**意向国家**: {country}")
        if intended_major:
            lines.append(f"**意向专业**: {intended_major}")
        if finance:
            lines.append(f"**家庭经济**: {finance}")
        if language:
            lines.append(f"**语言能力**: {language}")
        if contact:
            lines.append(f"**联系方式**: {contact}")
        if background:
            lines.append(f"**背景信息**: {background}")

        lines.append(f"")
        lines.append(f"**研判结果**: {'✅ 符合意向客户条件' if matched else '❌ 暂不符合条件'}")
        lines.append(f"**综合评分**: {score}/100")

        if reasons:
            lines.append(f"**匹配理由**:")
            for r in reasons:
                lines.append(f"  • {r}")

        if programs:
            lines.append(f"**推荐项目**:")
            for p in programs:
                lines.append(f"  • {p}")

        # Step 4: 符合条件 → 录入意向客户表
        if matched and db:
            try:
                from model import CrmLead
                lead_data = assessment.get("lead_data", {})
                lead = CrmLead(
                    customer_name=name,
                    contact_info=contact or lead_data.get("contact_info", ""),
                    age=age if age else None,
                    education=education or "",
                    intended_country=country or lead_data.get("intended_country", ""),
                    intended_major=intended_major or lead_data.get("intended_major", ""),
                    family_finance=finance or "",
                    language_level=language or "",
                    background_info=f"{'性别:' + gender + ' ' if gender else ''}{background or ''}".strip(),
                    status="新增意向",
                    source_channel="AI对话-画像研判",
                    score=score,
                    owner_employee_id=1,
                )
                db.add(lead)
                db.commit()
                lines.append(f"")
                lines.append(f"✅ 已自动录入意向客户表（ID: {lead.id}），状态「新增意向」，渠道「AI对话-画像研判」。")
            except Exception as e:
                lines.append(f"")
                lines.append(f"⚠️ 录入意向客户表失败: {e}")
        elif matched and not db:
            lines.append(f"")
            lines.append(f"⚠️ 数据库不可用，无法自动录入。请通过 CRM 页面手动添加。")
        else:
            lines.append(f"")
            lines.append(f"💡 该用户暂不符合粤教服务的意向客户画像条件，建议持续关注。")

        return "\n".join(lines)

    def _extract_profile(self, user_input: str) -> dict:
        """调用 LLM 从非结构化文本中提取客户关键信息"""
        prompt = LEAD_PROFILE_PROMPT.format(user_input=user_input)
        try:
            result = self.llm._call_api(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500,
            )
            return json.loads(result)
        except (json.JSONDecodeError, Exception):
            # fallback: 尝试用 extract_info
            info = self.llm.extract_info(
                user_input,
                ["姓名", "性别", "年龄", "学历", "意向国家", "意向专业",
                 "家庭经济水平", "语言能力", "联系方式", "背景信息"]
            )
            return {
                "姓名": info.get("姓名", ""),
                "性别": info.get("性别", ""),
                "年龄": int(info.get("年龄", 0) or 0),
                "学历": info.get("学历", ""),
                "意向国家": info.get("意向国家", ""),
                "意向专业": info.get("意向专业", ""),
                "家庭经济水平": info.get("家庭经济水平", ""),
                "语言能力": info.get("语言能力", ""),
                "联系方式": info.get("联系方式", ""),
                "背景信息": info.get("背景信息", ""),
            }

    def _evaluate_profile(self, age, education, country, finance, language, background, gender="") -> dict:
        """根据用户画像研判规则评估客户是否符合意向条件"""
        score = 0
        reasons = []
        programs = []

        # 合并可搜索文本
        search_text = f"{education} {country} {finance} {language} {background}".lower()

        # ===== 新加坡国际本硕升学计划 =====
        sg_matched = False
        if not country or "新加坡" in country or not country:
            # 年龄规则
            if age:
                if 14 <= age <= 16:
                    sg_score = 20
                    sg_reasons = [f"年龄{age}岁，适合初中毕业生项目（2+2新加坡定向培养本科班/2+2+1本硕连读）"]
                elif 17 <= age <= 19:
                    sg_score = 25
                    sg_reasons = [f"年龄{age}岁，适合高中/中职毕业生项目（0.5/1+2国际本科班/0.5/1+2+1本硕连读）"]
                    if any(kw in search_text for kw in ["职高", "中专", "中职", "中技"]):
                        sg_reasons.append("适合就业导向项目（6+6酒店运营/9+6航空运营大专就业班）")
                        sg_score = 30
                else:
                    sg_score = 0
                    sg_reasons = []

                if sg_score > 0:
                    # 学历加分
                    edu_map = {
                        "初中": 15, "高中": 20, "职高": 20, "中专": 20,
                        "中职": 20, "中技": 20, "大专": 10, "本科": 5,
                    }
                    edu_score = 0
                    for ek, es in edu_map.items():
                        if ek in education:
                            edu_score = es
                            sg_reasons.append(f"学历{education}匹配新加坡项目")
                            break
                    sg_score += edu_score

                    # 家庭经济
                    if any(kw in search_text for kw in ["富裕", "良好", "有钱", "中等"]):
                        sg_score += 10
                        sg_reasons.append("家庭经济条件较好，适合留学项目")
                    elif "一般" in search_text:
                        sg_score += 5
                        sg_reasons.append("家庭经济一般，可考虑公费/低学费项目")

                    sg_matched = True
                    score += sg_score
                    reasons.extend(sg_reasons)
                    programs.append("新加坡国际本硕升学计划（2+2/0.5+1+2/2+2+1等）")

        # ===== 中德精英人才共建计划 =====
        de_matched = False
        if not country or "德国" in country or not country:
            if age and 18 <= age <= 35:
                de_score = 15
                de_reasons = [f"年龄{age}岁，在中德项目18-35岁范围内"]

                if any(kw in education for kw in ["高中", "大专", "本科", "硕士"]):
                    de_score += 20
                    de_reasons.append(f"学历{education}达到中德项目高中及以上要求")
                elif "初中" in education:
                    de_score = 0  # 初中不符合德国项目
                    de_reasons = []

                if de_score > 0:
                    # 语言
                    if any(kw in search_text for kw in ["德语", "German", "B1", "B2"]):
                        de_score += 15
                        de_reasons.append("有德语基础，适合德国双元制职业培训")
                    elif any(kw in search_text for kw in ["英语"]):
                        de_score += 5
                        de_reasons.append("有英语基础，可学习德语后申请")

                    # 动手能力/逻辑思维
                    if any(kw in search_text for kw in ["动手", "实操", "实践", "逻辑", "技术"]):
                        de_score += 10
                        de_reasons.append("具备动手/逻辑能力，适合德国职业教育模式")

                    de_matched = True
                    score += de_score
                    reasons.extend(de_reasons)
                    programs.append("中德精英人才共建计划（双元制职业培训+升学+永居）")

        # ===== 综合判断 =====
        matched = sg_matched or de_matched

        # 最低门槛：年龄必须在合理范围内 + 有基本学历信息
        if not age or age < 14 or age > 40:
            matched = False
            score = 0
            reasons = ["年龄不在任何项目的招生范围内（需14-35岁）"]

        # 背景信息中的加分项
        if any(kw in search_text for kw in ["留学", "出国", "海外", "国际"]):
            score += 5
            reasons.append("有明确留学意愿")
        if any(kw in search_text for kw in ["一带一路", "政策", "国家战略"]):
            score += 3
            reasons.append("关注一带一路政策")

        score = min(score, 100)
        if score >= 20 and matched:
            return {"matched": True, "score": score, "reasons": reasons, "programs": programs}
        elif score > 0:
            return {"matched": True, "score": score, "reasons": reasons, "programs": programs}  # 有分数就纳入
        else:
            return {"matched": False, "score": score, "reasons": reasons, "programs": []}

    def _handle_daily_report(self, user_input: str, entities: dict, db, user_id: int = None) -> str:
        """口述日报 → 结构化整理 → 存入会话状态等待确认提交"""
        stm = get_conversation_state_manager()
        report = self.voice.text_to_report(user_input)

        # 判断日报内容是否充分
        summary = report.get("summary", "")
        has_content = bool(summary and summary.strip() and len(summary) > 5)

        if not has_content:
            state = stm.start(
                intent="daily_report",
                table_name="employee_daily_report",
                agent_type="enterprise",
                user_id=user_id,
                context={},
            )
            stm.update(state, user_id=user_id)
            return (
                f"日报内容似乎不够详细，请多描述一下你今天的工作内容~\n"
                f"比如：完成了什么任务、遇到了什么问题、明天的计划等。"
            )

        # 内容充分 → 存入会话状态，进入确认阶段
        state = stm.start(
            intent="daily_report",
            table_name="employee_daily_report",
            agent_type="enterprise",
            user_id=user_id,
            context={"employee_id": user_id} if user_id else {},
        )
        state.missing = []
        state.collected = {
            "employee_id": user_id,
            "content": summary,
        }
        state.extra["report_data"] = report
        state.phase = "confirming"
        stm.update(state, user_id=user_id)

        lines = [
            "📋 日报已整理如下（AI润色后）：",
            f"日期: {report.get('report_date', '')}",
            f"类型: {report.get('work_type', '')}",
            "",
            "核心内容:",
            summary,
        ]
        todos = report.get("todos", "")
        if todos and todos != "None":
            lines.append(f"\n待办: {todos}")
        lines.append("\n回复「确认」提交这份日报，「取消」放弃，或继续补充内容~")
        return "\n".join(lines)

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
                import logging
                logging.getLogger(__name__).error(
                    "NL2SQL查询失败 | 输入: %s | 错误: %s | SQL: %s",
                    user_input, result["error"], result.get("sql", "")
                )
                return "查询失败，请尝试更具体的描述，如'查询所有新加坡意向的客户'或'查询本周的日报'。"

            data = result.get("data", [])
            sql = result.get("sql", "")
            sql_lower = (sql or "").lower()
            is_feedback_query = "student_feedback_ticket" in sql_lower
            is_leave_query = "student_admin_service" in sql_lower

            # 对反馈/请假查询补全状态字段（NL2SQL 可能漏选 status）
            if db and data and (is_feedback_query or is_leave_query):
                ids = [r.get("id") for r in data if r.get("id")]
                if ids:
                    try:
                        if is_feedback_query:
                            from model import StudentFeedbackTicket
                            status_map = {
                                t.id: t.status for t in
                                db.query(StudentFeedbackTicket).filter(
                                    StudentFeedbackTicket.id.in_(ids)
                                ).all()
                            }
                            for row in data:
                                row.setdefault("status", status_map.get(row.get("id"), "未知"))
                        elif is_leave_query:
                            from model import StudentAdminService
                            status_map = {
                                s.id: s.status for s in
                                db.query(StudentAdminService).filter(
                                    StudentAdminService.id.in_(ids)
                                ).all()
                            }
                            for row in data:
                                row.setdefault("status", status_map.get(row.get("id"), "未知"))
                    except Exception:
                        pass

            lines = ["查询结果："]
            if not data:
                lines.append("查询结果为空。")
            else:
                lines.append(f"共 {len(data)} 条记录：")
                if is_feedback_query:
                    for i, row in enumerate(data[:15], 1):
                        status = row.get("status", "未知")
                        status_icon = {"待处理": "⏳", "已处理": "✅", "已跟进": "📝", "处理中": "🔧", "已解决": "✅"}.get(status, "")
                        content = row.get("content", "") or ""
                        student_id = row.get("student_id", "")
                        fb_type = row.get("feedback_type", "投诉")
                        lines.append(f"  {i}. {status_icon} [#{row.get('id', '?')}] 学生:{student_id} | {fb_type} | {content[:30]}{'...' if len(content) > 30 else ''} | 状态:{status}")
                elif is_leave_query:
                    for i, row in enumerate(data[:15], 1):
                        status = row.get("status", "未知")
                        status_icon = {"待审批": "⏳", "已通过": "✅", "已驳回": "❌"}.get(status, "")
                        student_id = row.get("student_id", "")
                        leave_type = row.get("leave_type", "请假")
                        start = str(row.get("start_time", ""))[:16]
                        end = str(row.get("end_time", ""))[:16]
                        lines.append(f"  {i}. {status_icon} [#{row.get('id', '?')}] 学生:{student_id} | {leave_type} | {start}~{end} | 状态:{status}")
                else:
                    for i, row in enumerate(data[:15], 1):
                        values = ", ".join(f"{k}={v}" for k, v in list(row.items())[:6])
                        lines.append(f"  {i}. {values}")
                if len(data) > 15:
                    lines.append(f"  ... 还有 {len(data) - 15} 条")
            return "\n".join(lines)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("NL2SQL查询异常 | 输入: %s | 异常: %s", user_input, str(e))
            return "查询时遇到问题，请换个方式描述你的需求。"

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

    def _handle_approval(self, user_input: str, entities: dict, db, user_id: int = None) -> str:
        """审批操作 —— 支持通过/驳回学生请假申请，处理投诉工单"""
        # 提取结构化信息
        info = self.llm.extract_info(
            user_input,
            ["审批类型", "申请编号", "审批决定", "审批意见", "学生姓名", "学生ID"]
        )

        decision = info.get("审批决定", "")
        reason = info.get("审批意见", "")
        student_name = info.get("学生姓名", "")
        student_id_str = info.get("学生ID", "")
        request_id_str = info.get("申请编号", "")
        approval_type = info.get("审批类型", "")

        # 判断是请假审批还是投诉处理
        is_complaint = any(kw in user_input for kw in ["投诉", "反馈", "工单"])
        is_leave = any(kw in user_input for kw in ["请假"]) or not is_complaint

        # 解析审批决定
        approved = None
        if any(kw in decision for kw in ["通过", "同意", "批准", "approve"]):
            approved = True
        elif any(kw in decision for kw in ["驳回", "拒绝", "不通过", "reject", "deny"]):
            approved = False

        # 解析申请编号
        request_id = None
        if request_id_str:
            try:
                request_id = int(request_id_str.strip().lstrip("#"))
            except ValueError:
                pass
        # 尝试从用户输入中直接提取数字ID
        if not request_id:
            import re
            id_matches = re.findall(r'#?(\d+)', user_input)
            if id_matches:
                request_id = int(id_matches[0])

        if not db:
            if approved is not None:
                return f"数据库不可用，无法执行审批。审批决定：{'通过' if approved else '驳回'}，原因：{reason or '无'}"
            return "数据库不可用，无法查询待审批列表。请稍后重试。"

        try:
            from model import StudentAdminService, SysUser
            from agents.student.approval_flow import ApprovalFlow
            from crud import NotificationCRUD
        except ImportError as e:
            return f"无法加载审批模块: {e}"

        # ===== 有申请编号 → 直接审批 =====
        if request_id and approved is not None:
            record = db.query(StudentAdminService).filter(
                StudentAdminService.id == request_id,
                StudentAdminService.delete_flag == 0,
            ).first()

            if not record:
                return f"申请 #{request_id} 不存在或已删除。"
            if record.status != "待审批":
                return f"申请 #{request_id} 状态为「{record.status}」，无法重复审批。"

            student = db.query(SysUser).filter(
                SysUser.id == record.student_id,
                SysUser.delete_flag == 0,
            ).first()

            flow = ApprovalFlow()
            result = flow.approve(db, request_id, user_id or 0, approved, reason)

            if not result.get("success"):
                return f"审批失败: {result.get('message', '未知错误')}"

            # 创建通知
            student_display = student.real_name if student else f"学生{record.student_id}"
            if approved:
                notif_title = "请假申请已通过"
                notif_content = f"您的{record.leave_type or '请假'}申请已审批通过。"
                notif_type = "leave_approved"
            else:
                notif_title = "请假申请已驳回"
                notif_content = f"您的{record.leave_type or '请假'}申请已被驳回。原因：{reason or '无'}"
                notif_type = "leave_rejected"

            NotificationCRUD.create(db, recipient_id=record.student_id, title=notif_title,
                                    content=notif_content, notification_type=notif_type,
                                    related_id=request_id)
            db.commit()

            status_icon = "✅" if approved else "❌"
            status_text = "已通过" if approved else "已驳回"
            lines = [
                f"{status_icon} 请假申请 #{request_id} {status_text}",
                f"",
                f"**学生**: {student_display}",
                f"**类型**: {record.leave_type or '请假'}",
                f"**时间**: {str(record.start_time)[:16] if record.start_time else '?'} ~ {str(record.end_time)[:16] if record.end_time else '?'}",
                f"**原因**: {record.reason or '无'}",
            ]
            if not approved and reason:
                lines.append(f"**驳回原因**: {reason}")
            return "\n".join(lines)

        # ===== 有学生姓名 → 查找该学生的待审批请假 =====
        if student_name and approved is not None:
            students = db.query(SysUser).filter(
                SysUser.real_name.like(f"%{student_name}%"),
                SysUser.delete_flag == 0,
            ).all()

            if not students:
                return f"未找到姓名为「{student_name}」的学生，请确认姓名是否正确。"

            if len(students) > 1:
                names = ", ".join(f"{s.real_name}(ID:{s.id})" for s in students[:5])
                return f"找到多个匹配的学生: {names}\n请指定具体的学生姓名或ID后重试。"

            student = students[0]
            pending = db.query(StudentAdminService).filter(
                StudentAdminService.student_id == student.id,
                StudentAdminService.status == "待审批",
                StudentAdminService.delete_flag == 0,
            ).order_by(StudentAdminService.create_time.desc()).all()

            if not pending:
                return f"{student.real_name} 目前没有待审批的请假申请。"

            if len(pending) == 1:
                # 只有一条 → 直接审批
                record = pending[0]
                flow = ApprovalFlow()
                result = flow.approve(db, record.id, user_id or 0, approved, reason)

                if not result.get("success"):
                    return f"审批失败: {result.get('message', '未知错误')}"

                if approved:
                    notif_title = "请假申请已通过"
                    notif_content = f"您的{record.leave_type or '请假'}申请已审批通过。"
                    notif_type = "leave_approved"
                else:
                    notif_title = "请假申请已驳回"
                    notif_content = f"您的{record.leave_type or '请假'}申请已被驳回。原因：{reason or '无'}"
                    notif_type = "leave_rejected"

                NotificationCRUD.create(db, recipient_id=student.id, title=notif_title,
                                        content=notif_content, notification_type=notif_type,
                                        related_id=record.id)
                db.commit()

                status_icon = "✅" if approved else "❌"
                status_text = "已通过" if approved else "已驳回"
                lines = [
                    f"{status_icon} {student.real_name} 的请假申请 {status_text}",
                    f"",
                    f"**申请编号**: #{record.id}",
                    f"**类型**: {record.leave_type or '请假'}",
                    f"**时间**: {str(record.start_time)[:16] if record.start_time else '?'} ~ {str(record.end_time)[:16] if record.end_time else '?'}",
                    f"**原因**: {record.reason or '无'}",
                ]
                if not approved and reason:
                    lines.append(f"**驳回原因**: {reason}")
                return "\n".join(lines)
            else:
                # 多条待审批 → 列出供选择
                lines = [
                    f"{student.real_name} 有 {len(pending)} 条待审批请假申请：",
                    f"",
                ]
                index_map = {}
                for i, p in enumerate(pending, 1):
                    start = str(p.start_time)[:16] if p.start_time else "?"
                    end = str(p.end_time)[:16] if p.end_time else "?"
                    lines.append(f"  {i}. [#{p.id}] [{p.leave_type or '请假'}] {start} ~ {end} — {p.reason or '无理由'}")
                    index_map[i] = p.id
                
                # 保存等待选择状态
                stm = get_conversation_state_manager()
                s = stm.start(
                    intent="approval",
                    table_name="",
                    agent_type="enterprise",
                    user_id=user_id,
                    context={},
                )
                s.phase = "awaiting_selection"
                s.extra["_awaiting_selection"] = True
                s.extra["_selection_type"] = "approval"
                s.extra["_index_to_id"] = index_map
                s.extra["_approved"] = approved
                s.extra["_is_complaint"] = False
                stm.update(s, user_id=user_id)
                
                lines.append(f"")
                lines.append("请回复序号（如「1」或「第1条」）选择要审批的申请。")
                return "\n".join(lines)

        # ===== 没有明确审批决定或有学生姓名但未指定决定 → 列出待处理列表 =====
        if not student_name and approved is None:
            # 投诉/反馈工单列表
            if is_complaint:
                from model import StudentFeedbackTicket
                pending = db.query(StudentFeedbackTicket).filter(
                    StudentFeedbackTicket.status == "待处理",
                    StudentFeedbackTicket.delete_flag == 0,
                ).order_by(StudentFeedbackTicket.create_time.desc()).limit(20).all()

                if not pending:
                    return (
                        "📭 当前没有待处理的投诉/反馈工单。\n\n"
                        "处理操作示例：\n"
                        "  • 「通过投诉 #3」— 按编号处理\n"
                        "  • 「处理李四的投诉」— 按学生姓名处理\n"
                        "  • 「查看待处理投诉」— 列出所有待处理工单"
                    )

                lines = [f"📋 当前共有 {len(pending)} 条待处理投诉/反馈工单：", ""]
                index_map = {}
                for i, p in enumerate(pending[:15], 1):
                    student = db.query(SysUser).filter(
                        SysUser.id == p.student_id, SysUser.delete_flag == 0
                    ).first()
                    name = student.real_name if student else f"学生{p.student_id}"
                    urgency = p.urgency_level or "中"
                    lines.append(f"  {i}. [#{p.id}] {name} [{p.feedback_type or '投诉'}] 紧急度:{urgency} | {p.content[:30]}...")
                    index_map[i] = p.id
                if len(pending) > 15:
                    lines.append(f"  ... 还有 {len(pending) - 15} 条")
                
                # 保存等待选择状态
                stm = get_conversation_state_manager()
                s = stm.start(
                    intent="approval",
                    table_name="",
                    agent_type="enterprise",
                    user_id=user_id,
                    context={},
                )
                s.phase = "awaiting_selection"
                s.extra["_awaiting_selection"] = True
                s.extra["_selection_type"] = "approval"
                s.extra["_index_to_id"] = index_map
                s.extra["_approved"] = None
                s.extra["_is_complaint"] = True
                stm.update(s, user_id=user_id)
                
                lines.append("")
                lines.append("请回复序号（如「1」或「第1条」）选择要处理的工单，并说明「通过」或「驳回」。")
                return "\n".join(lines)

            # 请假审批列表
            pending = db.query(StudentAdminService).filter(
                StudentAdminService.status == "待审批",
                StudentAdminService.delete_flag == 0,
            ).order_by(StudentAdminService.create_time.desc()).limit(20).all()

            if not pending:
                return (
                    "📭 当前没有待审批的请假申请。\n\n"
                    "审批操作示例：\n"
                    "  • 「通过张三的请假」— 按姓名审批\n"
                    "  • 「通过请假申请 #3」— 按编号审批\n"
                    "  • 「驳回李四的请假，原因：理由不充分」— 驳回并注明原因\n"
                    "  • 「查看待审批请假」— 列出所有待审批"
                )

            lines = [f"📋 当前共有 {len(pending)} 条待审批请假申请：", ""]
            index_map = {}
            for i, p in enumerate(pending[:15], 1):
                student = db.query(SysUser).filter(
                    SysUser.id == p.student_id, SysUser.delete_flag == 0
                ).first()
                name = student.real_name if student else f"学生{p.student_id}"
                start = str(p.start_time)[:16] if p.start_time else "?"
                end = str(p.end_time)[:16] if p.end_time else "?"
                lines.append(f"  {i}. [#{p.id}] {name} [{p.leave_type or '请假'}] {start} ~ {end}")
                index_map[i] = p.id
            if len(pending) > 15:
                lines.append(f"  ... 还有 {len(pending) - 15} 条")
            
            # 保存等待选择状态
            stm = get_conversation_state_manager()
            s = stm.start(
                intent="approval",
                table_name="",
                agent_type="enterprise",
                user_id=user_id,
                context={},
            )
            s.phase = "awaiting_selection"
            s.extra["_awaiting_selection"] = True
            s.extra["_selection_type"] = "approval"
            s.extra["_index_to_id"] = index_map
            s.extra["_approved"] = None
            s.extra["_is_complaint"] = False
            stm.update(s, user_id=user_id)
            
            lines.append(f"")
            lines.append("请回复序号（如「1」或「第1条」）选择要审批的申请，并说明「通过」或「驳回」。")
            return "\n".join(lines)

        # ===== 有审批决定但缺少目标 → 引导 =====
        if approved is not None and not student_name and not request_id:
            return (
                f"请说明要审批哪条申请：\n"
                f"  • 按姓名：「{'通过' if approved else '驳回'}张三的请假」\n"
                f"  • 按编号：「{'通过' if approved else '驳回'}请假申请 #3」\n"
                f"  • 查看列表：「查看待审批请假」"
            )

        # ===== 兜底：列待审批 =====
        return (
            f"审批操作示例：\n"
            f"  • 「通过张三的请假」— 按学生姓名审批\n"
            f"  • 「通过请假申请 #3」— 按申请编号审批\n"
            f"  • 「驳回李四的请假，原因：理由不充分」— 驳回\n"
            f"  • 「查看待审批请假」— 列出所有待审批申请"
        )

    def _handle_ticket_update(self, user_input: str, entities: dict, db, user_id: int = None) -> str:
        """投诉/反馈工单状态更新（非审批类，如更新为已跟进/处理中）"""
        if not db:
            return "数据库不可用，请稍后重试。"

        info = self.llm.extract_info(
            user_input,
            ["学生姓名", "工单编号", "新状态", "更新原因"]
        )

        student_name = info.get("学生姓名", "")
        ticket_id_str = info.get("工单编号", "")
        new_status = info.get("新状态", "")
        update_reason = info.get("更新原因", "")

        # 尝试从输入中提取编号
        ticket_id = None
        if ticket_id_str:
            try:
                ticket_id = int(ticket_id_str.strip().lstrip("#"))
            except ValueError:
                pass
        if not ticket_id:
            id_matches = re.findall(r'#?(\d+)', user_input)
            if id_matches:
                ticket_id = int(id_matches[0])

        # 状态白名单
        ALLOWED_STATUS = {"已跟进", "处理中", "已处理", "已解决"}

        # 如果LLM没提取到状态，尝试从原文匹配
        if not new_status or new_status not in ALLOWED_STATUS:
            for status in ALLOWED_STATUS:
                if status in user_input:
                    new_status = status
                    break

        if not new_status:
            return (
                "请说明要更新为哪种状态。支持的状态：\n"
                "  • 已跟进\n"
                "  • 处理中\n"
                "  • 已处理\n"
                "  • 已解决\n\n"
                "例如：「把李四的投诉状态更新为已跟进」"
            )

        if new_status not in ALLOWED_STATUS:
            return f"不支持的状态「{new_status}」，仅支持：已跟进、处理中、已处理、已解决。"

        from model import StudentFeedbackTicket, SysUser
        from crud import NotificationCRUD

        # ===== 按编号查找 =====
        if ticket_id:
            ticket = db.query(StudentFeedbackTicket).filter(
                StudentFeedbackTicket.id == ticket_id,
                StudentFeedbackTicket.delete_flag == 0,
            ).first()
            if not ticket:
                return f"工单 #{ticket_id} 不存在或已删除。"
        # ===== 按学生姓名查找 =====
        elif student_name:
            students = db.query(SysUser).filter(
                SysUser.real_name.like(f"%{student_name}%"),
                SysUser.delete_flag == 0,
            ).all()
            if not students:
                return f"未找到姓名为「{student_name}」的学生，请确认姓名是否正确。"
            if len(students) > 1:
                names = ", ".join(f"{s.real_name}(ID:{s.id})" for s in students[:5])
                return f"找到多个匹配的学生: {names}\n请指定具体的工单编号后重试。"

            student = students[0]
            tickets = db.query(StudentFeedbackTicket).filter(
                StudentFeedbackTicket.student_id == student.id,
                StudentFeedbackTicket.delete_flag == 0,
            ).order_by(StudentFeedbackTicket.create_time.desc()).all()

            if not tickets:
                return f"{student.real_name} 目前没有投诉/反馈工单。"
            if len(tickets) == 1:
                ticket = tickets[0]
            else:
                # 多条工单 → 列出并保存等待选择状态
                lines = [f"{student.real_name} 有 {len(tickets)} 条工单，请回复序号选择：", ""]
                index_map = {}
                for i, t in enumerate(tickets[:10], 1):
                    status_icon = {"待处理": "⏳", "已处理": "✅", "已跟进": "📝", "处理中": "🔧", "已解决": "✅"}.get(t.status, "")
                    lines.append(f"  {i}. {status_icon} [#{t.id}] {t.content[:30]}{'...' if len(t.content or '') > 30 else ''} | 状态: {t.status}")
                    index_map[i] = t.id
                lines.append("")
                lines.append(f"请回复序号（如「1」或「第1条」），我会将对应工单状态改为「{new_status}」")
                
                s = stm.start(
                    intent="ticket_update",
                    table_name="",
                    agent_type="enterprise",
                    user_id=user_id,
                    context={},
                )
                s.phase = "awaiting_selection"
                s.extra["_awaiting_selection"] = True
                s.extra["_selection_type"] = "ticket_update"
                s.extra["_index_to_id"] = index_map
                s.extra["_new_status"] = new_status
                s.extra["_original_input"] = user_input
                stm.update(s, user_id=user_id)
                return "\n".join(lines)
        else:
            # 无姓名无编号 → 列出最近工单供选择
            tickets = db.query(StudentFeedbackTicket).filter(
                StudentFeedbackTicket.delete_flag == 0,
            ).order_by(StudentFeedbackTicket.create_time.desc()).limit(10).all()
            
            if not tickets:
                return "当前系统中没有投诉/反馈工单。"
            
            lines = [f"📋 当前共有 {len(tickets)} 条工单，请回复序号选择：", ""]
            index_map = {}
            for i, t in enumerate(tickets[:10], 1):
                student = db.query(SysUser).filter(SysUser.id == t.student_id, SysUser.delete_flag == 0).first()
                name = student.real_name if student else f"学生{t.student_id}"
                status_icon = {"待处理": "⏳", "已处理": "✅", "已跟进": "📝", "处理中": "🔧", "已解决": "✅"}.get(t.status, "")
                lines.append(f"  {i}. {status_icon} [#{t.id}] {name} | {t.feedback_type or '投诉'} | {t.content[:30]}{'...' if len(t.content or '') > 30 else ''} | 状态: {t.status}")
                index_map[i] = t.id
            
            s = stm.start(
                intent="ticket_update",
                table_name="",
                agent_type="enterprise",
                user_id=user_id,
                context={},
            )
            s.phase = "awaiting_selection"
            s.extra["_awaiting_selection"] = True
            s.extra["_selection_type"] = "ticket_update"
            s.extra["_index_to_id"] = index_map
            s.extra["_new_status"] = new_status
            s.extra["_original_input"] = user_input
            stm.update(s, user_id=user_id)
            
            lines.append("")
            lines.append(f"请回复序号（如「1」或「第1条」），我会将对应工单状态改为「{new_status}」")
            return "\n".join(lines)

        # ===== 执行更新 =====
        old_status = ticket.status or "待处理"
        if old_status == new_status:
            return f"工单 #{ticket.id} 当前已经是「{new_status}」状态，无需重复更新。"

        ticket.status = new_status
        if user_id:
            ticket.handle_user_id = user_id

        # 通知学生
        NotificationCRUD.create(
            db,
            recipient_id=ticket.student_id,
            title="投诉/反馈状态已更新",
            content=f"你的投诉/反馈工单 #{ticket.id} 状态已由「{old_status}」更新为「{new_status}」。{update_reason or ''}",
            notification_type="feedback_resolved",
            related_id=ticket.id,
        )
        db.commit()

        student = db.query(SysUser).filter(SysUser.id == ticket.student_id).first()
        student_display = student.real_name if student else f"学生{ticket.student_id}"

        return (
            f"✅ 工单 #{ticket.id} 状态已更新\n"
            f"\n"
            f"**学生**: {student_display}\n"
            f"**原状态**: {old_status}\n"
            f"**新状态**: {new_status}\n"
            f"**内容摘要**: {ticket.content[:40] if ticket.content else '无'}..."
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

    def _get_pending_summary(self, db) -> dict:
        """查询全部待处理事项：待处理投诉 + 待审批请假"""
        if not db:
            return {"tickets": 0, "leaves": 0}
        try:
            from model import StudentFeedbackTicket, StudentAdminService
            pending_tickets = db.query(StudentFeedbackTicket).filter(
                StudentFeedbackTicket.status == "待处理",
                StudentFeedbackTicket.delete_flag == 0,
            ).count()
            pending_leaves = db.query(StudentAdminService).filter(
                StudentAdminService.status == "待审批",
                StudentAdminService.delete_flag == 0,
            ).count()
            return {"tickets": pending_tickets, "leaves": pending_leaves}
        except Exception:
            return {"tickets": 0, "leaves": 0}

    def _handle_chitchat(self, user_input: str, entities: dict, db, user_id: int = None) -> str:
        """日常闲聊 —— 如果有待处理事项，主动附加询问"""
        prompt = "你是粤教服务的企业助手，用轻松专业的语气和同事聊天。回复控制在2-3句话。"
        try:
            result = self.llm.chat(prompt, user_input)
            if result.startswith("[LLM"):
                response = self._local_chitchat(user_input)
            else:
                response = result
        except Exception:
            response = self._local_chitchat(user_input)

        # 主动询问待处理事项（只在有user_id且数据库可用时检测）
        if db and user_id:
            pending = self._get_pending_summary(db)
            if pending["tickets"] > 0 or pending["leaves"] > 0:
                lines = ["\n\n对了，我检测到你有一些待处理事项："]
                if pending["tickets"] > 0:
                    lines.append(f"  • {pending['tickets']} 条投诉/反馈工单待跟进")
                if pending["leaves"] > 0:
                    lines.append(f"  • {pending['leaves']} 条请假申请待审批")
                lines.append("\n需要我帮你处理吗？回复「处理投诉」或「审批请假」即可~")
                response += "\n".join(lines)

        return response

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

    # ==================== 列表序号选择 ====================

    @staticmethod
    def _extract_ordinal_index(text: str) -> int | None:
        """从用户输入中提取列表序号，支持：1、第1条、第一条、第1个、[1] 等"""
        cleaned = text.strip()
        # 阿拉伯数字格式
        patterns = [
            r"^第?(\d+)[条个号位]?[。！.!]?$",
            r"[「【\[\(\"'（(](\d+)[」】\]\"'）)]",
            r"^(\d+)$",
        ]
        for p in patterns:
            m = re.search(p, cleaned)
            if m:
                return int(m.group(1))

        # 中文数字
        cn_nums = {
            "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
        }
        m = re.search(r"^第?([一二两三四五六七八九十]+)[条个号位]?[。！.!]?$", cleaned)
        if m:
            cn = m.group(1)
            if cn in cn_nums:
                return cn_nums[cn]
            if cn.startswith("十"):
                if len(cn) == 1:
                    return 10
                rest = cn[1:]
                return 10 + cn_nums.get(rest, 0)
            if cn.endswith("十"):
                return cn_nums.get(cn[:-1], 0) * 10
            if "十" in cn:
                parts = cn.split("十")
                tens = cn_nums.get(parts[0], 0) if parts[0] else 1
                ones = cn_nums.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
                return tens * 10 + ones
        return None

    def _handle_selection_input(self, user_input: str, state: SlotState, db, user_id: int = None) -> dict:
        """处理用户在列表选择阶段的输入（如回复「第1条」「1」）"""
        stm = get_conversation_state_manager()
        idx = self._extract_ordinal_index(user_input)
        if idx is None:
            # 不是有效序号，清除状态
            stm.clear(user_id=user_id)
            return {"intent": "chitchat", "response": "已取消选择。请重新描述你的需求~", "confidence": 0.8}

        index_map = state.extra.get("_index_to_id", {})
        real_id = index_map.get(idx)
        if not real_id:
            # 序号超出范围，保留状态让用户重新输入
            selection_type = state.extra.get("_selection_type", "")
            return {
                "intent": selection_type or "chitchat",
                "response": f"序号 {idx} 不存在，请从刚才的列表中选择有效的序号，或输入「取消」退出。",
                "confidence": 0.9,
            }

        selection_type = state.extra.get("_selection_type")

        if selection_type == "ticket_update":
            new_status = state.extra.get("_new_status", "")
            stm.clear(user_id=user_id)
            # 构造一个带编号的请求重新处理
            constructed_input = f"把投诉 #{real_id} 状态改为{new_status}" if new_status else f"更新工单 #{real_id}"
            response = self._handle_ticket_update(constructed_input, {}, db, user_id)
            return {"intent": "ticket_update", "response": response, "confidence": 0.95}

        elif selection_type == "approval":
            approved = state.extra.get("_approved")
            is_complaint = state.extra.get("_is_complaint", False)
            if approved is None:
                # 还需要知道是通过还是驳回
                state.extra["_selected_id"] = real_id
                state.extra["_awaiting_decision"] = True
                state.extra["_awaiting_selection"] = False
                stm.update(state, user_id=user_id)
                obj_name = "投诉/反馈" if is_complaint else "请假"
                return {
                    "intent": "approval",
                    "response": f"已选择 #{real_id}，你想「通过」还是「驳回」这条{obj_name}申请？",
                    "confidence": 0.95,
                }
            else:
                stm.clear(user_id=user_id)
                decision = "通过" if approved else "驳回"
                obj = "投诉" if is_complaint else "请假"
                constructed_input = f"{decision}{obj} #{real_id}"
                response = self._handle_approval(constructed_input, {}, db, user_id)
                return {"intent": "approval", "response": response, "confidence": 0.95}

        stm.clear(user_id=user_id)
        return {"intent": "chitchat", "response": "选择流程出现错误，请重新描述你的需求~", "confidence": 0.8}

    # ==================== 槽位填充 ====================

    def continue_data_collection(self, user_input: str, state: SlotState,
                                 user_id: int = None, db=None) -> dict:
        """通用槽位填充 —— 支持取消 + 确认 + 重新编辑"""
        stm = get_conversation_state_manager()

        # ===== 第三层逃生：交互次数兜底 =====
        state.interaction_count += 1
        if state.interaction_count > SlotState.MAX_INTERACTIONS:
            stm.clear(user_id=user_id)
            return {
                "intent": "chitchat",
                "response": (
                    f"对话轮次较多，已自动结束之前的"
                    f"{'意向录入' if state.intent == 'lead_create' else '日报'}。"
                    f"请问还有什么可以帮你的？"
                ),
                "confidence": 0.8,
            }

        # ===== 取消检测 =====
        if SlotState.is_cancel(user_input):
            stm.clear(user_id=user_id)
            return {
                "intent": state.intent,
                "response": "好的，已取消当前操作。如有需要随时找我~",
                "confidence": 0.95,
            }

        # ===== 确认阶段 =====
        if state.phase == "confirming":
            if SlotState.is_confirm(user_input):
                # 日报意图：实际写入数据库
                if state.intent == "daily_report" and db:
                    report_data = state.extra.get("report_data", {})
                    uid = user_id or state.collected.get("employee_id")
                    from datetime import date
                    try:
                        from crud import ReportCRUD
                        ReportCRUD.create(db,
                            employee_id=uid,
                            content=report_data.get("summary", state.collected.get("content", "")),
                            report_date=report_data.get("report_date") or date.today().strftime("%Y-%m-%d"),
                            work_type=report_data.get("work_type", "日常工作"),
                            summary=report_data.get("summary", ""),
                        )
                        db.commit()
                        stm.clear(user_id=user_id)
                        return {
                            "intent": state.intent,
                            "response": "✅ 日报已提交成功！你可以在「员工日报」页面查看。",
                            "confidence": 1.0,
                        }
                    except Exception as e:
                        stm.clear(user_id=user_id)
                        return {
                            "intent": state.intent,
                            "response": f"日报提交失败: {e}",
                            "confidence": 0.9,
                        }
                stm.clear(user_id=user_id)
                return {
                    "intent": state.intent,
                    "response": (
                        f"📋 信息已确认！请通过对应 API 接口提交：\n"
                        f"  • 意向客户: POST /api/enterprise/lead\n"
                        f"  • 日报: POST /api/enterprise/report"
                    ),
                    "confidence": 0.95,
                }
            stripped = user_input.strip()

            # 条件A：短输入 → 可能是另起话题
            if len(stripped) <= 5:
                state.confirm_retries += 1
                if state.confirm_retries >= 2:
                    stm.clear(user_id=user_id)
                    return {
                        "intent": "chitchat",
                        "response": "检测到你可能想换个话题。已取消当前操作，有什么可以帮你的？",
                        "confidence": 0.8,
                    }
                stm.update(state, user_id=user_id)
                return {
                    "intent": state.intent,
                    "response": "你有一个待确认的提交。回复「确认」提交，「取消」放弃，或告诉我你想做什么~",
                    "confidence": 0.85,
                }

            # 条件B：话题切换关键词
            if any(kw in stripped for kw in SlotState.SWITCH_TOPIC_KW):
                stm.clear(user_id=user_id)
                return {
                    "intent": "chitchat",
                    "response": "好的，已取消当前操作。请重新描述你的需求，我来帮你处理~",
                    "confidence": 0.85,
                }

            # 条件C：状态已完整 → 不是补充，是另起话题
            # 条件D：状态不完整 → 当成补充信息
            if state.is_complete():
                stm.clear(user_id=user_id)
                return {
                    "intent": "chitchat",
                    "response": "好的，已取消当前操作。请重新描述你的需求，我来帮你处理~",
                    "confidence": 0.85,
                }
            state.confirm_retries = 0
            state.phase = "collecting"
            self._merge_enterprise_fields(state, user_input)
            if not state.is_complete():
                stm.update(state, user_id=user_id)
                return {
                    "intent": state.intent,
                    "response": f"收到补充。还需要「{state.next_missing_display()}」，请说明~",
                    "confidence": 0.85,
                }
            state.phase = "confirming"
            stm.update(state, user_id=user_id)
            return {
                "intent": state.intent,
                "response": f"已更新，请确认：\n\n{state.summary()}\n\n回复「确认」提交或继续补充~",
                "confidence": 0.9,
            }

        # ===== 收集阶段 =====
        # 第一层逃生：话题切换关键词检测
        stripped = user_input.strip()
        if any(kw in stripped for kw in SlotState.SWITCH_TOPIC_KW):
            stm.clear(user_id=user_id)
            return {
                "intent": "chitchat",
                "response": "好的，已取消当前操作。请重新描述你的需求，我来帮你处理~",
                "confidence": 0.85,
            }

        self._merge_enterprise_fields(state, user_input)

        if state.is_complete():
            state.phase = "confirming"
            stm.update(state, user_id=user_id)
            return {
                "intent": state.intent,
                "response": (
                    f"信息已收集完整，请确认：\n\n{state.summary()}\n\n"
                    f"回复「确认」提交，回复「取消」放弃，或继续补充~"
                ),
                "confidence": 0.9,
            }

        stm.update(state, user_id=user_id)
        return {
            "intent": state.intent,
            "response": f"收到，还需要补充「{state.next_missing_display()}」，请详细说明~",
            "confidence": 0.85,
        }

    def _merge_enterprise_fields(self, state: SlotState, user_input: str) -> None:
        """合并企业相关提取字段到槽位状态"""
        info = self.llm.extract_info(
            user_input,
            ["姓名", "年龄", "学历", "意向国家", "意向专业", "联系方式", "背景信息",
             "日报内容", "工作类型", "待办事项"]
        )
        for field_name in list(state.missing):
            if field_name == "content" and "日报内容" in info and info["日报内容"]:
                state.collect("content", info["日报内容"][:200])
            elif field_name == "content":
                state.collect("content", user_input[:200])
            elif field_name == "customer_name" and "姓名" in info and info["姓名"]:
                state.collect("customer_name", info["姓名"])
            elif field_name in info and info[field_name]:
                state.collect(field_name, info[field_name])

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
