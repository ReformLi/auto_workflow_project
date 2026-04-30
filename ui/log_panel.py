# -*- coding: utf-8 -*-
"""
log_editor.py
作者: reformLi
创建日期: 2026/3/24
最后修改: 2026/3/24
版本: 1.0.0

功能描述: 日志窗口
"""

# -*- coding: utf-8 -*-
"""
log_editor.py
作者: reformLi
创建日期: 2026/3/24
最后修改: 2026/4/29
版本: 1.1.0

功能描述: 支持主题切换的彩色日志窗口
"""

import logging
from datetime import datetime
from PyQt5.QtGui import QTextCharFormat, QColor, QFont, QTextCursor

from ui.styles import ThemeManager


class TextEditHandler(logging.Handler):
    """自定义日志处理器，将日志输出到QTextEdit，支持主题切换后更新已显示日志的颜色"""

    def __init__(self, text_edit, theme_manager=None):
        super().__init__()
        self.text_edit = text_edit
        self.theme_manager = theme_manager or ThemeManager()

        # 日志记录缓存： (time_str, levelno, levelname, message)
        self.log_records = []

        # 设置初始格式和颜色集
        self.setup_formats()
        self.setup_colors()

        # 监听主题变化信号（假设 ThemeManager 有 themeChanged 信号）
        if hasattr(self.theme_manager, 'themeChanged'):
            self.theme_manager.themeChanged.connect(self.on_theme_changed)

    def setup_formats(self):
        """设置不同日志级别的文本格式（用于消息文本）"""
        if self.theme_manager.current_theme == 'light':
            self.formats = {
                logging.DEBUG: self.create_format('#666666', italic=True),
                logging.INFO: self.create_format('#0066cc'),
                logging.WARNING: self.create_format('#ff8800', bold=True),
                logging.ERROR: self.create_format('#cc0000', bold=True),
                logging.CRITICAL: self.create_format('#aa0000', bold=True),
            }
        else:   # dark 主题
            self.formats = {
                logging.DEBUG: self.create_format('#888888', italic=True),
                logging.INFO: self.create_format('#ffffff'),
                logging.WARNING: self.create_format('#ffcc00', bold=True),
                logging.ERROR: self.create_format('#ff6b6b', bold=True),
                logging.CRITICAL: self.create_format('#ff0000', bold=True),
            }

    def setup_colors(self):
        """设置级别标签、时间戳的颜色（同样跟随主题）"""
        if self.theme_manager.current_theme == 'light':
            self.level_colors = {
                logging.DEBUG: '#666666',
                logging.INFO: '#0066cc',
                logging.WARNING: '#ff8800',
                logging.ERROR: '#cc0000',
                logging.CRITICAL: '#aa0000'
            }
            self.timestamp_color = '#999999'
            self.separator_color = '#aaaaaa'
        else:
            self.level_colors = {
                logging.DEBUG: '#888888',
                logging.INFO: '#00ff00',
                logging.WARNING: '#ffcc00',
                logging.ERROR: '#ff6b6b',
                logging.CRITICAL: '#ff0000'
            }
            self.timestamp_color = '#666666'
            self.separator_color = '#555555'

    def create_format(self, color, bold=False, italic=False):
        """创建指定颜色的 QTextCharFormat"""
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    def emit(self, record):
        """接收日志记录，插入到文本框并缓存"""
        try:
            msg = self.format(record)
            levelno = record.levelno
            levelname = record.levelname
            created = datetime.fromtimestamp(record.created)
            time_str = created.strftime('%H:%M:%S')

            # 缓存记录（便于主题切换时重绘）
            self.log_records.append((time_str, levelno, levelname, msg))

            # 插入当前主题的彩色日志
            self._insert_log(time_str, levelno, levelname, msg)

        except Exception:
            self.handleError(record)

    def _insert_log(self, time_str, levelno, levelname, msg):
        """在文本框末尾插入一条日志（使用当前主题颜色）"""
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)

        # 时间戳
        time_fmt = self.create_format(self.timestamp_color)
        cursor.insertText(f'[{time_str}] ', time_fmt)

        # 级别标签
        level_color = self.level_colors.get(levelno, '#ffffff')
        level_fmt = self.create_format(level_color, bold=True)
        cursor.insertText(f'{levelname:8}', level_fmt)

        # 分隔符
        sep_fmt = self.create_format(self.separator_color)
        cursor.insertText(' | ', sep_fmt)

        # 消息内容
        msg_fmt = self.formats.get(levelno, self.formats[logging.INFO])
        cursor.insertText(f'{msg}\n', msg_fmt)

        # 滚动到底部
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()

    def refresh(self):
        """清空文本框，用当前主题颜色重新插入所有缓存的日志"""
        self.text_edit.clear()
        # 临时屏蔽信号，避免重复记录（如果 text_edit 内容改变有信号）
        # 理论上不会触发 emit，但以防万一
        old_records = self.log_records.copy()
        self.log_records = []   # 清空缓存，防止 emit 重复添加

        for time_str, levelno, levelname, msg in old_records:
            # 重新缓存（因为下面 _insert_log 不会触发 emit，手动添加）
            self.log_records.append((time_str, levelno, levelname, msg))
            self._insert_log(time_str, levelno, levelname, msg)

    def on_theme_changed(self):
        """主题变化时的槽函数，更新颜色配置并刷新显示"""
        # self.setup_formats()
        # self.setup_colors()
        self.refresh()

    # def update_theme(self, theme_name):
    #     """
    #     手动切换主题时调用（若 ThemeManager 无信号或需要外部手动控制）
    #     usage: handler.update_theme('dark')
    #     """
    #     if self.theme_manager:
    #         self.theme_manager.current_theme = theme_name
    #     self.on_theme_changed(theme_name)

    def flush(self):
        pass