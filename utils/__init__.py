"""
粤教服务 - 工具模块
"""

import logging
import os
from pathlib import Path
from config import settings


def setup_logging(log_dir: str = None, log_level: str = None) -> logging.Logger:
    """
    配置日志系统
    
    Args:
        log_dir: 日志文件存放目录，默认从 settings.log_dir 读取
        log_level: 日志级别，默认从 settings.log_level 读取
    
    Returns:
        配置好的 logger 实例
    """
    log_dir = log_dir or settings.log_dir
    log_level = (log_level or settings.log_level).upper()

    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 文件处理器
    log_file = log_path / "app.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    # 配置根 logger
    logger = logging.getLogger("yuejiao")
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    logger.handlers = []  # 清除已有处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
