"""
粤教服务 - 数据库连接层
管理数据库连接、会话和表创建
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings
from model import Base

# ========== 数据库连接 ==========

engine = create_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_pool_overflow,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ========== 工具函数 ==========

def create_tables():
    """创建所有表（如果不存在）"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
