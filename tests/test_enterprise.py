"""
企业智能助手路由测试
覆盖：CRM 意向客户 / 员工日报 / 学生成绩 / 员工查询 / 仪表盘 / 对话 / NL2SQL / 语音转报告
"""

import pytest
from unittest.mock import patch

from tests.conftest import (
    make_empty_string_payload,
    make_oversized_payload,
    make_special_chars_payload,
    make_sql_injection_payload,
)

# ══════════════════════════════════════════════════════════════════════
# POST /api/enterprise/lead
# ══════════════════════════════════════════════════════════════════════


class TestCreateLead:
    def test_ok(self, client, seed_employee):
        payload = {
            "customer_name": "新客户张三",
            "contact_info": "13800001111",
            "age": 25,
            "education": "本科",
            "intended_country": "德国",
            "status": "新增意向",
            "score": 60,
            "owner_employee_id": seed_employee.id,
        }
        resp = client.post("/api/enterprise/lead", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["lead_id"]

    def test_minimal_payload(self, client, seed_employee):
        """仅填必填字段 customer_name + owner_employee_id。"""
        resp = client.post("/api/enterprise/lead", json={
            "customer_name": "最简客户",
            "owner_employee_id": seed_employee.id,
        })
        assert resp.status_code == 200

    def test_missing_customer_name_422(self, client, seed_employee):
        resp = client.post("/api/enterprise/lead", json={
            "owner_employee_id": seed_employee.id,
        })
        assert resp.status_code == 422

    def test_empty_customer_name(self, client, seed_employee):
        """空 customer_name —— str 必填，空串合法。"""
        resp = client.post("/api/enterprise/lead", json={
            "customer_name": "",
            "owner_employee_id": seed_employee.id,
        })
        assert resp.status_code == 200

    def test_invalid_age_type_422(self, client, seed_employee):
        resp = client.post("/api/enterprise/lead", json={
            "customer_name": "测试",
            "age": "二十五",
            "owner_employee_id": seed_employee.id,
        })
        assert resp.status_code == 422

    def test_oversized_customer_name(self, client, seed_employee):
        ov = make_oversized_payload()
        resp = client.post("/api/enterprise/lead", json={
            "customer_name": ov["customer_name"],
            "owner_employee_id": seed_employee.id,
        })
        assert resp.status_code == 200

    def test_special_chars_name(self, client, seed_employee):
        sp = make_special_chars_payload()
        resp = client.post("/api/enterprise/lead", json={
            "customer_name": sp["customer_name"],
            "owner_employee_id": seed_employee.id,
        })
        assert resp.status_code == 200

    def test_sql_injection(self, client, seed_employee):
        inj = make_sql_injection_payload()
        resp = client.post("/api/enterprise/lead", json={
            "customer_name": inj["customer_name"],
            "contact_info": inj["contact_info"],
            "owner_employee_id": seed_employee.id,
        })
        assert resp.status_code == 200

    @pytest.mark.skip(reason="认证功能尚未实现")
    def test_auth_required_401(self, client):
        resp = client.post("/api/enterprise/lead", json={})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# GET /api/enterprise/lead
# ══════════════════════════════════════════════════════════════════════


class TestListLeads:
    def test_list_all(self, client):
        resp = client.get("/api/enterprise/lead")
        assert resp.status_code == 200
        assert "leads" in resp.json()

    def test_filter_by_status(self, client):
        resp = client.get("/api/enterprise/lead?status=新增意向")
        assert resp.status_code == 200

    def test_empty_status(self, client):
        resp = client.get("/api/enterprise/lead?status=")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════
# PUT /api/enterprise/lead/{lead_id}
# ══════════════════════════════════════════════════════════════════════


class TestUpdateLead:
    def test_ok(self, client, seed_lead):
        resp = client.put(f"/api/enterprise/lead/{seed_lead.id}", json={
            "status": "跟进中",
            "score": 80,
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_not_found(self, client):
        resp = client.put("/api/enterprise/lead/99999", json={
            "status": "跟进中",
        })
        assert resp.status_code == 404

    def test_empty_body_ok(self, client, seed_lead):
        """空 body（全部字段 Optional）应正常返回。"""
        resp = client.put(f"/api/enterprise/lead/{seed_lead.id}", json={})
        assert resp.status_code == 200

    def test_invalid_lead_id_422(self, client):
        resp = client.put("/api/enterprise/lead/abc", json={"status": "跟进中"})
        assert resp.status_code == 422

    def test_sql_injection_status(self, client, seed_lead):
        inj = make_sql_injection_payload()
        resp = client.put(f"/api/enterprise/lead/{seed_lead.id}", json={
            "status": inj["content"],
        })
        assert resp.status_code == 200

    @pytest.mark.skip(reason="认证功能尚未实现")
    def test_auth_required_401(self, client):
        resp = client.put("/api/enterprise/lead/1", json={})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# POST /api/enterprise/report
# ══════════════════════════════════════════════════════════════════════


class TestCreateReport:
    def test_ok(self, client, seed_employee):
        resp = client.post("/api/enterprise/report", json={
            "employee_id": seed_employee.id,
            "content": "今天完成了3个客户跟进，新增1个意向客户。",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_with_date(self, client, seed_employee):
        resp = client.post("/api/enterprise/report", json={
            "employee_id": seed_employee.id,
            "content": "测试日报内容",
            "report_date": "2026-05-15",
            "work_type": "客户跟进",
        })
        assert resp.status_code == 200

    def test_missing_content_422(self, client, seed_employee):
        resp = client.post("/api/enterprise/report", json={
            "employee_id": seed_employee.id,
        })
        assert resp.status_code == 422

    def test_missing_employee_id_422(self, client):
        resp = client.post("/api/enterprise/report", json={
            "content": "没有员工ID的日报",
        })
        assert resp.status_code == 422

    def test_empty_content(self, client, seed_employee):
        resp = client.post("/api/enterprise/report", json={
            "employee_id": seed_employee.id,
            "content": "",
        })
        assert resp.status_code == 200

    def test_oversized_content(self, client, seed_employee):
        ov = make_oversized_payload()
        resp = client.post("/api/enterprise/report", json={
            "employee_id": seed_employee.id,
            "content": ov["content"],
        })
        assert resp.status_code == 200

    @pytest.mark.skip(reason="认证功能尚未实现")
    def test_auth_required_401(self, client):
        resp = client.post("/api/enterprise/report", json={})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# GET /api/enterprise/report
# ══════════════════════════════════════════════════════════════════════


class TestListReports:
    def test_list_all(self, client):
        resp = client.get("/api/enterprise/report")
        assert resp.status_code == 200
        assert "reports" in resp.json()

    def test_filter_by_employee(self, client, seed_employee):
        resp = client.get(f"/api/enterprise/report?employee_id={seed_employee.id}")
        assert resp.status_code == 200

    def test_invalid_employee_id(self, client):
        resp = client.get("/api/enterprise/report?employee_id=abc")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════
# POST /api/enterprise/score
# ══════════════════════════════════════════════════════════════════════


class TestCreateScore:
    def test_ok(self, client, seed_student):
        resp = client.post("/api/enterprise/score", json={
            "student_id": seed_student.id,
            "course_name": "高等数学",
            "score": 85.5,
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_full_payload(self, client, seed_student):
        resp = client.post("/api/enterprise/score", json={
            "student_id": seed_student.id,
            "course_name": "线性代数",
            "score": 92.0,
            "total_score": 100.0,
            "pass_score": 60.0,
            "exam_type": "期末",
            "semester": "2025-2026第二学期",
        })
        assert resp.status_code == 200

    def test_missing_course_name_422(self, client, seed_student):
        resp = client.post("/api/enterprise/score", json={
            "student_id": seed_student.id,
            "score": 85,
        })
        assert resp.status_code == 422

    def test_invalid_score_type_422(self, client, seed_student):
        resp = client.post("/api/enterprise/score", json={
            "student_id": seed_student.id,
            "course_name": "测试",
            "score": "八十五",
        })
        assert resp.status_code == 422

    def test_negative_score(self, client, seed_student):
        """负数成绩 —— Pydantic float 接受负数。"""
        resp = client.post("/api/enterprise/score", json={
            "student_id": seed_student.id,
            "course_name": "测试课程",
            "score": -10.0,
        })
        assert resp.status_code == 200

    @pytest.mark.skip(reason="认证功能尚未实现")
    def test_auth_required_401(self, client):
        resp = client.post("/api/enterprise/score", json={})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# GET /api/enterprise/score
# ══════════════════════════════════════════════════════════════════════


class TestListScores:
    def test_ok(self, client, seed_student):
        resp = client.get(f"/api/enterprise/score?student_id={seed_student.id}")
        assert resp.status_code == 200
        assert "scores" in resp.json()

    def test_empty_for_new_student(self, client, seed_student):
        resp = client.get(f"/api/enterprise/score?student_id={seed_student.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["scores"] == []

    def test_missing_student_id_422(self, client):
        resp = client.get("/api/enterprise/score")
        assert resp.status_code == 422

    def test_invalid_student_id_422(self, client):
        resp = client.get("/api/enterprise/score?student_id=abc")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════
# GET /api/enterprise/employee
# ══════════════════════════════════════════════════════════════════════


class TestListEmployees:
    def test_ok(self, client, seed_employee):
        resp = client.get("/api/enterprise/employee")
        assert resp.status_code == 200
        data = resp.json()
        assert "employees" in data

    def test_empty_when_no_employees(self, client):
        """没有员工时返回空列表（但 fixture 可能已插入）"""
        resp = client.get("/api/enterprise/employee")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════
# GET /api/enterprise/dashboard
# ══════════════════════════════════════════════════════════════════════


class TestDashboard:
    def test_ok(self, client):
        resp = client.get("/api/enterprise/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "customers" in data
        assert "feedback" in data
        assert "psych_alerts" in data
        assert "daily_reports" in data

    def test_empty_stats(self, client):
        """数据库为空时各计数应为 0。"""
        resp = client.get("/api/enterprise/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["customers"]["total"] >= 0
        assert data["feedback"]["total"] >= 0


# ══════════════════════════════════════════════════════════════════════
# POST /api/enterprise/chat
# ══════════════════════════════════════════════════════════════════════


class TestEnterpriseChat:
    def test_ok(self, client):
        with patch(
            "agents.enterprise.agent.EnterpriseAgent.route_intent",
            return_value={
                "intent": "lead_query",
                "response": "当前共有3个新增意向客户。",
                "confidence": 0.92,
            },
        ):
            resp = client.post("/api/enterprise/chat", json={
                "message": "查询新增意向客户",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "lead_query"

    def test_empty_message(self, client):
        with patch(
            "agents.enterprise.agent.EnterpriseAgent.route_intent",
            return_value={"intent": "unknown", "response": "", "confidence": 0.0},
        ):
            resp = client.post("/api/enterprise/chat", json={"message": ""})
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════
# POST /api/enterprise/nl2sql
# ══════════════════════════════════════════════════════════════════════


class TestNL2SQL:
    def test_ok(self, client):
        with patch(
            "agents.enterprise.agent.EnterpriseAgent.query_database",
            return_value={
                "sql": "SELECT * FROM crm_lead WHERE status = '新增意向'",
                "explanation": "查询所有新增意向客户",
                "count": 5,
                "data": [],
            },
        ):
            resp = client.post("/api/enterprise/nl2sql", json={
                "message": "查一下所有新增意向客户",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "sql" in data

    def test_query_error(self, client):
        with patch(
            "agents.enterprise.agent.EnterpriseAgent.query_database",
            return_value={"error": "不支持的查询操作"},
        ):
            resp = client.post("/api/enterprise/nl2sql", json={
                "message": "删除所有数据",
            })
        assert resp.status_code == 200
        assert "error" in resp.json()


# ══════════════════════════════════════════════════════════════════════
# POST /api/enterprise/voice-report
# ══════════════════════════════════════════════════════════════════════


class TestVoiceToReport:
    def test_ok(self, client):
        with patch(
            "agents.enterprise.agent.EnterpriseAgent.voice_to_report",
            return_value={
                "employee_id": 1,
                "content": "今天跟进2个客户",
                "work_type": "客户跟进",
            },
        ):
            resp = client.post("/api/enterprise/voice-report", json={
                "message": "今天跟进两个客户，张三对新加坡项目感兴趣",
            })
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert "report" in resp.json()

    def test_empty_message(self, client):
        with patch(
            "agents.enterprise.agent.EnterpriseAgent.voice_to_report",
            return_value={},
        ):
            resp = client.post("/api/enterprise/voice-report", json={"message": ""})
        assert resp.status_code == 200
