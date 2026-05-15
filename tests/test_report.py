"""
智能报告路由测试
覆盖：管理仪表盘 / 客户分析 / 日报汇总 / 周报汇总 / 心理周报 / 投诉周报
"""

import pytest
from unittest.mock import patch


# ══════════════════════════════════════════════════════════════════════
# GET /api/reports/dashboard
# ══════════════════════════════════════════════════════════════════════


class TestReportDashboard:
    def test_ok(self, client):
        resp = client.get("/api/reports/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "customers" in data
        assert "feedback" in data

    def test_empty_data(self, client):
        resp = client.get("/api/reports/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["customers"]["total"] >= 0


# ══════════════════════════════════════════════════════════════════════
# GET /api/reports/customer
# ══════════════════════════════════════════════════════════════════════


class TestCustomerReport:
    def test_ok(self, client):
        with patch(
            "reports.report_generator.ReportGenerator.generate",
            return_value={
                "title": "客户经营分析月报",
                "period": "2026-05",
                "total_leads": 10,
                "new_leads": 5,
                "conversion_rate": 0.3,
            },
        ):
            resp = client.get("/api/reports/customer")
            assert resp.status_code == 200
            data = resp.json()
            assert data["title"] == "客户经营分析月报"

    def test_generator_error(self, client):
        with patch(
            "reports.report_generator.ReportGenerator.generate",
            side_effect=Exception("LLM 调用失败"),
        ):
            resp = client.get("/api/reports/customer")
            # FastAPI 会将未处理异常转为 500
            assert resp.status_code == 500


# ══════════════════════════════════════════════════════════════════════
# GET /api/reports/daily
# ══════════════════════════════════════════════════════════════════════


class TestDailyReport:
    def test_ok_no_params(self, client):
        with patch(
            "reports.report_generator.ReportGenerator.generate",
            return_value={
                "title": "日报汇总",
                "date": "2026-05-15",
                "total_reports": 2,
            },
        ):
            resp = client.get("/api/reports/daily")
            assert resp.status_code == 200

    def test_with_date(self, client):
        with patch(
            "reports.report_generator.ReportGenerator.generate",
            return_value={"title": "日报汇总", "date": "2026-05-14"},
        ):
            resp = client.get("/api/reports/daily?date=2026-05-14")
            assert resp.status_code == 200

    def test_with_employee_id(self, client):
        with patch(
            "reports.report_generator.ReportGenerator.generate",
            return_value={"title": "日报汇总", "employee_id": 1},
        ):
            resp = client.get("/api/reports/daily?employee_id=1")
            assert resp.status_code == 200

    def test_invalid_employee_id_422(self, client):
        resp = client.get("/api/reports/daily?employee_id=abc")
        assert resp.status_code == 422

    def test_with_both_params(self, client):
        with patch(
            "reports.report_generator.ReportGenerator.generate",
            return_value={"title": "日报汇总", "date": "2026-05-15", "employee_id": 1},
        ):
            resp = client.get(
                "/api/reports/daily?date=2026-05-15&employee_id=1"
            )
            assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════
# GET /api/reports/weekly
# ══════════════════════════════════════════════════════════════════════


class TestWeeklyReport:
    def test_ok(self, client):
        with patch(
            "reports.report_generator.ReportGenerator.generate",
            return_value={
                "title": "员工周报汇总",
                "week": "2026-W20",
                "total_reports": 15,
            },
        ):
            resp = client.get("/api/reports/weekly")
            assert resp.status_code == 200
            data = resp.json()
            assert data["title"] == "员工周报汇总"


# ══════════════════════════════════════════════════════════════════════
# GET /api/reports/psych-weekly
# ══════════════════════════════════════════════════════════════════════


class TestPsychWeeklyReport:
    def test_ok(self, client):
        with patch(
            "reports.report_generator.ReportGenerator.generate",
            return_value={
                "title": "学生心理健康周报",
                "week": "2026-W20",
                "high_risk_count": 2,
                "medium_risk_count": 5,
            },
        ):
            resp = client.get("/api/reports/psych-weekly")
            assert resp.status_code == 200
            data = resp.json()
            assert data["title"] == "学生心理健康周报"


# ══════════════════════════════════════════════════════════════════════
# GET /api/reports/complaint-weekly
# ══════════════════════════════════════════════════════════════════════


class TestComplaintWeeklyReport:
    def test_ok(self, client):
        with patch(
            "reports.report_generator.ReportGenerator.generate",
            return_value={
                "title": "投诉处理周报",
                "week": "2026-W20",
                "total_tickets": 8,
                "resolved": 6,
                "pending": 2,
            },
        ):
            resp = client.get("/api/reports/complaint-weekly")
            assert resp.status_code == 200
            data = resp.json()
            assert data["title"] == "投诉处理周报"
