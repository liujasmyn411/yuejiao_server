"""
粤教服务 - 系统级 API 路由
根路径、健康检查、登录认证
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from schemas import LoginRequest
from crud import UserCRUD
from utils.auth import verify_password, create_access_token

router = APIRouter(tags=["系统"])


@router.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


@router.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """用户登录，返回 JWT access_token"""
    user = UserCRUD.get_by_username(db, req.username)
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token({"sub": str(user.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "user_type": user.user_type,
        },
    }
