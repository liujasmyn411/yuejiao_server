"""
企业助手 - NL2SQL 自然语言转SQL引擎
将员工的自然语言查询转为安全的MySQL SELECT语句
"""
import json
import re
from utils.llm_client import get_llm_client
from agents.enterprise.prompts import NL2SQL_PROMPT


class NL2SQL:
    """自然语言 → 安全SQL转换器（支持SELECT和有限UPDATE）"""

    # 可查询的表白名单
    ALLOWED_TABLES = [
        "sys_user", "crm_lead", "employee_daily_report",
        "student_score", "student_admin_service", "student_feedback_ticket",
        "student_academic", "student_study_abroad_progress",
        "course_project", "event_lecture", "event_registration",
    ]

    # UPDATE安全白名单: {表名: {允许SET的列, ...}}
    UPDATE_WHITELIST = {
        "crm_lead": {"status", "follow_up_history", "next_follow_time", "score", "owner_employee_id"},
        "student_feedback_ticket": {"status", "solution", "handle_user_id", "handle_time", "is_notified"},
        "student_admin_service": {"status", "reject_reason", "approver_id", "notify_status"},
        "student_academic": {"ddl_status", "remind_enabled", "remind_days_before"},
    }

    # 危险SQL关键字（UPDATE已从黑名单移除，走白名单控制）
    DANGEROUS_KEYWORDS = [
        "INSERT", "DELETE", "DROP", "ALTER",
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

        # 必须是SELECT或UPDATE开头
        if upper.startswith("SELECT"):
            return self._validate_select(sql)
        elif upper.startswith("UPDATE"):
            return self._validate_update(sql)
        else:
            return False, "只允许SELECT查询和有限的UPDATE操作"

    def _validate_select(self, sql: str) -> tuple:
        """验证SELECT语句安全性"""
        upper = sql.upper()

        for kw in self.DANGEROUS_KEYWORDS:
            if kw.upper() in upper:
                return False, f"SQL包含不允许的操作: {kw}"

        table_pattern = re.compile(r'\bFROM\s+(\w+)|JOIN\s+(\w+)', re.IGNORECASE)
        tables = set()
        for m in table_pattern.finditer(sql):
            t = (m.group(1) or m.group(2)).lower()
            tables.add(t)

        for t in tables:
            if t not in self.ALLOWED_TABLES:
                return False, f"不允许查询表: {t}"

        return True, ""

    def _validate_update(self, sql: str) -> tuple:
        """验证UPDATE语句安全性（白名单列级校验）"""
        upper = sql.upper()

        # 必须有WHERE
        if "WHERE" not in upper:
            return False, "UPDATE必须有WHERE条件"

        # 必须有LIMIT
        if "LIMIT" not in upper:
            return False, "UPDATE必须有LIMIT限制"

        # 提取表名
        table_m = re.search(r'UPDATE\s+(\w+)', sql, re.IGNORECASE)
        if not table_m:
            return False, "无法识别UPDATE目标表"
        table = table_m.group(1).lower()
        if table not in self.UPDATE_WHITELIST:
            return False, f"不允许UPDATE表: {table}，仅支持: {', '.join(self.UPDATE_WHITELIST.keys())}"

        # 提取SET列名
        set_match = re.search(r'SET\s+(.+?)\s*(?:WHERE|$)', sql, re.IGNORECASE | re.DOTALL)
        if not set_match:
            return False, "无法识别SET子句"

        set_clause = set_match.group(1)
        allowed_cols = self.UPDATE_WHITELIST[table]
        col_pattern = re.compile(r'(\w+)\s*=', re.IGNORECASE)
        for m in col_pattern.finditer(set_clause):
            col = m.group(1).lower()
            if col not in allowed_cols:
                return False, f"表{table}不允许修改列: {col}，仅允许: {', '.join(sorted(allowed_cols))}"

        return True, ""

    def execute(self, db, sql: str) -> list:
        """执行安全的SQL查询/更新并返回结果"""
        from sqlalchemy import text

        safe, reason = self._validate_sql(sql)
        if not safe:
            raise ValueError(reason)

        try:
            result = db.execute(text(sql))
            upper = sql.upper().strip()
            if upper.startswith("UPDATE"):
                db.flush()
                return [{"affected_rows": result.rowcount, "message": "更新成功"}]
            else:
                rows = result.fetchall()
                columns = result.keys()
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            raise RuntimeError(f"SQL执行失败: {e}")

    def query(self, db, natural_language: str) -> dict:
        """一步完成：解析 → 验证 → 执行 → 格式化结果（仅SELECT）"""
        parsed = self.parse(natural_language)
        if "error" in parsed:
            return parsed

        sql = parsed["sql"]
        if sql.upper().strip().startswith("UPDATE"):
            return {"error": "请使用update方法执行更新操作", "sql": sql}

        try:
            rows = self.execute(db, sql)
            return {
                "sql": sql,
                "explanation": parsed.get("explanation", ""),
                "type": parsed.get("type", "SELECT"),
                "count": len(rows),
                "data": rows,
            }
        except Exception as e:
            return {"error": str(e), "sql": sql}

    def update(self, db, natural_language: str) -> dict:
        """一步完成：解析 → 验证 → 执行UPDATE → 提交事务"""
        parsed = self.parse(natural_language)
        if "error" in parsed:
            return parsed

        sql = parsed["sql"]
        if not sql.upper().strip().startswith("UPDATE"):
            return {"error": "该语句不是UPDATE操作，请使用query方法", "sql": sql}

        try:
            rows = self.execute(db, sql)
            db.commit()
            return {
                "sql": sql,
                "explanation": parsed.get("explanation", ""),
                "type": "UPDATE",
                "data": rows,
            }
        except Exception as e:
            db.rollback()
            return {"error": str(e), "sql": sql}
