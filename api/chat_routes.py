"""
粤教服务 - 统一对话入口
替代 Dify 顶级路由，将用户消息分发到对应的子Agent
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from utils.llm_client import get_llm_client
from agents.customer_service.agent import CustomerServiceAgent
from agents.enterprise.agent import EnterpriseAgent
from agents.student.agent import StudentAgent

router = APIRouter(tags=["统一对话入口"])


class ChatRequest(BaseModel):
    message: str
    student_id: int | None = None


TOP_LEVEL_INTENTS = {
    "customer": "外部客户咨询：了解公司信息/业务项目/留学政策/活动报名/客户画像等",
    "enterprise": "企业内部办公：员工日报/CRM客户管理/数据查询/审批/新人指引/仪表盘等",
    "student": "留学生服务：请假申请/心理关怀/学业查询/留学进度/生活支持/反馈建议等",
}

# 本地关键词意图识别（LLM不可用时的 fallback）
ENTERPRISE_KW = ['客户', 'crm', '日报', '审批', '仪表盘', '数据', '统计', '组织架构', '部门',
                 '员工', '成绩', '请假', '录入', '更新', '修改', '跟进', '签约', '意向',
                 '查询', 'sql', '数据库', '表', '周报', '月报', '工作记录']
STUDENT_KW = ['我的', '成绩', '考试', '论文', '作业', 'ddl', '截止', '留学', '申请',
              '签证', '心理', '焦虑', '压力', '请假', '通知', '进度', '阶段', '课程']
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


@router.post("/api/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """统一对话入口 —— LLM 意图识别优先，本地关键词兜底"""
    llm = get_llm_client()
    message = req.message.strip()

    # 1. 优先用 LLM 做意图分类
    agent_type = None
    try:
        result = llm.classify_intent(req.message, TOP_LEVEL_INTENTS)
        llm_intent = result.get("intent", "")
        if llm_intent and not llm_intent.startswith("[LLM") and llm_intent != "fallback":
            agent_type = llm_intent
    except Exception:
        pass

    # 2. LLM 失败 → 用本地关键词兜底
    if not agent_type:
        agent_type = _local_classify(message)

    # 3. 路由到对应 Agent
    if agent_type in ("enterprise", "fallback"):
        agent = EnterpriseAgent()
        output = agent.route_intent(req.message, db=db)
        output["agent"] = "enterprise"
    elif agent_type == "student":
        agent = StudentAgent()
        output = agent.route_intent(req.message, student_id=req.student_id, db=db)
        output["agent"] = "student"
    else:
        agent = CustomerServiceAgent()
        output = agent.route_intent(req.message)
        output["agent"] = "customer"

    return output
