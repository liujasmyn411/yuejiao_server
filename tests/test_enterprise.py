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


# ══════════════════════════════════════════════════════════════════════
# P1: 待处理事项主动询问
# ══════════════════════════════════════════════════════════════════════


class TestActivePendingReminder:
    """员工闲聊时，系统主动检测待办并询问"""

    def test_chitchat_shows_pending_summary(self, db_session, seed_employee, seed_student):
        """有待办时，闲聊回复主动附加待办提醒"""
        from agents.enterprise.agent import EnterpriseAgent
        from model import StudentFeedbackTicket, StudentAdminService

        # 构造待办数据
        db_session.add(StudentFeedbackTicket(student_id=seed_student.id, content="测试投诉", status="待处理"))
        db_session.add(StudentAdminService(student_id=seed_student.id, service_type="请假", status="待审批"))
        db_session.commit()

        agent = EnterpriseAgent()
        with patch("agents.enterprise.agent.get_llm_client") as mock_llm:
            mock_llm.return_value.chat.return_value = "你好！有什么可以帮你的？"
            resp = agent._handle_chitchat("你好", {}, db_session, seed_employee.id)

        assert "待处理事项" in resp
        assert "1 条投诉/反馈工单待跟进" in resp
        assert "1 条请假申请待审批" in resp
        assert "处理投诉" in resp
        assert "审批请假" in resp

    def test_chitchat_no_pending_no_reminder(self, db_session, seed_employee):
        """无待办时，闲聊不附加提醒"""
        from agents.enterprise.agent import EnterpriseAgent

        agent = EnterpriseAgent()
        with patch("agents.enterprise.agent.get_llm_client") as mock_llm:
            mock_llm.return_value.chat.return_value = "你好！有什么可以帮你的？"
            resp = agent._handle_chitchat("你好", {}, db_session, seed_employee.id)

        assert "待处理事项" not in resp

    def test_quick_route_handle_complaint(self, db_session, seed_employee, seed_student):
        """快捷路由：处理投诉直接列出待处理工单"""
        from agents.enterprise.agent import EnterpriseAgent
        from model import StudentFeedbackTicket

        db_session.add(StudentFeedbackTicket(student_id=seed_student.id, content="测试投诉内容", status="待处理"))
        db_session.commit()

        agent = EnterpriseAgent()
        result = agent._quick_route("处理投诉", db=db_session, user_id=seed_employee.id)
        assert result is not None
        assert "待处理投诉" in result[1]
        assert "测试投诉" in result[1]

    def test_quick_route_approve_leave(self, db_session, seed_employee, seed_student):
        """快捷路由：审批请假直接列出待审批请假"""
        from agents.enterprise.agent import EnterpriseAgent
        from model import StudentAdminService

        db_session.add(StudentAdminService(student_id=seed_student.id, service_type="请假", status="待审批"))
        db_session.commit()

        agent = EnterpriseAgent()
        result = agent._quick_route("审批请假", db=db_session, user_id=seed_employee.id)
        assert result is not None
        assert "待审批请假" in result[1]


# ══════════════════════════════════════════════════════════════════════
# P2: 自然语言指令解析增强
# ══════════════════════════════════════════════════════════════════════


class TestNaturalLanguageCommand:
    """自然语言指令解析：审批同义词 + 工单状态更新"""

    def test_ticket_update_by_student_name(self, db_session, seed_employee, seed_student):
        """按学生姓名更新投诉状态"""
        from agents.enterprise.agent import EnterpriseAgent
        from model import StudentFeedbackTicket

        db_session.add(StudentFeedbackTicket(student_id=seed_student.id, content="测试投诉内容", status="待处理"))
        db_session.commit()

        agent = EnterpriseAgent()
        with patch("agents.enterprise.agent.get_llm_client") as mock_llm:
            mock_llm.return_value.extract_info.return_value = {
                "学生姓名": "测试学生",
                "新状态": "已跟进",
            }
            resp = agent._handle_ticket_update("把测试学生的投诉状态更新为已跟进", {}, db_session, seed_employee.id)

        assert "状态已更新" in resp
        assert "已跟进" in resp
        assert "待处理" in resp  # 原状态

        # 验证数据库
        ticket = db_session.query(StudentFeedbackTicket).filter(
            StudentFeedbackTicket.student_id == seed_student.id
        ).first()
        assert ticket.status == "已跟进"
        assert ticket.handle_user_id == seed_employee.id

    def test_ticket_update_by_id(self, db_session, seed_employee, seed_student):
        """按工单编号更新状态"""
        from agents.enterprise.agent import EnterpriseAgent
        from model import StudentFeedbackTicket

        ticket = StudentFeedbackTicket(student_id=seed_student.id, content="测试投诉", status="待处理")
        db_session.add(ticket)
        db_session.commit()
        db_session.refresh(ticket)

        agent = EnterpriseAgent()
        with patch("agents.enterprise.agent.get_llm_client") as mock_llm:
            mock_llm.return_value.extract_info.return_value = {}
            resp = agent._handle_ticket_update(f"将投诉 #{ticket.id} 状态改为已解决", {}, db_session, seed_employee.id)

        assert "状态已更新" in resp
        assert "已解决" in resp

    def test_ticket_update_duplicate_status_blocked(self, db_session, seed_employee, seed_student):
        """重复更新同一状态应被拦截"""
        from agents.enterprise.agent import EnterpriseAgent
        from model import StudentFeedbackTicket

        db_session.add(StudentFeedbackTicket(student_id=seed_student.id, content="测试投诉", status="已跟进"))
        db_session.commit()

        agent = EnterpriseAgent()
        with patch("agents.enterprise.agent.get_llm_client") as mock_llm:
            mock_llm.return_value.extract_info.return_value = {"学生姓名": "测试学生", "新状态": "已跟进"}
            resp = agent._handle_ticket_update("把测试学生的投诉更新为已跟进", {}, db_session, seed_employee.id)

        assert "无需重复更新" in resp

    def test_ticket_update_invalid_status_rejected(self, db_session, seed_employee, seed_student):
        """无效状态应被拒绝"""
        from agents.enterprise.agent import EnterpriseAgent
        from model import StudentFeedbackTicket

        db_session.add(StudentFeedbackTicket(student_id=seed_student.id, content="测试投诉", status="待处理"))
        db_session.commit()

        agent = EnterpriseAgent()
        with patch("agents.enterprise.agent.get_llm_client") as mock_llm:
            mock_llm.return_value.extract_info.return_value = {"学生姓名": "测试学生", "新状态": "随便写"}
            resp = agent._handle_ticket_update("把测试学生的投诉更新为随便写", {}, db_session, seed_employee.id)

        assert "不支持的状态" in resp

    def test_quick_route_approve_synonyms(self, db_session, seed_employee, seed_student):
        """审批同义词：同意/批准/准予 均应触发审批路由"""
        from agents.enterprise.agent import EnterpriseAgent
        from model import StudentAdminService

        db_session.add(StudentAdminService(student_id=seed_student.id, service_type="请假", status="待审批"))
        db_session.commit()

        agent = EnterpriseAgent()
        for phrase in ["同意测试学生的请假", "批准测试学生的请假", "准予测试学生的请假"]:
            result = agent._quick_route(phrase, db=db_session, user_id=seed_employee.id)
            assert result is not None, f"'{phrase}' 应被识别为审批指令"
            assert result[0] == "approval"

    def test_quick_route_ticket_update(self, db_session, seed_employee, seed_student):
        """快捷路由：更新投诉状态指令直接命中 ticket_update"""
        from agents.enterprise.agent import EnterpriseAgent
        from model import StudentFeedbackTicket

        db_session.add(StudentFeedbackTicket(student_id=seed_student.id, content="测试投诉", status="待处理"))
        db_session.commit()

        agent = EnterpriseAgent()
        for phrase in ["把测试学生的投诉状态更新为已跟进", "修改测试学生的投诉为已解决"]:
            result = agent._quick_route(phrase, db=db_session, user_id=seed_employee.id)
            assert result is not None, f"'{phrase}' 应被识别为状态更新"
            assert result[0] == "ticket_update"
