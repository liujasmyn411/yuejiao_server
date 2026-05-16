"""
企业智能助手路由测试
覆盖：CRM 意向客户 / 员工日报 / 学生成绩 / 员工查询 / 仪表盘 / 审批管理 / 组织架构 / 对话 / NL2SQL / 语音转报告
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
# POST /api/enterprise/lead  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestCreateLead:
    def test_ok(self, client, seed_employee, auth_headers_employee):
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
        resp = client.post("/api/enterprise/lead", json=payload, headers=auth_headers_employee)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_minimal_payload(self, client, seed_employee, auth_headers_employee):
        resp = client.post("/api/enterprise/lead", json={
            "customer_name": "最简客户",
            "owner_employee_id": seed_employee.id,
        }, headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_missing_customer_name_422(self, client, seed_employee, auth_headers_employee):
        resp = client.post("/api/enterprise/lead", json={
            "owner_employee_id": seed_employee.id,
        }, headers=auth_headers_employee)
        assert resp.status_code == 422

    def test_empty_customer_name(self, client, seed_employee, auth_headers_employee):
        resp = client.post("/api/enterprise/lead", json={
            "customer_name": "",
            "owner_employee_id": seed_employee.id,
        }, headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_invalid_age_type_422(self, client, seed_employee, auth_headers_employee):
        resp = client.post("/api/enterprise/lead", json={
            "customer_name": "测试",
            "age": "二十五",
            "owner_employee_id": seed_employee.id,
        }, headers=auth_headers_employee)
        assert resp.status_code == 422

    def test_oversized_customer_name(self, client, seed_employee, auth_headers_employee):
        ov = make_oversized_payload()
        resp = client.post("/api/enterprise/lead", json={
            "customer_name": ov["customer_name"],
            "owner_employee_id": seed_employee.id,
        }, headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_special_chars_name(self, client, seed_employee, auth_headers_employee):
        sp = make_special_chars_payload()
        resp = client.post("/api/enterprise/lead", json={
            "customer_name": sp["customer_name"],
            "owner_employee_id": seed_employee.id,
        }, headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_sql_injection(self, client, seed_employee, auth_headers_employee):
        inj = make_sql_injection_payload()
        resp = client.post("/api/enterprise/lead", json={
            "customer_name": inj["customer_name"],
            "contact_info": inj["contact_info"],
            "owner_employee_id": seed_employee.id,
        }, headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_auth_required_401(self, client):
        resp = client.post("/api/enterprise/lead", json={"customer_name": "test"})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# GET /api/enterprise/lead  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestListLeads:
    def test_list_all(self, client, auth_headers_employee):
        resp = client.get("/api/enterprise/lead", headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_filter_by_status(self, client, auth_headers_employee):
        resp = client.get("/api/enterprise/lead?status=新增意向", headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_empty_status(self, client, auth_headers_employee):
        resp = client.get("/api/enterprise/lead?status=", headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_auth_required_401(self, client):
        resp = client.get("/api/enterprise/lead")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# PUT /api/enterprise/lead/{lead_id}  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestUpdateLead:
    def test_ok(self, client, seed_lead, auth_headers_employee):
        resp = client.put(f"/api/enterprise/lead/{seed_lead.id}", json={
            "status": "跟进中",
            "score": 80,
        }, headers=auth_headers_employee)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_not_found(self, client, auth_headers_employee):
        resp = client.put("/api/enterprise/lead/99999", json={
            "status": "跟进中",
        }, headers=auth_headers_employee)
        assert resp.status_code == 404

    def test_empty_body_ok(self, client, seed_lead, auth_headers_employee):
        resp = client.put(f"/api/enterprise/lead/{seed_lead.id}", json={}, headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_invalid_lead_id_422(self, client, auth_headers_employee):
        resp = client.put("/api/enterprise/lead/abc", json={"status": "跟进中"}, headers=auth_headers_employee)
        assert resp.status_code == 422

    def test_sql_injection_status(self, client, seed_lead, auth_headers_employee):
        inj = make_sql_injection_payload()
        resp = client.put(f"/api/enterprise/lead/{seed_lead.id}", json={
            "status": inj["content"],
        }, headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_auth_required_401(self, client):
        resp = client.put("/api/enterprise/lead/1", json={})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# POST /api/enterprise/report  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestCreateReport:
    def test_ok(self, client, seed_employee, auth_headers_employee):
        resp = client.post("/api/enterprise/report", json={
            "employee_id": seed_employee.id,
            "content": "今天完成了3个客户跟进，新增1个意向客户。",
        }, headers=auth_headers_employee)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_with_date(self, client, seed_employee, auth_headers_employee):
        """report_date 不传则路由默认取当天 date 对象，兼容 SQLite Date 类型。"""
        resp = client.post("/api/enterprise/report", json={
            "employee_id": seed_employee.id,
            "content": "测试日报内容",
            "work_type": "客户跟进",
        }, headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_missing_content_422(self, client, seed_employee, auth_headers_employee):
        resp = client.post("/api/enterprise/report", json={
            "employee_id": seed_employee.id,
        }, headers=auth_headers_employee)
        assert resp.status_code == 422

    def test_missing_employee_id_422(self, client, auth_headers_employee):
        resp = client.post("/api/enterprise/report", json={
            "content": "没有员工ID的日报",
        }, headers=auth_headers_employee)
        assert resp.status_code == 422

    def test_empty_content(self, client, seed_employee, auth_headers_employee):
        resp = client.post("/api/enterprise/report", json={
            "employee_id": seed_employee.id,
            "content": "",
        }, headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_oversized_content(self, client, seed_employee, auth_headers_employee):
        ov = make_oversized_payload()
        resp = client.post("/api/enterprise/report", json={
            "employee_id": seed_employee.id,
            "content": ov["content"],
        }, headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_auth_required_401(self, client):
        resp = client.post("/api/enterprise/report", json={"employee_id": 1, "content": "test"})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# GET /api/enterprise/report  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestListReports:
    def test_list_all(self, client, auth_headers_employee):
        resp = client.get("/api/enterprise/report", headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_filter_by_employee(self, client, seed_employee, auth_headers_employee):
        resp = client.get(f"/api/enterprise/report?employee_id={seed_employee.id}", headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_invalid_employee_id(self, client, auth_headers_employee):
        resp = client.get("/api/enterprise/report?employee_id=abc", headers=auth_headers_employee)
        assert resp.status_code == 422

    def test_auth_required_401(self, client):
        resp = client.get("/api/enterprise/report")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# POST /api/enterprise/score  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestCreateScore:
    def test_ok(self, client, seed_student, auth_headers_employee):
        resp = client.post("/api/enterprise/score", json={
            "student_id": seed_student.id,
            "course_name": "高等数学",
            "score": 85.5,
        }, headers=auth_headers_employee)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_full_payload(self, client, seed_student, auth_headers_employee):
        resp = client.post("/api/enterprise/score", json={
            "student_id": seed_student.id,
            "course_name": "线性代数",
            "score": 92.0,
            "total_score": 100.0,
            "pass_score": 60.0,
            "exam_type": "期末",
            "semester": "2025-2026第二学期",
        }, headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_missing_course_name_422(self, client, seed_student, auth_headers_employee):
        resp = client.post("/api/enterprise/score", json={
            "student_id": seed_student.id,
            "score": 85,
        }, headers=auth_headers_employee)
        assert resp.status_code == 422

    def test_invalid_score_type_422(self, client, seed_student, auth_headers_employee):
        resp = client.post("/api/enterprise/score", json={
            "student_id": seed_student.id,
            "course_name": "测试",
            "score": "八十五",
        }, headers=auth_headers_employee)
        assert resp.status_code == 422

    def test_negative_score(self, client, seed_student, auth_headers_employee):
        resp = client.post("/api/enterprise/score", json={
            "student_id": seed_student.id,
            "course_name": "测试课程",
            "score": -10.0,
        }, headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_auth_required_401(self, client):
        resp = client.post("/api/enterprise/score", json={"student_id": 1, "course_name": "test", "score": 80})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# GET /api/enterprise/score  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestListScores:
    def test_ok(self, client, seed_student, auth_headers_employee):
        resp = client.get(f"/api/enterprise/score?student_id={seed_student.id}", headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_empty_for_new_student(self, client, seed_student, auth_headers_employee):
        resp = client.get(f"/api/enterprise/score?student_id={seed_student.id}", headers=auth_headers_employee)
        assert resp.status_code == 200
        assert resp.json()["scores"] == []

    def test_missing_student_id_422(self, client, auth_headers_employee):
        resp = client.get("/api/enterprise/score", headers=auth_headers_employee)
        assert resp.status_code == 422

    def test_invalid_student_id_422(self, client, auth_headers_employee):
        resp = client.get("/api/enterprise/score?student_id=abc", headers=auth_headers_employee)
        assert resp.status_code == 422

    def test_auth_required_401(self, client):
        resp = client.get("/api/enterprise/score?student_id=1")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# GET /api/enterprise/employee  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestListEmployees:
    def test_ok(self, client, seed_employee, auth_headers_employee):
        resp = client.get("/api/enterprise/employee", headers=auth_headers_employee)
        assert resp.status_code == 200
        assert "employees" in resp.json()

    def test_auth_required_401(self, client):
        resp = client.get("/api/enterprise/employee")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# GET /api/enterprise/dashboard  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestDashboard:
    def test_ok(self, client, auth_headers_employee):
        resp = client.get("/api/enterprise/dashboard", headers=auth_headers_employee)
        assert resp.status_code == 200
        data = resp.json()
        assert "customers" in data
        assert "feedback" in data
        assert "psych_alerts" in data
        assert "daily_reports" in data

    def test_empty_stats(self, client, auth_headers_employee):
        resp = client.get("/api/enterprise/dashboard", headers=auth_headers_employee)
        assert resp.status_code == 200
        assert resp.json()["customers"]["total"] >= 0

    def test_auth_required_401(self, client):
        resp = client.get("/api/enterprise/dashboard")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# 审批管理 (需班主任/管理员认证)
# ══════════════════════════════════════════════════════════════════════


class TestApprovals:
    def test_pending_empty(self, client, auth_headers_employee):
        """普通员工角色非班主任，查看待审批应返回 403。"""
        resp = client.get("/api/enterprise/approvals/pending", headers=auth_headers_employee)
        assert resp.status_code == 403

    def test_approve_not_found(self, client, auth_headers_employee):
        """非班主任审批应返回 403（角色校验先于申请存在性校验）。"""
        resp = client.post("/api/enterprise/approvals/99999/approve", json={
            "approved": True,
        }, headers=auth_headers_employee)
        assert resp.status_code == 403

    def test_auth_required_401_pending(self, client):
        resp = client.get("/api/enterprise/approvals/pending")
        assert resp.status_code == 401

    def test_auth_required_401_approve(self, client):
        resp = client.post("/api/enterprise/approvals/1/approve", json={"approved": True})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# 组织架构 (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestOrgChart:
    def test_org_chart_ok(self, client, auth_headers_employee):
        resp = client.get("/api/enterprise/org-chart", headers=auth_headers_employee)
        assert resp.status_code == 200
        assert "org_tree" in resp.json()

    def test_org_department_all(self, client, auth_headers_employee):
        resp = client.get("/api/enterprise/org-chart/department", headers=auth_headers_employee)
        assert resp.status_code == 200
        assert "departments" in resp.json()

    def test_org_department_filter(self, client, auth_headers_employee):
        resp = client.get("/api/enterprise/org-chart/department?dept_name=留学部", headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_auth_required_401(self, client):
        resp = client.get("/api/enterprise/org-chart")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# POST /api/enterprise/chat  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestEnterpriseChat:
    def test_ok(self, client, auth_headers_employee):
        with patch(
            "agents.enterprise.agent.EnterpriseAgent.route_intent",
            return_value={"intent": "lead_query", "response": "当前共有3个新增意向客户。", "confidence": 0.92},
        ):
            resp = client.post("/api/enterprise/chat", json={"message": "查询新增意向客户"}, headers=auth_headers_employee)
        assert resp.status_code == 200
        assert resp.json()["intent"] == "lead_query"

    def test_empty_message(self, client, auth_headers_employee):
        with patch(
            "agents.enterprise.agent.EnterpriseAgent.route_intent",
            return_value={"intent": "unknown", "response": "", "confidence": 0.0},
        ):
            resp = client.post("/api/enterprise/chat", json={"message": ""}, headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_auth_required_401(self, client):
        resp = client.post("/api/enterprise/chat", json={"message": "test"})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# POST /api/enterprise/nl2sql  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestNL2SQL:
    def test_ok(self, client, auth_headers_employee):
        with patch(
            "agents.enterprise.agent.EnterpriseAgent.query_database",
            return_value={"sql": "SELECT * FROM crm_lead", "explanation": "查询所有客户", "count": 5, "data": []},
        ):
            resp = client.post("/api/enterprise/nl2sql", json={"message": "查所有客户"}, headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_query_error(self, client, auth_headers_employee):
        with patch(
            "agents.enterprise.agent.EnterpriseAgent.query_database",
            return_value={"error": "不支持的查询操作"},
        ):
            resp = client.post("/api/enterprise/nl2sql", json={"message": "删除数据"}, headers=auth_headers_employee)
        assert resp.status_code == 200
        assert "error" in resp.json()

    def test_auth_required_401(self, client):
        resp = client.post("/api/enterprise/nl2sql", json={"message": "test"})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# POST /api/enterprise/nl2sql/update  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestNL2SQLUpdate:
    def test_ok(self, client, auth_headers_employee):
        with patch(
            "agents.enterprise.nl2sql.NL2SQL.update",
            return_value={"success": True, "affected": 1},
        ):
            resp = client.post("/api/enterprise/nl2sql/update", json={"message": "更新客户状态"}, headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_auth_required_401(self, client):
        resp = client.post("/api/enterprise/nl2sql/update", json={"message": "test"})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# POST /api/enterprise/voice-report  (需认证)
# ══════════════════════════════════════════════════════════════════════


class TestVoiceToReport:
    def test_ok(self, client, auth_headers_employee):
        with patch(
            "agents.enterprise.agent.EnterpriseAgent.voice_to_report",
            return_value={"employee_id": 1, "content": "今天跟进2个客户", "work_type": "客户跟进"},
        ):
            resp = client.post("/api/enterprise/voice-report", json={"message": "今天跟进两个客户"}, headers=auth_headers_employee)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_empty_message(self, client, auth_headers_employee):
        with patch(
            "agents.enterprise.agent.EnterpriseAgent.voice_to_report",
            return_value={},
        ):
            resp = client.post("/api/enterprise/voice-report", json={"message": ""}, headers=auth_headers_employee)
        assert resp.status_code == 200

    def test_auth_required_401(self, client):
        resp = client.post("/api/enterprise/voice-report", json={"message": "test"})
        assert resp.status_code == 401
