"""
粤教服务 - 系统级 API 路由
根路径、健康检查
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter(tags=["系统"])


@router.get("/")
def root():
    """服务根路径"""
    return {"msg": "粤教服务AI Agent API运行中", "status": "ok"}


@router.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
