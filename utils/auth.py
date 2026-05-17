"""
认证模块 —— JWT 令牌 + bcrypt 密码哈希
"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from crud import UserCRUD

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    plain_bytes = plain.encode("utf-8")[:72]
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    """FastAPI 依赖：从 Authorization: Bearer <token> 解析当前用户，缺失/无效均 401。"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="无效的认证令牌")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="令牌格式错误")
    user = UserCRUD.get_by_id(db, int(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在或已注销")
    return user


def require_student(
    current_user: "SysUser" = Depends(get_current_user),
):
    """只允许 STUDENT 角色访问"""
    if current_user.user_type != "STUDENT":
        raise HTTPException(status_code=403, detail="仅学生可访问此接口")
    return current_user


def require_employee_or_admin(
    current_user: "SysUser" = Depends(get_current_user),
):
    """只允许 EMPLOYEE 或 ADMIN 角色访问"""
    if current_user.user_type not in ("EMPLOYEE", "ADMIN"):
        raise HTTPException(status_code=403, detail="仅员工/管理员可访问此接口")
    return current_user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    """
    可选登录：尝试解析 token，有则返回用户对象，无则返回 None。
    用于统一聊天入口 —— 游客不登录也能用，但功能受限。
    """
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    return UserCRUD.get_by_id(db, int(user_id))


def enforce_self_only(current_user, target_user_id: int) -> None:
    """
    学生只能操作自己的数据，员工/管理员不受限。
    违反时抛出 403。
    """
    if current_user.user_type == "STUDENT" and current_user.id != target_user_id:
        raise HTTPException(
            status_code=403,
            detail="仅可查看/操作自己的数据"
        )
