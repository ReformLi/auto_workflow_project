# -*- coding: utf-8 -*-
"""
log_search_bar.py
功能描述: 日志搜索工具栏——搜索框/高亮/计数/前后导航，操作目标为注入的 QTextEdit
"""
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor, QTextCharFormat
from PyQt5.QtWidgets import QToolBar, QLineEdit, QLabel, QToolButton


class LogSearchBar(QToolBar):
    """日志搜索工具栏：搜索/高亮/计数/导航，操作目标为注入的 QTextEdit"""

    closed = pyqtSignal()  # 点击 ✕ 或 close_search() 时发出

    def __init__(self, log_text, theme_manager, parent=None):
        super().__init__(parent)
        self._log_text = log_text
        self.theme_manager = theme_manager
        self.search_matches = []
        self.current_match_index = -1
        self._build_ui()

    def _build_ui(self):
        """构建搜索框/计数/导航/关闭按钮"""
        self.setStyleSheet(self.theme_manager.get_stylesheet('search_toolbar'))
        self.setMovable(False)
        self.setVisible(False)  # 默认隐藏

        # 搜索框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索日志...")
        self.search_box.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.theme_manager.colors['primary_bg']};
                color: {self.theme_manager.colors['text_primary']};
                border: 1px solid {self.theme_manager.colors['border']};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 200px;
            }}
        """)
        self.search_box.textChanged.connect(self.search_logs)

        # 搜索结果计数标签
        self.count_label = QLabel("0/0")
        self.count_label.setStyleSheet(f"color: {self.theme_manager.colors['text_secondary']}; font-size: 11px;")
        self.count_label.setMinimumWidth(40)

        # 上一个按钮
        btn_style = f"""
            QToolButton {{
                background-color: {self.theme_manager.colors['button_bg']};
                color: {self.theme_manager.colors['text_primary']};
                border: 1px solid {self.theme_manager.colors['border_light']};
                border-radius: 4px;
                padding: 4px;
                min-width: 30px;
            }}
            QToolButton:hover {{
                background-color: {self.theme_manager.colors['button_hover']};
            }}
        """
        close_btn_style = f"""
            QToolButton {{
                background-color: {self.theme_manager.colors['button_bg']};
                color: {self.theme_manager.colors['text_primary']};
                border: 1px solid {self.theme_manager.colors['border_light']};
                border-radius: 4px;
                padding: 4px;
                min-width: 30px;
            }}
            QToolButton:hover {{
                background-color: {self.theme_manager.colors['error']};
                border-color: {self.theme_manager.colors['critical']};
            }}
        """

        self.prev_btn = QToolButton()
        self.prev_btn.setText("↑")
        self.prev_btn.setToolTip("上一个匹配项")
        self.prev_btn.setStyleSheet(btn_style)
        self.prev_btn.clicked.connect(self.search_previous)

        # 下一个按钮
        self.next_btn = QToolButton()
        self.next_btn.setText("↓")
        self.next_btn.setToolTip("下一个匹配项")
        self.next_btn.setStyleSheet(btn_style)
        self.next_btn.clicked.connect(self.search_next)

        # 关闭搜索按钮
        self.close_btn = QToolButton()
        self.close_btn.setText("✕")
        self.close_btn.setToolTip("关闭搜索")
        self.close_btn.setStyleSheet(close_btn_style)
        self.close_btn.clicked.connect(self.close_search)

        # 添加到工具栏
        self.addWidget(self.search_box)
        self.addWidget(self.count_label)
        self.addWidget(self.prev_btn)
        self.addWidget(self.next_btn)
        self.addWidget(self.close_btn)

    def open_search(self):
        """打开搜索栏并聚焦"""
        self.setVisible(True)
        self.search_box.setFocus()

    def close_search(self):
        """关闭搜索栏并清除高亮"""
        self.setVisible(False)
        self.search_box.clear()
        self.clear_search_highlights()
        self.closed.emit()

    def apply_theme(self, theme_manager):
        """更新搜索工具栏样式"""
        self.theme_manager = theme_manager
        self.setStyleSheet(theme_manager.get_stylesheet('search_toolbar'))

    def search_logs(self, search_text):
        """搜索日志内容"""
        if not search_text:
            self.clear_search_highlights()
            self.count_label.setText("0/0")
            return

        # 清除之前的高亮
        self.clear_search_highlights()

        # 搜索匹配项
        cursor = self._log_text.textCursor()
        cursor.movePosition(cursor.Start)

        self.search_matches = []
        fmt = QTextCharFormat()
        fmt.setBackground(QColor('#ffa502'))  # 橙色高亮
        fmt.setForeground(QColor('#000000'))  # 黑色文本

        while True:
            cursor = self._log_text.document().find(search_text, cursor)
            if cursor.isNull():
                break
            # 保存匹配位置
            self.search_matches.append(cursor.position())
            # 高亮匹配项
            cursor.movePosition(cursor.NoMove, cursor.KeepAnchor, len(search_text))
            self._log_text.setTextCursor(cursor)
            cursor.mergeCharFormat(fmt)
            cursor.clearSelection()

        # 更新计数显示
        total_matches = len(self.search_matches)
        if total_matches > 0:
            self.current_match_index = 0
            self.highlight_current_match()
            self.count_label.setText(f"{self.current_match_index + 1}/{total_matches}")
        else:
            self.current_match_index = -1
            self.count_label.setText("0/0")

    def clear_search_highlights(self):
        """清除搜索高亮"""
        cursor = self._log_text.textCursor()
        cursor.movePosition(cursor.Start)
        cursor.movePosition(cursor.End, cursor.KeepAnchor)
        fmt = QTextCharFormat()
        fmt.clearBackground()
        cursor.mergeCharFormat(fmt)
        self.search_matches = []
        self.current_match_index = -1

    def highlight_current_match(self):
        """高亮当前匹配项"""
        if not self.search_matches or self.current_match_index < 0:
            return

        # 移除之前的高亮
        cursor = self._log_text.textCursor()
        cursor.movePosition(cursor.Start)
        cursor.movePosition(cursor.End, cursor.KeepAnchor)
        fmt = QTextCharFormat()
        fmt.clearBackground()
        cursor.mergeCharFormat(fmt)

        # 高亮当前匹配项
        cursor.setPosition(self.search_matches[self.current_match_index])
        cursor.movePosition(cursor.Right, cursor.KeepAnchor, len(self.search_box.text()))
        fmt.setBackground(QColor('#ffa502'))
        fmt.setForeground(QColor('#000000'))
        cursor.mergeCharFormat(fmt)

        # 滚动到匹配项
        self._log_text.setTextCursor(cursor)
        self._log_text.ensureCursorVisible()

    def search_next(self):
        """查找下一个匹配项"""
        if not self.search_matches:
            return

        self.current_match_index = (self.current_match_index + 1) % len(self.search_matches)
        total_matches = len(self.search_matches)
        self.count_label.setText(f"{self.current_match_index + 1}/{total_matches}")
        self.highlight_current_match()

    def search_previous(self):
        """查找上一个匹配项"""
        if not self.search_matches:
            return

        self.current_match_index = (self.current_match_index - 1) % len(self.search_matches)
        total_matches = len(self.search_matches)
        self.count_label.setText(f"{self.current_match_index + 1}/{total_matches}")
        self.highlight_current_match()
