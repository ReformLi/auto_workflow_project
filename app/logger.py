# -*- coding: utf-8 -*-
"""
日志工具
"""

import logging
import sys

from app.config import LOG_FORMAT, LOG_DATE_FORMAT, LOG_LEVEL

def setup_logging():
    """设置日志"""
    # 创建格式化器
    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT
    )

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # 设置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL))
    root_logger.addHandler(console_handler)

    # 禁用某些库的日志
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)