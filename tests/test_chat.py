"""
统一对话入口测试
覆盖：POST /api/chat —— 意图路由到 customer / enterprise / student agent
"""

import pytest
from unittest.mock import patch, MagicMock

from utils.auth import get_optional_user


def _make_fake_user(user_type):
    """创建模拟 SysUser，仅用于权限检查"""
    m = MagicMock()
    m.user_type = user_type
    m.id = 42
    return m


class TestUnifiedChat:
    def test_routes_to_customer(self, client):
        """LLM 识别为 customer 意图时分发到 CustomerServiceAgent。"""
        with patch("api.chat_routes.get_llm_client") as mock_llm, \
             patch("agents.customer_service.agent.CustomerServiceAgent.route_intent") as mock_route:
            mock_llm.return_value.classify_intent.return_value = {"intent": "customer", "confidence": 0.9}
            mock_route.return_value = {"intent": "event_query", "response": "本月有3场活动。", "confidence": 0.88}

            resp = client.post("/api/chat", json={"message": "最近有什么活动？"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["agent"] == "customer"
            assert data["intent"] == "event_query"

    def test_routes_to_enterprise(self, client):
        """LLM 识别为 enterprise 意图时分发到 EnterpriseAgent（需员工身份）。"""
        from main import app
        app.dependency_overrides[get_optional_user] = lambda: _make_fake_user("EMPLOYEE")
        try:
            with patch("api.chat_routes.get_llm_client") as mock_llm, \
                 patch("agents.enterprise.agent.EnterpriseAgent.route_intent") as mock_route:
                mock_llm.return_value.classify_intent.return_value = {"intent": "enterprise", "confidence": 0.9}
                mock_route.return_value = {"intent": "lead_query", "response": "当前有5个意向客户。", "confidence": 0.92}

                resp = client.post("/api/chat", json={"message": "查询意向客户"})
                assert resp.status_code == 200
                data = resp.json()
                assert data["agent"] == "enterprise"
                assert data["intent"] == "lead_query"
        finally:
            del app.dependency_overrides[get_optional_user]

    def test_routes_to_student(self, client):
        """LLM 识别为 student 意图时分发到 StudentAgent（需学生身份）。"""
        from main import app
        app.dependency_overrides[get_optional_user] = lambda: _make_fake_user("STUDENT")
        try:
            with patch("api.chat_routes.get_llm_client") as mock_llm, \
                 patch("agents.student.agent.StudentAgent.route_intent") as mock_route:
                mock_llm.return_value.classify_intent.return_value = {"intent": "student", "confidence": 0.9}
                mock_route.return_value = {"intent": "chitchat", "response": "你好，有什么可以帮你的？", "confidence": 0.95}

                resp = client.post("/api/chat", json={"message": "你好", "student_id": 1})
                assert resp.status_code == 200
                data = resp.json()
                assert data["agent"] == "student"
                assert data["intent"] == "chitchat"
        finally:
            del app.dependency_overrides[get_optional_user]

    def test_defaults_to_customer_on_unknown(self, client):
        """LLM 返回未知意图时默认路由到 customer agent。"""
        with patch("api.chat_routes.get_llm_client") as mock_llm, \
             patch("agents.customer_service.agent.CustomerServiceAgent.route_intent") as mock_route:
            mock_llm.return_value.classify_intent.return_value = {"intent": "unknown", "confidence": 0.3}
            mock_route.return_value = {"intent": "unknown", "response": "", "confidence": 0.0}

            resp = client.post("/api/chat", json={"message": "..."})
            assert resp.status_code == 200
            data = resp.json()
            assert data["agent"] == "customer"

    def test_guest_forced_to_customer(self, client):
        """游客即使 LLM 识别为 student/enterprise，也被强制路由到 customer。"""
        with patch("api.chat_routes.get_llm_client") as mock_llm, \
             patch("agents.customer_service.agent.CustomerServiceAgent.route_intent") as mock_route:
            mock_llm.return_value.classify_intent.return_value = {"intent": "student", "confidence": 0.9}
            mock_route.return_value = {"intent": "faq", "response": "请咨询客服。", "confidence": 0.5}

            resp = client.post("/api/chat", json={"message": "我要请假"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["agent"] == "customer"  # 游客被强制转客服

    def test_empty_message(self, client):
        """空消息也能正常处理。"""
        with patch("api.chat_routes.get_llm_client") as mock_llm, \
             patch("agents.customer_service.agent.CustomerServiceAgent.route_intent") as mock_route:
            mock_llm.return_value.classify_intent.return_value = {"intent": "customer", "confidence": 0.8}
            mock_route.return_value = {"intent": "unknown", "response": "", "confidence": 0.0}

            resp = client.post("/api/chat", json={"message": ""})
            assert resp.status_code == 200

    def test_missing_message_field_422(self, client):
        """缺少 message 字段返回 422。"""
        resp = client.post("/api/chat", json={})
        assert resp.status_code == 422

    def test_with_student_id(self, client):
        """带 student_id 且为学生身份时正确传递给 StudentAgent。"""
        from main import app
        app.dependency_overrides[get_optional_user] = lambda: _make_fake_user("STUDENT")
        try:
            with patch("api.chat_routes.get_llm_client") as mock_llm, \
                 patch("agents.student.agent.StudentAgent.route_intent") as mock_route:
                mock_llm.return_value.classify_intent.return_value = {"intent": "student", "confidence": 0.9}
                mock_route.return_value = {"intent": "leave_request", "response": "请假已提交", "confidence": 0.9}

                resp = client.post("/api/chat", json={"message": "我要请假", "student_id": 42})
                assert resp.status_code == 200
                data = resp.json()
                assert data["agent"] == "student"
        finally:
            del app.dependency_overrides[get_optional_user]

    def test_not_json_422(self, client):
        """发送非 JSON body 返回 422。"""
        resp = client.post("/api/chat", content=b"not json", headers={"Content-Type": "application/json"})
        assert resp.status_code == 422
