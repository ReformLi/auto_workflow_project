# -*- coding: utf-8 -*-
"""
log_panel.py
功能描述: 日志窗口处理器——把 logging 记录以「时间戳 + 级别徽章 + 正文」的三段式
         彩色格式写入 QTextEdit，支持级别过滤与最大行数裁剪
         （见 UI_DESIGN.md §5.5）
"""

import logging
from datetime import datetime

from PyQt5.QtGui import QColor, QFont, QTextCharFormat, QTextCursor

from ui import tokens

# 级别 → (徽章色 token, 正文是否用级别色强调)
_LEVEL_STYLE = {
    logging.DEBUG:    ('text_dim', False),
    logging.INFO:     ('info',     False),
    logging.WARNING:  ('warning',  False),
    logging.ERROR:    ('error',    True),
    logging.CRITICAL: ('error',    True),
}

_LEVEL_NAMES = {
    logging.DEBUG: 'DEBUG',
    logging.INFO: 'INFO',
    logging.WARNING: 'WARN',
    logging.ERROR: 'ERROR',
    logging.CRITICAL: 'CRIT',
}

DEFAULT_MAX_LINES = 5000


class TextEditHandler(logging.Handler):
    """把日志写入 QTextEdit 的处理器（支持级别过滤、行数上限、缓存重绘）"""

    def __init__(self, text_edit, max_lines=DEFAULT_MAX_LINES):
        super().__init__()
        self.text_edit = text_edit
        self.max_lines = max_lines

        # 记录缓存：(time_str, levelno, message)
        self.log_records = []
        self._level_filter = logging.NOTSET   # NOTSET = 显示全部

    # ── 颜色 ────────────────────────────────────────────
    @staticmethod
    def _color(key):
        return QColor(tokens.DARK[key])

    def create_format(self, color_key, bold=False, italic=False):
        """创建指定 tokens 色的字符格式"""
        fmt = QTextCharFormat()
        fmt.setForeground(self._color(color_key))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    # ── 写入 ────────────────────────────────────────────
    def emit(self, record):
        """接收日志记录，按当前过滤条件插入文本框并缓存"""
        try:
            msg = self.format(record)
            created = datetime.fromtimestamp(record.created)
            time_str = created.strftime('%H:%M:%S')

            self.log_records.append((time_str, record.levelno, msg))
            self._trim_cache()

            if self._level_filter is not logging.NOTSET and record.levelno < self._level_filter:
                return
            self._insert_log(time_str, record.levelno, msg)
        except Exception:
            self.handleError(record)

    def _insert_log(self, time_str, levelno, msg):
        """插入一条日志：时间戳(暗) + 级别徽章(级别色加粗) + 正文"""
        badge_key, emphasize = _LEVEL_STYLE.get(levelno, ('text', False))
        body_key = badge_key if emphasize else 'text'

        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)

        cursor.insertText(f'[{time_str}] ', self.create_format('text_dim'))
        cursor.insertText(f'{_LEVEL_NAMES.get(levelno, "LOG"):<5} ',
                          self.create_format(badge_key, bold=True))
        cursor.insertText(f'{msg}\n', self.create_format(body_key))

        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()

    # ── 过滤 / 重绘 ─────────────────────────────────────
    def set_level_filter(self, levelno):
        """设置最低显示级别（logging.NOTSET 或 None 表示全部）"""
        self._level_filter = levelno if levelno is not None else logging.NOTSET
        self.refresh()

    def level_filter(self):
        return self._level_filter

    def refresh(self):
        """按当前过滤条件重绘全部缓存日志"""
        self.text_edit.clear()
        for time_str, levelno, msg in self.log_records:
            if self._level_filter is not logging.NOTSET and levelno < self._level_filter:
                continue
            self._insert_log(time_str, levelno, msg)

    def clear_logs(self):
        """清空日志（缓存与显示一起清）"""
        self.log_records = []
        self.text_edit.clear()

    # ── 行数上限 ────────────────────────────────────────
    def set_max_lines(self, max_lines):
        """设置最大保留行数（None/0 表示不限制）"""
        self.max_lines = max_lines or 0
        self._trim_cache()
        self.refresh()

    def _trim_cache(self):
        if self.max_lines and len(self.log_records) > self.max_lines:
            self.log_records = self.log_records[-self.max_lines:]
            # 同步裁剪文档，避免控件内存无限增长
            self.text_edit.document().setMaximumBlockCount(self.max_lines + 50)

    def flush(self):
        pass
