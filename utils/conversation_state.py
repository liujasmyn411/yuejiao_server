"""
会话状态管理 —— 支持多轮对话的槽位填充（slot-filling）
当用户意图为"向表中插入数据"时，AI 会持续追问直到所有必填字段收集完毕。
"""
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SlotState:
    """单个数据收集会话的槽位状态"""
    intent: str                          # 当前意图，如 "feedback", "admin_service"
    table_name: str                      # 目标表名
    agent_type: str                      # 所属 agent: "student"/"enterprise"/"customer"
    required_fields: dict                # 必填字段: {field_name: display_name}
    collected: dict = field(default_factory=dict)   # 已收集的字段值
    missing: list = field(default_factory=list)     # 尚缺的字段名列表
    phase: str = "collecting"            # collecting → confirming → done
    confirmed: bool = False              # 用户已确认
    confirm_retries: int = 0             # 确认阶段循环次数（防死循环）
    interaction_count: int = 0           # 总交互次数（防无限循环）
    created_at: float = field(default_factory=time.time)

    # 取消关键词
    CANCEL_KEYWORDS = ["取消", "算了", "不用了", "不要了", "放弃", "不提交", "不填了",
                       "不投诉", "不请假", "不录了", "不报了"]

    # 确认关键词
    CONFIRM_KEYWORDS = ["确认", "是的", "对的", "没问题", "可以", "行", "好", "好的",
                        "嗯", "对", "是", "提交", "ok", "OK", "yes", "y"]

    # 切换话题关键词 —— 用户明显想另起话题（第一层逃生：快速关键词）
    SWITCH_TOPIC_KW = [
        "查询", "查看", "帮我查", "我想查", "帮我看看", "我想看", "看一下",
        "成绩", "分数", "考试", "论文", "作业", "ddl", "截止",
        "进度", "状态", "课程", "活动", "报名", "请假", "日报", "天气",
        "通知", "消息", "信息", "记录", "历史", "我的",
        "签证", "留学", "申请", "心理", "安排", "课表",
    ]

    # 最大交互次数 —— 超过后自动清状态（第三层逃生：计数兜底）
    MAX_INTERACTIONS = 5

    def is_complete(self) -> bool:
        return len(self.missing) == 0

    def collect(self, field_name: str, value) -> None:
        """记录一个已收集的字段"""
        self.collected[field_name] = value
        if field_name in self.missing:
            self.missing.remove(field_name)

    def next_missing_display(self) -> str:
        """下一个需要追问的字段的中文名"""
        if self.missing:
            return self.required_fields.get(self.missing[0], self.missing[0])
        return ""

    @classmethod
    def is_cancel(cls, user_input: str) -> bool:
        """检测用户是否想取消当前操作"""
        return any(kw in user_input for kw in cls.CANCEL_KEYWORDS)

    @classmethod
    def is_confirm(cls, user_input: str) -> bool:
        """检测用户是否确认提交"""
        stripped = user_input.strip()
        # 短确认词（≤3字）精确匹配
        if len(stripped) <= 3:
            return stripped in cls.CONFIRM_KEYWORDS
        # 长文本包含确认词
        return any(kw in stripped for kw in ["确认", "提交", "没问题", "可以"])

    def summary(self) -> str:
        """生成已收集字段的摘要"""
        lines = []
        for name, display in self.required_fields.items():
            value = self.collected.get(name, "（未填写）")
            lines.append(f"  • {display}: {value}")
        return "\n".join(lines)


# ============================================================
# 各表必填字段定义（排除 autoincrement 主键和有默认值的字段）
# key: 字段名, value: 中文显示名
# ============================================================
TABLE_REQUIRED_FIELDS: dict[str, dict[str, str]] = {
    "student_feedback_ticket": {
        "student_id": "学生ID",
        "content": "投诉/反馈内容",
    },
    "student_admin_service": {
        "student_id": "学生ID",
        "service_type": "服务类型（请假/考务）",
        "leave_type": "请假类型（病假/事假）",
        "start_time": "开始时间",
        "end_time": "结束时间",
        "reason": "请假原因",
    },
    "crm_lead": {
        "customer_name": "客户姓名",
        "owner_employee_id": "归属员工ID",
    },
    "employee_daily_report": {
        "employee_id": "员工ID",
        "content": "日报内容",
    },
}

# 意图 → 表名映射
INTENT_TO_TABLE: dict[str, str] = {
    "feedback": "student_feedback_ticket",
    "admin_service": "student_admin_service",
    "lead_create": "crm_lead",
    "daily_report": "employee_daily_report",
}


def get_required_fields(table_name: str, context: dict = None) -> dict[str, str]:
    """
    获取指定表的必填字段。
    context 中的字段视为已满足，自动排除。
    返回仍需要用户提供的字段: {field_name: display_name}
    """
    fields = TABLE_REQUIRED_FIELDS.get(table_name, {}).copy()
    if context:
        for key in list(fields.keys()):
            if key in context and context[key] is not None:
                del fields[key]
    return fields


class ConversationStateManager:
    """会话状态管理器 —— 基于用户ID追踪多轮对话"""

    def __init__(self, ttl_seconds: int = 600):
        self._states: dict[str, SlotState] = {}  # key: session_key → SlotState
        self._ttl = ttl_seconds

    def _make_key(self, student_id: int = None, user_id: int = None,
                  session_id: str = None) -> str:
        if student_id:
            return f"student:{student_id}"
        if user_id:
            return f"user:{user_id}"
        if session_id:
            return f"session:{session_id}"
        return "anonymous"

    def get(self, student_id: int = None, user_id: int = None,
            session_id: str = None) -> Optional[SlotState]:
        """获取当前活跃的槽位填充状态，过期自动清除"""
        self._sweep_expired()
        key = self._make_key(student_id, user_id, session_id)
        state = self._states.get(key)
        if state and time.time() - state.created_at > self._ttl:
            del self._states[key]
            return None
        return state

    def _sweep_expired(self) -> None:
        """清理所有已过期的状态，防止内存泄漏"""
        now = time.time()
        expired = [
            k for k, v in self._states.items()
            if now - v.created_at > self._ttl
        ]
        for k in expired:
            del self._states[k]

    def start(self, intent: str, table_name: str, agent_type: str,
              student_id: int = None, user_id: int = None,
              session_id: str = None, context: dict = None) -> SlotState:
        """
        开始一个新的槽位填充会话。
        context: 可从请求上下文自动填充的字段（如 student_id, employee_id）
        """
        key = self._make_key(student_id, user_id, session_id)
        required = get_required_fields(table_name, context or {})
        collected = {}
        if context:
            for field_name, value in context.items():
                if field_name in TABLE_REQUIRED_FIELDS.get(table_name, {}):
                    collected[field_name] = value

        state = SlotState(
            intent=intent,
            table_name=table_name,
            agent_type=agent_type,
            required_fields=TABLE_REQUIRED_FIELDS.get(table_name, {}),
            collected=collected,
            missing=list(required.keys()),
        )
        self._states[key] = state
        return state

    def update(self, state: SlotState, student_id: int = None, user_id: int = None,
               session_id: str = None) -> None:
        key = self._make_key(student_id, user_id, session_id)
        self._states[key] = state

    def clear(self, student_id: int = None, user_id: int = None,
              session_id: str = None) -> None:
        key = self._make_key(student_id, user_id, session_id)
        self._states.pop(key, None)


# 全局单例
_state_manager: Optional[ConversationStateManager] = None


def get_conversation_state_manager() -> ConversationStateManager:
    global _state_manager
    if _state_manager is None:
        _state_manager = ConversationStateManager()
    return _state_manager
