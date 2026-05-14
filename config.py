"""
粤教服务 - 全局配置管理
从 .env 文件加载所有环境变量配置
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ==================== 数据库配置 ====================
    db_type: str = "mysql"

    # MySQL 配置
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "yuejiao"
    mysql_charset: str = "utf8mb4"

    # SQLite 配置
    sqlite_url: str = "sqlite:///./yuejiao.db"

    # 连接池配置
    db_pool_size: int = 10
    db_pool_overflow: int = 20
    db_pool_recycle: int = 3600

    # ==================== API 服务配置 ====================
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_title: str = "粤教服务 AI Agent API"
    api_version: str = "1.0.0"

    # ==================== CORS 跨域配置 ====================
    cors_origins: str = "*"

    # ==================== 日志配置 ====================
    log_level: str = "INFO"
    log_dir: str = "log"

    # ==================== 安全配置 ====================
    secret_key: str = "yuejiao-secret-key-change-in-production"
    access_token_expire_minutes: int = 1440

    # ==================== 心理AI Agent配置 ====================
    psych_ai_api_base: str = "http://127.0.0.1:5000"
    psych_ai_api_key: str = ""
    psych_ai_model: str = "psych-assistant-v1"

    # ==================== 兼容旧配置名 ====================
    openai_api_key: str = ""
    model_name: str = "gpt-4o-mini"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "protected_namespaces": ("settings_",),
    }

    # ========== 派生属性 ==========

    @property
    def database_url(self) -> str:
        """根据 db_type 动态生成数据库连接 URL"""
        if self.db_type.lower() == "sqlite":
            return self.sqlite_url
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset={self.mysql_charset}"
        )

    @property
    def cors_origins_list(self) -> list:
        """将 CORS_ORIGINS 字符串解析为列表"""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]


# 全局配置实例
settings = Settings()
