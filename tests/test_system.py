"""
系统级路由测试 —— GET /, GET /health
"""

import pytest
from fastapi.testclient import TestClient


class TestRootEndpoint:
    """GET / —— 根路径健康检查。"""

    def test_root_ok(self, client: TestClient):
        """正常请求返回 200 和 ok 状态。"""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "粤教服务" in data["msg"]

    def test_root_method_not_allowed(self, client: TestClient):
        """POST / 应返回 405。"""
        resp = client.post("/")
        assert resp.status_code == 405


class TestHealthEndpoint:
    """GET /health —— 健康检查。"""

    def test_health_ok(self, client: TestClient):
        """正常请求返回 200 和 healthy 状态。"""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "time" in data

    def test_health_method_not_allowed(self, client: TestClient):
        """POST /health 应返回 405。"""
        resp = client.post("/health")
        assert resp.status_code == 405
