# -*- coding: utf-8 -*-
"""
log_editor.py
作者: reformLi
创建日期: 2026/3/24
最后修改: 2026/3/24
版本: 1.0.0

功能描述: 日志窗口
"""

import logging

class TextEditHandler(logging.Handler):
    """自定义日志处理器，将日志输出到QTextEdit"""

    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit

    def emit(self, record):
        msg = self.format(record)
        self.text_edit.append(msg)

    def flush(self):
        pass