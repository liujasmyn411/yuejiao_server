"""
粤教服务 - 统一对话入口
替代 Dify 顶级路由，将用户消息分发到对应的子Agent
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from utils.llm_client import get_llm_client
from utils.conversation_state import get_conversation_state_manager
from utils.auth import get_optional_user
from agents.customer_service.agent import CustomerServiceAgent
from agents.enterprise.agent import EnterpriseAgent
from agents.student.agent import StudentAgent

router = APIRouter(tags=["统一对话入口"])


class ChatRequest(BaseModel):
    message: str
    student_id: int | None = None
    user_id: int | None = None
    session_id: str | None = None


TOP_LEVEL_INTENTS = {
    "customer": "外部客户咨询：了解公司信息/业务项目/留学政策/活动报名/客户画像等",
    "enterprise": "企业内部办公：员工日报/CRM客户管理/数据查询/审批/新人指引/仪表盘等",
    "student": "留学生个人服务：个人请假申请/心理关怀/本人学业查询/本人留学进度/生活支持/投诉反馈/建议等",
}

# 本地关键词意图识别（LLM不可用时的 fallback）
ENTERPRISE_KW = ['客户', 'crm', '日报', '审批', '仪表盘', '数据', '统计', '组织架构', '部门',
                 '员工', '成绩', '请假', '录入', '更新', '修改', '跟进', '签约', '意向',
                 '查询', 'sql', '数据库', '表', '周报', '月报', '工作记录',
                 '姓名', '年龄', '学历', '家庭', '画像', '研判', '是不是意向', '评估一下',
                 '分析一下', '匹配项目', '意向客户']
STUDENT_KW = ['我的', '成绩', '考试', '论文', '作业', 'ddl', '截止', '留学', '申请',
              '签证', '心理', '焦虑', '压力', '请假', '通知', '进度', '阶段', '课程',
              '投诉', '反馈', '建议', '不满', '售后', '查询', '数据', '记录', '表']
CUSTOMER_KW = ['项目', '课程', '费用', '学费', '报名', '活动', '讲座', '留学', '签证',
               '政策', '退款', '退费', '公司', '地址', '电话', '客服', '咨询', '推荐']
CHITCHAT_KW = ['天气', '吃饭', '电影', '音乐', '游戏', '运动', '周末', '干嘛', '无聊',
               '笑话', '故事', '新闻', '股票', '旅游', '爱好', '兴趣', '喜欢', '怎么样啊',
               '在吗', '在么', '你是谁', '你叫什么', '叫什么名字', '你能做什么', '你会什么']

def _local_classify(message: str) -> str:
    """基于关键词的本地意图分类，返回 agent 类型"""
    msg = message.lower().strip()
    # 先判断是否为闲聊
    chitchat_score = sum(1 for kw in CHITCHAT_KW if kw in msg)
    enterprise_score = sum(1 for kw in ENTERPRISE_KW if kw in msg)
    student_score = sum(1 for kw in STUDENT_KW if kw in msg)
    customer_score = sum(1 for kw in CUSTOMER_KW if kw in msg)

    # 短输入（≤4字）且无业务词 → 闲聊
    if len(message.strip()) <= 4 and not any(kw in msg for kw in ENTERPRISE_KW + STUDENT_KW + CUSTOMER_KW):
        return "chitchat"

    # 闲聊分最高 或 所有分都为0 → 闲聊
    scores = {"chitchat": chitchat_score, "enterprise": enterprise_score,
              "student": student_score, "customer": customer_score}
    if chitchat_score > enterprise_score and chitchat_score > student_score and chitchat_score > customer_score:
        return "chitchat"
    if max(scores.values()) == 0:
        return "chitchat"

    # 否则选最高分的业务类型
    biz = {"enterprise": enterprise_score, "student": student_score, "customer": customer_score}
    best = max(biz, key=biz.get)
    return best if biz[best] > 0 else "chitchat"


TOPIC_SWITCH_CHECK_PROMPT = """你是一个对话状态判断助手。用户当前有一个待处理的事项，需要判断用户的新消息是「补充当前事项的信息」还是「想切换到新话题」。

当前事项类型: {intent}
已收集信息: {collected}
当前阶段: {phase}

用户新消息: {message}

请判断用户意图，只回复一个词：
- "supplementary" —— 用户在补充/修改当前事项的信息
- "new_topic" —— 用户想切换话题，问别的事情

注意：如果用户的消息明显是查询类（如查成绩、查进度、查信息、看数据等），应该判为 new_topic。"""


def _llm_check_topic_switch(llm, message: str, state) -> bool:
    """用 LLM 判断用户是否想切换话题（第二层逃生）。
    返回 True 表示是新话题，应清除状态重新路由。"""
    try:
        prompt = TOPIC_SWITCH_CHECK_PROMPT.format(
            intent=state.intent,
            collected=state.summary(),
            phase=state.phase,
            message=message,
        )
        result = llm.chat(prompt, message)
        if result and "new_topic" in result.lower():
            return True
        return False
    except Exception:
        return False


@router.post("/api/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db),
         current_user = Depends(get_optional_user)):
    """统一对话入口 —— LLM 意图识别优先，本地关键词兜底，角色限制"""
    llm = get_llm_client()
    stm = get_conversation_state_manager()
    message = req.message.strip()

    # 确定当前用户角色
    user_type = current_user.user_type if current_user else None
    # 如果未传 student_id 但已登录是学生 → 自动填入
    if not req.student_id and current_user and current_user.user_type == "STUDENT":
        req.student_id = current_user.id

    # 0. 检查是否处于多轮数据收集会话中
    active_state = stm.get(student_id=req.student_id, user_id=req.user_id,
                            session_id=req.session_id)
    if active_state:
        # 检查该会话的 agent 是否仍有权访问
        allowed = _agent_allowed_for_role(active_state.agent_type, user_type)
        if not allowed:
            stm.clear(student_id=req.student_id, user_id=req.user_id,
                       session_id=req.session_id)
            agent = CustomerServiceAgent()
            output = agent.route_intent(req.message, student_id=req.student_id, db=db)
            output["agent"] = "customer"
            return output

        # 第二层逃生：LLM 意图复核 —— 判断新输入是「补充信息」还是「另起话题」
        is_new_topic = _llm_check_topic_switch(llm, message, active_state)
        if is_new_topic:
            stm.clear(student_id=req.student_id, user_id=req.user_id,
                       session_id=req.session_id)
            # 状态已清除，agent_type 仍为 None，fall-through 到步骤1走正常路由

        else:
            # 有权访问 → 继续收集
            agent_type = active_state.agent_type
            if agent_type == "student":
                agent = StudentAgent()
                output = agent.continue_data_collection(
                    message, active_state, student_id=req.student_id, db=db
                )
                output["agent"] = "student"
            elif agent_type == "enterprise":
                agent = EnterpriseAgent()
                output = agent.continue_data_collection(
                    message, active_state, user_id=req.user_id, db=db
                )
                output["agent"] = "enterprise"
            else:
                agent = CustomerServiceAgent()
                output = agent.continue_data_collection(
                    message, active_state, student_id=req.student_id, db=db
                )
                output["agent"] = "customer"
            return output

    # 1. 优先用 LLM 做意图分类
    agent_type = None
    try:
        result = llm.classify_intent(req.message, TOP_LEVEL_INTENTS)
        llm_intent = result.get("intent", "")
        if llm_intent and not llm_intent.startswith("[LLM") and llm_intent != "fallback":
            agent_type = llm_intent
    except Exception:
        pass

    # 2. LLM 失败 → 用本地关键词兜底（游客只匹配客服/闲聊词）
    if not agent_type:
        agent_type = _local_classify_for_role(message, user_type)

    # 3. 角色限制：不合规的 agent_type 回退到用户有权访问的 Agent
    if not _agent_allowed_for_role(agent_type, user_type):
        if user_type in ("EMPLOYEE", "ADMIN"):
            agent_type = "enterprise"
        else:
            agent_type = "customer"

    # 4. 路由到对应 Agent
    if agent_type == "enterprise":
        agent = EnterpriseAgent()
        output = agent.route_intent(req.message, db=db, user_id=current_user.id if current_user else None)
        output["agent"] = "enterprise"
    elif agent_type == "student":
        agent = StudentAgent()
        output = agent.route_intent(req.message, student_id=req.student_id, db=db)
        output["agent"] = "student"
    else:
        agent = CustomerServiceAgent()
        output = agent.route_intent(req.message, student_id=req.student_id, db=db)
        output["agent"] = "customer"

    return output


def _agent_allowed_for_role(agent_type: str, user_type: str | None) -> bool:
    """检查某角色是否有权访问某 Agent"""
    if agent_type == "student":
        return user_type == "STUDENT"
    if agent_type == "enterprise":
        return user_type in ("EMPLOYEE", "ADMIN")
    # customer → 所有人
    return True


def _local_classify_for_role(message: str, user_type: str | None) -> str:
    """基于关键词的本地意图分类，游客不匹配学生/企业词"""
    msg = message.lower().strip()

    chitchat_score = sum(1 for kw in CHITCHAT_KW if kw in msg)
    customer_score = sum(1 for kw in CUSTOMER_KW if kw in msg)

    if user_type in ("EMPLOYEE", "ADMIN"):
        enterprise_score = sum(1 for kw in ENTERPRISE_KW if kw in msg)
        if len(message.strip()) <= 4 and not any(
            kw in msg for kw in ENTERPRISE_KW + CUSTOMER_KW
        ):
            return "chitchat"
        scores = {"chitchat": chitchat_score, "enterprise": enterprise_score,
                  "customer": customer_score}
    elif user_type == "STUDENT":
        student_score = sum(1 for kw in STUDENT_KW if kw in msg)
        if len(message.strip()) <= 4 and not any(
            kw in msg for kw in STUDENT_KW + CUSTOMER_KW
        ):
            return "chitchat"
        scores = {"chitchat": chitchat_score, "student": student_score,
                  "customer": customer_score}
    else:
        # 游客：只匹配客服和闲聊
        if len(message.strip()) <= 4 and not any(kw in msg for kw in CUSTOMER_KW):
            return "chitchat"
        scores = {"chitchat": chitchat_score, "customer": customer_score}

    if max(scores.values()) == 0:
        return "chitchat"
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "chitchat"
