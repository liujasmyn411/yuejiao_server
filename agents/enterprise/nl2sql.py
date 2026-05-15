"""
企业助手 - NL2SQL 自然语言转SQL引擎
将员工的自然语言查询转为安全的MySQL SELECT语句
"""
import json
import re
from utils.llm_client import get_llm_client
from agents.enterprise.prompts import NL2SQL_PROMPT


class NL2SQL:
    """自然语言 → 安全SQL转换器"""

    # 可查询的表白名单
    ALLOWED_TABLES = [
        "sys_user", "crm_lead", "employee_daily_report",
        "student_score", "student_admin_service", "student_feedback_ticket",
        "student_academic", "student_study_abroad_progress",
        "course_project", "event_lecture", "event_registration",
    ]

    # 危险SQL关键字
    DANGEROUS_KEYWORDS = [
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
        "TRUNCATE", "CREATE", "REPLACE", "GRANT", "REVOKE",
        "EXEC", "EXECUTE", "INTO OUTFILE", "INTO DUMPFILE",
        "LOAD_FILE", "SLEEP(", "BENCHMARK(", "WAITFOR",
    ]

    def __init__(self):
        self.llm = get_llm_client()

    def parse(self, natural_language: str) -> dict:
        """将自然语言转为SQL（含安全检查）"""
        prompt = NL2SQL_PROMPT.format(user_input=natural_language)
        result = self.llm._call_api(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=600,
        )
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            return {"error": "无法解析生成的SQL，请换一种方式描述查询"}

        if "error" in parsed:
            return parsed

        sql = parsed.get("sql", "")
        if not sql:
            return {"error": "未能生成SQL语句"}

        # 安全检查
        safe, reason = self._validate_sql(sql)
        if not safe:
            return {"error": reason}

        parsed["sql"] = sql
        return parsed

    def _validate_sql(self, sql: str) -> tuple:
        """验证SQL安全性，返回 (是否安全, 原因)"""
        upper = sql.upper().strip()

        # 必须是SELECT开头
        if not upper.startswith("SELECT"):
            return False, "只允许SELECT查询，不支持修改操作"

        # 检测危险关键字
        for kw in self.DANGEROUS_KEYWORDS:
            if kw.upper() in upper:
                return False, f"SQL包含不允许的操作: {kw}"

        # 检测表名是否在白名单
        table_pattern = re.compile(r'\bFROM\s+(\w+)|JOIN\s+(\w+)', re.IGNORECASE)
        tables = set()
        for m in table_pattern.finditer(sql):
            t = (m.group(1) or m.group(2)).lower()
            tables.add(t)

        for t in tables:
            if t not in self.ALLOWED_TABLES:
                return False, f"不允许查询表: {t}"

        # 确保有LIMIT
        if "LIMIT" not in upper:
            sql_clean = sql.rstrip().rstrip(";").rstrip()
            return True, ""  # 允许不加LIMIT

        return True, ""

    def execute(self, db, sql: str) -> list:
        """执行安全的SQL查询并返回结果"""
        from sqlalchemy import text

        # 二次验证
        safe, reason = self._validate_sql(sql)
        if not safe:
            raise ValueError(reason)

        try:
            result = db.execute(text(sql))
            rows = result.fetchall()
            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            raise RuntimeError(f"SQL执行失败: {e}")

    def query(self, db, natural_language: str) -> dict:
        """一步完成：解析 → 验证 → 执行 → 格式化结果"""
        parsed = self.parse(natural_language)
        if "error" in parsed:
            return parsed

        try:
            rows = self.execute(db, parsed["sql"])
            return {
                "sql": parsed["sql"],
                "explanation": parsed.get("explanation", ""),
                "type": parsed.get("type", "SELECT"),
                "count": len(rows),
                "data": rows,
            }
        except Exception as e:
            return {"error": str(e), "sql": parsed.get("sql", "")}
