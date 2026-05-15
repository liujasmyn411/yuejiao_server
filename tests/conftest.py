"""
测试配置文件 —— 提供共享 fixture：
- SQLite 测试数据库（文件模式，测试间自动清表）
- FastAPI TestClient（get_db 已替换为测试会话）
- 种子数据 fixture（学生/员工/活动/项目/意向客户）
- 边界数据生成器（faker）
"""

import os
import sys

# ═══════════════════════════════════════════════
# 强制 SQLite 模式（必须在所有 app 导入之前）
# ═══════════════════════════════════════════════
os.environ["DB_TYPE"] = "sqlite"
os.environ["SQLITE_URL"] = "sqlite:///./test.db"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from faker import Faker

from model import Base
from database import get_db

# ── 测试引擎 ──────────────────────────────────
TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

fake = Faker("zh_CN")

# ═══════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════


@pytest.fixture(scope="session")
def engine():
    """创建全部表结构（整个测试会话仅执行一次）。"""
    Base.metadata.create_all(bind=test_engine)
    yield test_engine


@pytest.fixture
def db_session(engine):
    """
    每个测试获取干净的数据库会话。
    测试结束后删除所有表数据，保证用例隔离。
    """
    db = TestSessionLocal()
    try:
        yield db
    finally:
        # 按 FK 依赖逆序清空所有表
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
        db.close()


@pytest.fixture
def client(db_session):
    """
    FastAPI TestClient —— get_db 已被替换为测试会话。
    """
    from main import app

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════
# 种子数据 fixtures
# ═══════════════════════════════════════════════


@pytest.fixture
def seed_student(db_session):
    """插入一个测试学生并返回 ORM 对象。"""
    from model import SysUser

    s = SysUser(
        username="test_student",
        password_hash="hashed_pw",
        real_name="测试学生",
        user_type="STUDENT",
        department="计算机学院",
        contact_info="13800138000",
        email="student@test.com",
        country_region="中国",
        status="正常",
    )
    db_session.add(s)
    db_session.flush()
    db_session.refresh(s)
    return s


@pytest.fixture
def seed_employee(db_session):
    """插入一个测试员工并返回 ORM 对象。"""
    from model import SysUser

    e = SysUser(
        username="test_employee",
        password_hash="hashed_pw",
        real_name="测试员工",
        user_type="EMPLOYEE",
        employee_role="留学顾问",
        department="留学部",
        contact_info="13900139000",
        email="employee@test.com",
        status="正常",
    )
    db_session.add(e)
    db_session.flush()
    db_session.refresh(e)
    return e


@pytest.fixture
def seed_event(db_session):
    """插入一个测试活动并返回 ORM 对象。"""
    from model import EventLecture
    from datetime import datetime

    ev = EventLecture(
        event_name="测试活动-新加坡留学讲座",
        event_type="线上",
        start_time=datetime(2026, 6, 15, 19, 0),
        location="腾讯会议",
        max_participants=100,
        current_participants=0,
    )
    db_session.add(ev)
    db_session.flush()
    db_session.refresh(ev)
    return ev


@pytest.fixture
def seed_lead(db_session, seed_employee):
    """插入一个测试意向客户并返回 ORM 对象。"""
    from model import CrmLead

    lead = CrmLead(
        customer_name="测试客户",
        contact_info="13600136000",
        status="新增意向",
        owner_employee_id=seed_employee.id,
    )
    db_session.add(lead)
    db_session.flush()
    db_session.refresh(lead)
    return lead


@pytest.fixture
def seed_project(db_session):
    """插入一个测试课程项目并返回 ORM 对象。"""
    from model import CourseProject

    p = CourseProject(
        project_name="测试项目-新加坡本科",
        category="新加坡-本科",
        country="新加坡",
        description="测试用项目描述",
        target_audience="高中生",
    )
    db_session.add(p)
    db_session.flush()
    db_session.refresh(p)
    return p


# ═══════════════════════════════════════════════
# 边界 / 攻击数据生成器
# ═══════════════════════════════════════════════


def make_empty_string_payload() -> dict:
    """空字符串字段的请求体。"""
    return {"content": "", "customer_name": ""}


def make_oversized_payload() -> dict:
    """超长文本（>255 字符）。"""
    return {
        "customer_name": "A" * 256,
        "content": "B" * 1000,
        "contact_info": "C" * 300,
        "detail": "D" * 5000,
    }


def make_special_chars_payload() -> dict:
    """特殊符号字段的请求体。"""
    return {
        "customer_name": "<script>alert(1)</script>",
        "content": "'; DROP TABLE students; --",
        "reason": "😈💀🎃",
        "real_name": "姓名\x00NULL",
    }


def make_sql_injection_payload() -> dict:
    """SQL 注入尝试 payload。"""
    return {
        "customer_name": "'; DROP TABLE sys_user; --",
        "content": "1' OR '1'='1",
        "contact_info": "1; UPDATE sys_user SET delete_flag=1; --",
        "reason": "' UNION SELECT * FROM sys_user --",
    }
