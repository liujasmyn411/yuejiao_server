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


class TestGuestEventRegistration:
    """游客活动报名完整流程测试（多轮对话 + 数据落地）"""

    def _clear_state(self, session_id: str):
        from utils.conversation_state import get_conversation_state_manager
        get_conversation_state_manager().clear(session_id=session_id)

    def test_full_flow_bracket_number_creates_lead(self, client, db_session, seed_event):
        """
        游客输入「1」报名，走完姓名→联系方式→确认流程，
        最终自动创建 CRM 意向客户并写入 event_registration。
        """
        self._clear_state("test-guest-001")
        session_id = "test-guest-001"

        with patch("api.chat_routes.get_llm_client") as mock_llm_factory, \
             patch("agents.customer_service.agent.get_llm_client") as mock_agent_llm:

            mock_llm = MagicMock()
            mock_llm.classify_intent.return_value = {"intent": "event_registration", "confidence": 0.95}

            def _extract(text, fields):
                if "张三" in text:
                    return {"姓名": "张三"}
                if "138" in text:
                    return {"联系方式": "13800138000"}
                return {}

            mock_llm.extract_info.side_effect = _extract
            mock_llm_factory.return_value = mock_llm
            mock_agent_llm.return_value = mock_llm

            # 第1轮：触发报名
            r1 = client.post("/api/chat", json={"message": "我想报名活动", "session_id": session_id})
            assert r1.status_code == 200
            assert "回复活动编号" in r1.json()["response"]

            # 第2轮：回复「1」（带中文引号）
            r2 = client.post("/api/chat", json={"message": "「1」", "session_id": session_id})
            assert r2.status_code == 200
            assert "姓名" in r2.json()["response"]

            # 第3轮：提供姓名
            r3 = client.post("/api/chat", json={"message": "张三", "session_id": session_id})
            assert r3.status_code == 200
            assert "联系方式" in r3.json()["response"]

            # 第4轮：提供联系方式
            r4 = client.post("/api/chat", json={"message": "13800138000", "session_id": session_id})
            assert r4.status_code == 200
            assert "确认" in r4.json()["response"]

            # 第5轮：确认提交
            r5 = client.post("/api/chat", json={"message": "确认", "session_id": session_id})
            assert r5.status_code == 200
            assert "报名成功" in r5.json()["response"]

        # 验证数据库写入
        from model import EventRegistration, CrmLead
        reg = db_session.query(EventRegistration).filter(
            EventRegistration.event_id == seed_event.id,
            EventRegistration.contact == "13800138000",
        ).first()
        assert reg is not None, "event_registration 未写入"
        assert reg.customer_name == "张三"
        assert reg.customer_id is not None and reg.customer_id > 0, "customer_id 不应为 0"

        lead = db_session.query(CrmLead).filter(CrmLead.id == reg.customer_id).first()
        assert lead is not None, "crm_lead 未自动创建"
        assert lead.customer_name == "张三"
        assert lead.contact_info == "13800138000"
        assert lead.source_channel == "活动报名-游客"

    def test_duplicate_registration_blocked(self, client, db_session, seed_event):
        """同一联系方式重复报名应被拦截"""
        self._clear_state("test-guest-002")
        session_id = "test-guest-002"

        # 预写入一条报名记录
        from model import EventRegistration
        db_session.add(EventRegistration(
            event_id=seed_event.id,
            customer_id=999,
            customer_name="已有用户",
            contact="13900139000",
        ))
        db_session.commit()

        with patch("api.chat_routes.get_llm_client") as mock_llm_factory, \
             patch("agents.customer_service.agent.get_llm_client") as mock_agent_llm:

            mock_llm = MagicMock()
            mock_llm.classify_intent.return_value = {"intent": "event_registration", "confidence": 0.95}
            mock_llm.extract_info.side_effect = lambda text, fields: {"姓名": "李四", "联系方式": "13900139000"} if "李四" in text or "139" in text else {}
            mock_llm_factory.return_value = mock_llm
            mock_agent_llm.return_value = mock_llm

            # 快速走完流程到确认
            client.post("/api/chat", json={"message": "报名活动", "session_id": session_id})
            client.post("/api/chat", json={"message": "1", "session_id": session_id})
            client.post("/api/chat", json={"message": "李四 13900139000", "session_id": session_id})
            r = client.post("/api/chat", json={"message": "确认", "session_id": session_id})
            assert r.status_code == 200
            assert "已经报名过" in r.json()["response"]

    def test_event_full_blocked(self, client, db_session, seed_event):
        """活动已满员时报名应被拦截"""
        self._clear_state("test-guest-003")
        session_id = "test-guest-003"

        seed_event.max_participants = 1
        seed_event.current_participants = 1
        db_session.flush()
        db_session.commit()

        with patch("api.chat_routes.get_llm_client") as mock_llm_factory, \
             patch("agents.customer_service.agent.get_llm_client") as mock_agent_llm:

            mock_llm = MagicMock()
            mock_llm.classify_intent.return_value = {"intent": "event_registration", "confidence": 0.95}
            mock_llm_factory.return_value = mock_llm
            mock_agent_llm.return_value = mock_llm

            client.post("/api/chat", json={"message": "报名活动", "session_id": session_id})
            r = client.post("/api/chat", json={"message": "1", "session_id": session_id})
            assert r.status_code == 200
            assert "已满员" in r.json()["response"]
