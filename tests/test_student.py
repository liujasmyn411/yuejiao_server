"""
学生智能助手路由测试
覆盖：学生信息 / 请假 / 投诉反馈 / 心理预警 / 教务 / 留学进度 / 对话
"""

import pytest
from unittest.mock import patch
from datetime import datetime, date

from faker import Faker

fake = Faker("zh_CN")

# ══════════════════════════════════════════════════════════════════════
# GET /api/student/info  (公开接口，无需认证)
# ══════════════════════════════════════════════════════════════════════


class TestGetStudentInfo:
    def test_ok(self, client, seed_student):
        resp = client.get(f"/api/student/info?student_id={seed_student.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["real_name"] == seed_student.real_name

    def test_not_found(self, client):
        resp = client.get("/api/student/info?student_id=99999")
        assert resp.status_code == 404

    def test_employee_not_student(self, client, seed_employee):
        resp = client.get(f"/api/student/info?student_id={seed_employee.id}")
        assert resp.status_code == 404

    def test_missing_param_422(self, client):
        resp = client.get("/api/student/info")
        assert resp.status_code == 422

    def test_invalid_type_422(self, client):
        resp = client.get("/api/student/info?student_id=abc")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════
# POST /api/student/leave  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestCreateLeave:
    def test_ok(self, client, seed_student, auth_headers_student):
        payload = {
            "student_id": seed_student.id,
            "service_type": "请假",
            "leave_type": "事假",
            "start_time": "2026-06-01 09:00",
            "end_time": "2026-06-01 18:00",
            "reason": "家里有事",
        }
        resp = client.post("/api/student/leave", json=payload, headers=auth_headers_student)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_not_found_student(self, client, auth_headers_student):
        resp = client.post("/api/student/leave", json={
            "student_id": 99999,
            "service_type": "请假",
            "leave_type": "事假",
        }, headers=auth_headers_student)
        assert resp.status_code == 404

    def test_duplicate_submission_400(self, client, seed_student, auth_headers_student):
        payload = {
            "student_id": seed_student.id,
            "service_type": "请假",
            "leave_type": "病假",
            "start_time": "2026-07-10 08:00",
            "end_time": "2026-07-10 17:00",
            "reason": "身体不适",
        }
        resp1 = client.post("/api/student/leave", json=payload, headers=auth_headers_student)
        assert resp1.status_code == 200
        resp2 = client.post("/api/student/leave", json=payload, headers=auth_headers_student)
        assert resp2.status_code == 400
        assert "重复提交" in resp2.json()["detail"]

    def test_missing_required_fields_422(self, client, auth_headers_student):
        resp = client.post("/api/student/leave", json={}, headers=auth_headers_student)
        assert resp.status_code == 422

    def test_invalid_student_id_type_422(self, client, auth_headers_student):
        resp = client.post("/api/student/leave", json={
            "student_id": "不是数字",
            "service_type": "请假",
        }, headers=auth_headers_student)
        assert resp.status_code == 422

    def test_empty_reason(self, client, seed_student, auth_headers_student):
        resp = client.post("/api/student/leave", json={
            "student_id": seed_student.id,
            "service_type": "请假",
            "leave_type": "事假",
            "reason": "",
        }, headers=auth_headers_student)
        assert resp.status_code == 200

    def test_sql_injection_reason(self, client, seed_student, auth_headers_student):
        from tests.conftest import make_sql_injection_payload
        inj = make_sql_injection_payload()
        resp = client.post("/api/student/leave", json={
            "student_id": seed_student.id,
            "service_type": "请假",
            "leave_type": "事假",
            "reason": inj["reason"],
        }, headers=auth_headers_student)
        assert resp.status_code == 200

    def test_special_chars_reason(self, client, seed_student, auth_headers_student):
        from tests.conftest import make_special_chars_payload
        sp = make_special_chars_payload()
        resp = client.post("/api/student/leave", json={
            "student_id": seed_student.id,
            "service_type": "请假",
            "reason": sp["reason"],
        }, headers=auth_headers_student)
        assert resp.status_code == 200

    def test_auth_required_401(self, client):
        resp = client.post("/api/student/leave", json={"student_id": 1, "service_type": "请假"})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# GET /api/student/leave  (公开接口)
# ══════════════════════════════════════════════════════════════════════


class TestListLeaves:
    def test_list_all(self, client):
        resp = client.get("/api/student/leave")
        assert resp.status_code == 200
        assert "leaves" in resp.json()

    def test_filter_by_student(self, client, seed_student):
        resp = client.get(f"/api/student/leave?student_id={seed_student.id}")
        assert resp.status_code == 200

    def test_invalid_student_id_type(self, client):
        resp = client.get("/api/student/leave?student_id=abc")
        assert resp.status_code == 422

    def test_student_not_found(self, client):
        resp = client.get("/api/student/leave?student_id=99999")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════
# POST /api/student/feedback  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestCreateFeedback:
    def test_ok(self, client, seed_student, auth_headers_student):
        payload = {
            "student_id": seed_student.id,
            "content": "课程安排不合理",
            "feedback_type": "投诉",
            "urgency_level": "高",
        }
        resp = client.post("/api/student/feedback", json=payload, headers=auth_headers_student)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "ticket_id" in data

    def test_minimal_payload(self, client, seed_student, auth_headers_student):
        resp = client.post("/api/student/feedback", json={
            "student_id": seed_student.id,
            "content": "测试反馈",
        }, headers=auth_headers_student)
        assert resp.status_code == 200

    def test_not_found_student(self, client, auth_headers_student):
        resp = client.post("/api/student/feedback", json={
            "student_id": 99999,
            "content": "测试内容",
        }, headers=auth_headers_student)
        assert resp.status_code == 404

    def test_missing_content_422(self, client, seed_student, auth_headers_student):
        resp = client.post("/api/student/feedback", json={
            "student_id": seed_student.id,
        }, headers=auth_headers_student)
        assert resp.status_code == 422

    def test_missing_student_id_422(self, client, auth_headers_student):
        resp = client.post("/api/student/feedback", json={
            "content": "没有学生的反馈",
        }, headers=auth_headers_student)
        assert resp.status_code == 422

    def test_empty_content(self, client, seed_student, auth_headers_student):
        resp = client.post("/api/student/feedback", json={
            "student_id": seed_student.id,
            "content": "",
        }, headers=auth_headers_student)
        assert resp.status_code == 200

    def test_oversized_content(self, client, seed_student, auth_headers_student):
        from tests.conftest import make_oversized_payload
        ov = make_oversized_payload()
        resp = client.post("/api/student/feedback", json={
            "student_id": seed_student.id,
            "content": ov["content"],
        }, headers=auth_headers_student)
        assert resp.status_code == 200

    def test_sql_injection(self, client, seed_student, auth_headers_student):
        from tests.conftest import make_sql_injection_payload
        inj = make_sql_injection_payload()
        resp = client.post("/api/student/feedback", json={
            "student_id": seed_student.id,
            "content": inj["content"],
        }, headers=auth_headers_student)
        assert resp.status_code == 200

    def test_auth_required_401(self, client):
        resp = client.post("/api/student/feedback", json={"student_id": 1, "content": "test"})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# GET /api/student/feedback  (公开接口)
# ══════════════════════════════════════════════════════════════════════


class TestListFeedback:
    def test_list_all(self, client):
        resp = client.get("/api/student/feedback")
        assert resp.status_code == 200

    def test_filter_by_student(self, client, seed_student):
        resp = client.get(f"/api/student/feedback?student_id={seed_student.id}")
        assert resp.status_code == 200

    def test_invalid_type_422(self, client):
        resp = client.get("/api/student/feedback?student_id=abc")
        assert resp.status_code == 422

    def test_student_not_found(self, client):
        resp = client.get("/api/student/feedback?student_id=99999")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════
# POST /api/student/psych-alert  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestCreatePsychAlert:
    def test_ok_high_risk(self, client, seed_student, auth_headers_student):
        resp = client.post("/api/student/psych-alert", json={
            "student_id": seed_student.id,
            "trigger_reason": "学生连续3天未回复消息",
            "risk_level": "high",
        }, headers=auth_headers_student)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_ok_low_risk(self, client, seed_student, auth_headers_student):
        resp = client.post("/api/student/psych-alert", json={
            "student_id": seed_student.id,
            "trigger_reason": "学生表达轻微焦虑",
            "risk_level": "low",
        }, headers=auth_headers_student)
        assert resp.status_code == 200

    def test_invalid_risk_level_422(self, client, seed_student, auth_headers_student):
        resp = client.post("/api/student/psych-alert", json={
            "student_id": seed_student.id,
            "risk_level": "critical",
        }, headers=auth_headers_student)
        assert resp.status_code == 422

    def test_missing_risk_level_422(self, client, seed_student, auth_headers_student):
        resp = client.post("/api/student/psych-alert", json={
            "student_id": seed_student.id,
        }, headers=auth_headers_student)
        assert resp.status_code == 422

    def test_not_found_student(self, client, auth_headers_student):
        resp = client.post("/api/student/psych-alert", json={
            "student_id": 99999,
            "risk_level": "medium",
        }, headers=auth_headers_student)
        assert resp.status_code == 404

    def test_auth_required_401(self, client):
        resp = client.post("/api/student/psych-alert", json={"student_id": 1, "risk_level": "low"})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# GET /api/student/psych-alert  (公开接口)
# ══════════════════════════════════════════════════════════════════════


class TestListPsychAlerts:
    def test_list_all(self, client):
        resp = client.get("/api/student/psych-alert")
        assert resp.status_code == 200

    def test_filter_by_risk_level(self, client):
        resp = client.get("/api/student/psych-alert?risk_level=high")
        assert resp.status_code == 200

    def test_invalid_risk_level_422(self, client):
        resp = client.get("/api/student/psych-alert?risk_level=unknown")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════
# GET /api/student/academic  (公开接口，有 _validate_student)
# ══════════════════════════════════════════════════════════════════════


class TestListAcademic:
    def test_ok(self, client, seed_student):
        resp = client.get(f"/api/student/academic?student_id={seed_student.id}")
        assert resp.status_code == 200

    def test_filter_by_type(self, client, seed_student):
        resp = client.get(f"/api/student/academic?student_id={seed_student.id}&academic_type=考试")
        assert resp.status_code == 200

    def test_missing_student_id_422(self, client):
        resp = client.get("/api/student/academic")
        assert resp.status_code == 422

    def test_invalid_student_id_422(self, client):
        resp = client.get("/api/student/academic?student_id=abc")
        assert resp.status_code == 422

    def test_not_found_student(self, client):
        resp = client.get("/api/student/academic?student_id=99999")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════
# GET /api/student/academic/upcoming  (公开接口)
# ══════════════════════════════════════════════════════════════════════


class TestListUpcomingAcademic:
    def test_ok(self, client, seed_student):
        resp = client.get(f"/api/student/academic/upcoming?student_id={seed_student.id}")
        assert resp.status_code == 200

    def test_custom_days(self, client, seed_student):
        resp = client.get(f"/api/student/academic/upcoming?student_id={seed_student.id}&days=30")
        assert resp.status_code == 200

    def test_invalid_days_422(self, client, seed_student):
        resp = client.get(f"/api/student/academic/upcoming?student_id={seed_student.id}&days=abc")
        assert resp.status_code == 422

    def test_missing_student_id_422(self, client):
        resp = client.get("/api/student/academic/upcoming")
        assert resp.status_code == 422

    def test_not_found_student(self, client):
        resp = client.get("/api/student/academic/upcoming?student_id=99999")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════
# GET /api/student/study-abroad  (公开接口)
# ══════════════════════════════════════════════════════════════════════


class TestListStudyAbroad:
    def test_ok_with_data(self, client, seed_student, db_session):
        from model import StudentStudyAbroadProgress

        progress = StudentStudyAbroadProgress(
            student_id=seed_student.id,
            target_country="英国",
            target_school="帝国理工学院",
            target_major="计算机科学",
            degree_level="硕士",
            stage="院校申请",
            stage_order=3,
            stage_status="进行中",
            stage_detail="已提交在线申请",
            estimated_complete_date=date(2026, 5, 30),
            is_current=1,
        )
        db_session.add(progress)
        db_session.flush()

        resp = client.get(f"/api/student/study-abroad?student_id={seed_student.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "progress" in data
        assert len(data["progress"]) >= 1

    def test_empty_progress(self, client, seed_student):
        resp = client.get(f"/api/student/study-abroad?student_id={seed_student.id}")
        assert resp.status_code == 200
        data = resp.json()
        if len(data.get("progress", [])) == 0:
            assert "暂无" in data.get("message", "")

    def test_missing_student_id_422(self, client):
        resp = client.get("/api/student/study-abroad")
        assert resp.status_code == 422

    def test_not_found_student(self, client):
        resp = client.get("/api/student/study-abroad?student_id=99999")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════
# GET /api/student/study-abroad/current  (公开接口)
# ══════════════════════════════════════════════════════════════════════


class TestGetCurrentStage:
    def test_no_current_stage(self, client, seed_student):
        resp = client.get(f"/api/student/study-abroad/current?student_id={seed_student.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "暂无" in data.get("message", "")

    def test_missing_student_id_422(self, client):
        resp = client.get("/api/student/study-abroad/current")
        assert resp.status_code == 422

    def test_not_found_student(self, client):
        resp = client.get("/api/student/study-abroad/current?student_id=99999")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════
# POST /api/student/chat  (公开接口)
# ══════════════════════════════════════════════════════════════════════


class TestStudentChat:
    def test_ok(self, client):
        with patch(
            "agents.student.agent.StudentAgent.route_intent",
            return_value={"intent": "chitchat", "response": "你好！", "confidence": 0.95},
        ):
            resp = client.post("/api/student/chat", json={"message": "你好", "student_id": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "chitchat"

    def test_empty_message(self, client):
        with patch(
            "agents.student.agent.StudentAgent.route_intent",
            return_value={"intent": "unknown", "response": "", "confidence": 0.0},
        ):
            resp = client.post("/api/student/chat", json={"message": ""})
        assert resp.status_code == 200

    def test_missing_body_422(self, client):
        resp = client.post("/api/student/chat", content=b"not json", headers={"Content-Type": "application/json"})
        assert resp.status_code == 422

    def test_special_chars_message(self, client):
        with patch(
            "agents.student.agent.StudentAgent.route_intent",
            return_value={"intent": "unknown", "response": "", "confidence": 0.0},
        ):
            resp = client.post("/api/student/chat", json={"message": "<script>alert('xss')</script>"})
        assert resp.status_code == 200
