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
    # 单字关键词 — 用词边界匹配，避免误杀列名（如 DELETE 误匹配 delete_flag）
    DANGEROUS_WORDS = [
        "INSERT", "DELETE", "DROP", "ALTER",
        "TRUNCATE", "CREATE", "REPLACE", "GRANT", "REVOKE",
        "EXEC", "EXECUTE",
    ]
    # 多词/函数模式 — 子串匹配（不太可能出现在正常标识符中）
    DANGEROUS_PATTERNS = [
        "INTO OUTFILE", "INTO DUMPFILE",
        "LOAD_FILE", "SLEEP(", "BENCHMARK(", "WAITFOR",
    ]

    def __init__(self, table_allowlist=None, prompt_template=None, update_whitelist=None):
        self.llm = get_llm_client()
        if table_allowlist:
            self.ALLOWED_TABLES = table_allowlist
        if update_whitelist is not None:
            self.UPDATE_WHITELIST = update_whitelist
        self._prompt_template = prompt_template or NL2SQL_PROMPT

    def parse(self, natural_language: str) -> dict:
        """将自然语言转为SQL（含安全检查）"""
        prompt = self._prompt_template.format(user_input=natural_language)
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

        # 单字关键词用词边界匹配（避免 DELETE 误匹配 delete_flag 等列名）
        for word in self.DANGEROUS_WORDS:
            if re.search(r'\b' + re.escape(word) + r'\b', upper):
                return False, f"SQL包含不允许的操作: {word}"

        # 多词/函数模式用子串匹配
        for pat in self.DANGEROUS_PATTERNS:
            if pat.upper() in upper:
                return False, f"SQL包含不允许的操作: {pat}"

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

    def query(self, db, natural_language: str, student_scope: int = None) -> dict:
        """
        一步完成：解析 → 验证 → 执行 → 格式化结果（仅SELECT）。
        student_scope: 学生ID，传入时自动限制为只查该学生的数据。
        """
        parsed = self.parse(natural_language)
        if "error" in parsed:
            return parsed

        sql = parsed["sql"]
        if sql.upper().strip().startswith("UPDATE"):
            return {"error": "请使用update方法执行更新操作", "sql": sql}

        # 学生范围限制：在 WHERE 中自动追加 student_id 条件
        if student_scope is not None:
            sql = self._apply_student_scope(sql, student_scope)

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

    def _apply_student_scope(self, sql: str, student_id: int) -> str:
        """
        在 SELECT 语句中注入 student_id 条件，确保学生只能查自己的数据。
        支持：已有 WHERE → 追加 AND；无 WHERE → 插入 WHERE。
        """
        import re
        # 只对包含学生相关表的查询做限制
        student_tables = {"student_score", "student_admin_service",
                          "student_feedback_ticket", "student_academic",
                          "student_study_abroad_progress"}
        upper = sql.upper()
        has_student_table = any(t in upper for t in student_tables)
        if not has_student_table:
            return sql  # 不涉及学生表，不加限制

        scope_clause = f"student_id = {int(student_id)}"
        # 尝试在 WHERE 后追加
        where_match = re.search(r'\bWHERE\b\s+', sql, re.IGNORECASE)
        if where_match:
            pos = where_match.end()
            # 找 WHERE 子句的结束位置（GROUP BY / ORDER BY / LIMIT / 语句末尾）
            end_match = re.search(r'\b(GROUP\s+BY|ORDER\s+BY|LIMIT|HAVING)\b', sql[pos:], re.IGNORECASE)
            if end_match:
                end_pos = pos + end_match.start()
                sql = sql[:end_pos] + f"({sql[pos:end_pos].strip()}) AND {scope_clause} " + sql[end_pos:]
            else:
                sql = sql[:pos] + f"({sql[pos:].strip()}) AND {scope_clause}"
        else:
            # 没有 WHERE 子句 → 在 ORDER BY / GROUP BY / LIMIT / 末尾之前插入
            end_match = re.search(r'\b(ORDER\s+BY|GROUP\s+BY|LIMIT|HAVING)\b', sql, re.IGNORECASE)
            if end_match:
                sql = sql[:end_match.start()] + f" WHERE {scope_clause} " + sql[end_match.start():]
            else:
                sql = sql.rstrip(';').strip() + f" WHERE {scope_clause}"
        return sql

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
