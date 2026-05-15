"""
登录接口测试
覆盖：POST /api/login —— 正常登录 / 异常登录 / 参数校验 / 安全测试
"""

import pytest
from tests.conftest import make_sql_injection_payload

# ══════════════════════════════════════════════════════════════════════
# POST /api/login
# ══════════════════════════════════════════════════════════════════════


class TestLogin:
    def test_ok_student(self, client, seed_student):
        """学生用户使用正确密码登录成功。"""
        resp = client.post("/api/login", json={
            "username": "test_student",
            "password": "test123456",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "test_student"
        assert data["user"]["user_type"] == "STUDENT"
        assert data["user"]["real_name"] == "测试学生"
        assert "id" in data["user"]

    def test_ok_employee(self, client, seed_employee):
        """员工用户使用正确密码登录成功。"""
        resp = client.post("/api/login", json={
            "username": "test_employee",
            "password": "test123456",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "test_employee"
        assert data["user"]["user_type"] == "EMPLOYEE"

    def test_token_is_valid_jwt(self, client, seed_student):
        """登录返回的 token 是有效 JWT，可以解码。"""
        resp = client.post("/api/login", json={
            "username": "test_student",
            "password": "test123456",
        })
        token = resp.json()["access_token"]
        from utils.auth import decode_access_token
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == str(seed_student.id)

    def test_wrong_password_401(self, client, seed_student):
        """密码错误返回 401。"""
        resp = client.post("/api/login", json={
            "username": "test_student",
            "password": "wrong_password",
        })
        assert resp.status_code == 401
        assert "用户名或密码错误" in resp.json()["detail"]

    def test_user_not_found_401(self, client):
        """不存在的用户名返回 401（不应区分无用户/密码错）。"""
        resp = client.post("/api/login", json={
            "username": "ghost_user",
            "password": "test123456",
        })
        assert resp.status_code == 401
        assert "用户名或密码错误" in resp.json()["detail"]

    def test_deleted_user_401(self, client, seed_student, db_session):
        """已软删除的用户无法登录。"""
        seed_student.delete_flag = 1
        db_session.flush()
        resp = client.post("/api/login", json={
            "username": "test_student",
            "password": "test123456",
        })
        assert resp.status_code == 401

    def test_missing_username_422(self, client):
        """缺少 username 字段返回 422。"""
        resp = client.post("/api/login", json={
            "password": "test123456",
        })
        assert resp.status_code == 422

    def test_missing_password_422(self, client):
        """缺少 password 字段返回 422。"""
        resp = client.post("/api/login", json={
            "username": "test_student",
        })
        assert resp.status_code == 422

    def test_empty_body_422(self, client):
        """空请求体返回 422。"""
        resp = client.post("/api/login", json={})
        assert resp.status_code == 422

    def test_empty_username(self, client, seed_student):
        """用户名为空字符串。"""
        resp = client.post("/api/login", json={
            "username": "",
            "password": "test123456",
        })
        assert resp.status_code == 401

    def test_empty_password(self, client, seed_student):
        """密码为空字符串（hash 校验应失败）。"""
        resp = client.post("/api/login", json={
            "username": "test_student",
            "password": "",
        })
        assert resp.status_code == 401

    def test_wrong_http_method_405(self, client):
        """GET /api/login 不应被允许。"""
        resp = client.get("/api/login")
        assert resp.status_code == 405

    def test_case_sensitive_username(self, client, seed_student):
        """用户名大小写应敏感。"""
        resp = client.post("/api/login", json={
            "username": "Test_Student",
            "password": "test123456",
        })
        assert resp.status_code == 401

    def test_sql_injection_username(self, client, seed_student):
        """用户名含 SQL 注入 payload —— 应安全拒绝。"""
        inj = make_sql_injection_payload()
        resp = client.post("/api/login", json={
            "username": inj["customer_name"],
            "password": "test123456",
        })
        assert resp.status_code == 401

    def test_sql_injection_password(self, client, seed_student):
        """密码含 SQL 注入 payload —— 应安全拒绝。"""
        inj = make_sql_injection_payload()
        resp = client.post("/api/login", json={
            "username": "test_student",
            "password": inj["content"],
        })
        assert resp.status_code == 401

    def test_long_username(self, client):
        """超长用户名。"""
        resp = client.post("/api/login", json={
            "username": "A" * 500,
            "password": "test123456",
        })
        assert resp.status_code == 401

    def test_long_password(self, client, seed_student):
        """超长密码。"""
        resp = client.post("/api/login", json={
            "username": "test_student",
            "password": "B" * 500,
        })
        assert resp.status_code == 401

    def test_username_not_string_422(self, client):
        """username 为非字符串类型。"""
        resp = client.post("/api/login", json={
            "username": 12345,
            "password": "test123456",
        })
        assert resp.status_code == 422

    def test_password_not_string_422(self, client):
        """password 为非字符串类型。"""
        resp = client.post("/api/login", json={
            "username": "test_student",
            "password": 12345,
        })
        assert resp.status_code == 422
