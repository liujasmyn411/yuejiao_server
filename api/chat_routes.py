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


@router.post("/api/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """统一对话入口 —— 自动识别用户角色并路由到对应Agent"""
    llm = get_llm_client()

    result = llm.classify_intent(req.message, TOP_LEVEL_INTENTS)
    agent_type = result.get("intent", "customer")

    if agent_type == "enterprise":
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
