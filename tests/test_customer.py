"""
客服 Agent 路由测试
覆盖：活动讲座 / 活动报名 / 课程项目 / 客户画像研判 / 客服对话
"""

import pytest
from unittest.mock import patch

from tests.conftest import make_special_chars_payload, make_sql_injection_payload

# ══════════════════════════════════════════════════════════════════════
# GET /api/customer/events  (公开接口)
# ══════════════════════════════════════════════════════════════════════


class TestListEvents:
    def test_ok(self, client, seed_event):
        resp = client.get("/api/customer/events")
        assert resp.status_code == 200
        assert "events" in resp.json()

    def test_empty_list(self, client):
        resp = client.get("/api/customer/events")
        assert resp.status_code == 200
        assert isinstance(resp.json()["events"], list)

    def test_method_not_allowed(self, client):
        resp = client.post("/api/customer/events")
        assert resp.status_code == 405


# ══════════════════════════════════════════════════════════════════════
# POST /api/customer/events/register  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestRegisterEvent:
    def test_ok(self, client, seed_event, seed_student, auth_headers_student):
        resp = client.post("/api/customer/events/register", json={
            "event_id": seed_event.id,
            "customer_id": seed_student.id,
            "customer_name": "报名用户",
            "contact": "13800000000",
        }, headers=auth_headers_student)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "registration_id" in data

    def test_event_not_found(self, client, seed_student, auth_headers_student):
        resp = client.post("/api/customer/events/register", json={
            "event_id": 99999,
            "customer_id": seed_student.id,
            "customer_name": "张三",
        }, headers=auth_headers_student)
        assert resp.status_code == 404

    def test_event_full_400(self, client, seed_event, seed_student, db_session, auth_headers_student):
        seed_event.max_participants = 1
        seed_event.current_participants = 1
        db_session.flush()
        resp = client.post("/api/customer/events/register", json={
            "event_id": seed_event.id,
            "customer_id": seed_student.id,
            "customer_name": "迟到者",
        }, headers=auth_headers_student)
        assert resp.status_code == 400
        assert "已满" in resp.json()["detail"]

    def test_missing_event_id_422(self, client, seed_student, auth_headers_student):
        resp = client.post("/api/customer/events/register", json={
            "customer_id": seed_student.id,
            "customer_name": "只有名字",
        }, headers=auth_headers_student)
        assert resp.status_code == 422

    def test_missing_customer_name_422(self, client, seed_student, auth_headers_student):
        resp = client.post("/api/customer/events/register", json={
            "event_id": 1,
            "customer_id": seed_student.id,
        }, headers=auth_headers_student)
        assert resp.status_code == 422

    def test_missing_customer_id_422(self, client, seed_event, auth_headers_student):
        """customer_id 改为必填后，缺失应返回 422。"""
        resp = client.post("/api/customer/events/register", json={
            "event_id": seed_event.id,
            "customer_name": "没ID",
        }, headers=auth_headers_student)
        assert resp.status_code == 422

    def test_empty_customer_name(self, client, seed_event, seed_student, auth_headers_student):
        resp = client.post("/api/customer/events/register", json={
            "event_id": seed_event.id,
            "customer_id": seed_student.id,
            "customer_name": "",
        }, headers=auth_headers_student)
        assert resp.status_code == 200

    def test_sql_injection_name(self, client, seed_event, seed_student, auth_headers_student):
        inj = make_sql_injection_payload()
        resp = client.post("/api/customer/events/register", json={
            "event_id": seed_event.id,
            "customer_id": seed_student.id,
            "customer_name": inj["customer_name"],
        }, headers=auth_headers_student)
        assert resp.status_code == 200

    def test_auth_required_401(self, client, seed_student):
        resp = client.post("/api/customer/events/register", json={
            "event_id": 1,
            "customer_id": seed_student.id,
            "customer_name": "test",
        })
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# GET /api/customer/events/{event_id}/registrations  (公开接口)
# ══════════════════════════════════════════════════════════════════════


class TestListEventRegistrations:
    def test_ok(self, client, seed_event):
        resp = client.get(f"/api/customer/events/{seed_event.id}/registrations")
        assert resp.status_code == 200
        assert "registrations" in resp.json()

    def test_empty_registrations(self, client, seed_event):
        resp = client.get(f"/api/customer/events/{seed_event.id}/registrations")
        assert resp.status_code == 200
        assert isinstance(resp.json()["registrations"], list)

    def test_invalid_event_id_422(self, client):
        resp = client.get("/api/customer/events/abc/registrations")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════
# GET /api/customer/projects  (公开接口)
# ══════════════════════════════════════════════════════════════════════


class TestListProjects:
    def test_ok(self, client, seed_project):
        resp = client.get("/api/customer/projects")
        assert resp.status_code == 200

    def test_filter_by_category(self, client, seed_project):
        resp = client.get("/api/customer/projects?category=新加坡-本科")
        assert resp.status_code == 200

    def test_empty_category(self, client):
        resp = client.get("/api/customer/projects?category=")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════
# POST /api/customer/profile-match  (公开接口)
# ══════════════════════════════════════════════════════════════════════


class TestProfileMatch:
    def test_ok_no_params(self, client):
        resp = client.post("/api/customer/profile-match")
        assert resp.status_code == 200

    def test_ok_with_params(self, client, seed_project):
        resp = client.post("/api/customer/profile-match?age=20&education=高中&intended_country=新加坡")
        assert resp.status_code == 200

    def test_invalid_age_type_422(self, client):
        resp = client.post("/api/customer/profile-match?age=abc")
        assert resp.status_code == 422

    def test_no_match_result(self, client):
        resp = client.post("/api/customer/profile-match?age=20&education=高中&intended_country=墨西哥")
        assert resp.status_code == 200
        assert "暂无" in resp.json().get("message", "")

    def test_sql_injection_education(self, client):
        inj = make_sql_injection_payload()
        resp = client.post(f"/api/customer/profile-match?education={inj['content']}")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════
# POST /api/customer/chat  (公开接口)
# ══════════════════════════════════════════════════════════════════════


class TestCustomerChat:
    def test_ok(self, client):
        with patch(
            "agents.customer_service.agent.CustomerServiceAgent.route_intent",
            return_value={"intent": "event_query", "response": "本月活动……", "confidence": 0.88},
        ):
            resp = client.post("/api/customer/chat", json={"message": "最近有什么活动？"})
        assert resp.status_code == 200

    def test_empty_message(self, client):
        with patch(
            "agents.customer_service.agent.CustomerServiceAgent.route_intent",
            return_value={"intent": "unknown", "response": "", "confidence": 0.0},
        ):
            resp = client.post("/api/customer/chat", json={"message": ""})
        assert resp.status_code == 200

    def test_special_chars(self, client):
        sp = make_special_chars_payload()
        with patch(
            "agents.customer_service.agent.CustomerServiceAgent.route_intent",
            return_value={"intent": "unknown", "response": "", "confidence": 0.0},
        ):
            resp = client.post("/api/customer/chat", json={"message": sp["customer_name"]})
        assert resp.status_code == 200
