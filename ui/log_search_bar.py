# -*- coding: utf-8 -*-
"""
log_search_bar.py
功能描述: 日志搜索工具栏——搜索框/高亮/计数/前后导航，操作目标为注入的 QTextEdit
         高亮使用 QTextEdit.setExtraSelections（非破坏性叠加层），不改动只读文档；
         旧实现用 mergeCharFormat 直接改文档，在只读控件上会导致进程 abort。
         样式统一由全局 QSS 提供（objectName 选择器），本文件不再内联样式表
"""
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import QLineEdit, QLabel, QTextEdit, QToolBar, QToolButton

from ui import icons, tokens

MAX_MATCHES = 5000    # 防御：极端搜索词不做无界遍历


class LogSearchBar(QToolBar):
    """日志搜索工具栏：搜索/高亮/计数/导航，操作目标为注入的 QTextEdit"""

    closed = pyqtSignal()  # 关闭搜索时发出

    def __init__(self, log_text, parent=None):
        super().__init__(parent)
        self._log_text = log_text
        self.search_matches = []          # [(起始位置, 长度), ...]
        self.current_match_index = -1
        self._build_ui()

    def _build_ui(self):
        """构建搜索框/计数/导航/关闭按钮"""
        self.setObjectName('logSearchBar')
        self.setMovable(False)
        self.setFloatable(False)
        self.setVisible(False)  # 默认隐藏

        self.search_box = QLineEdit()
        self.search_box.setObjectName('logSearchInput')
        self.search_box.setPlaceholderText("搜索日志…")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.addAction(
            icons.icon('fa5s.search', color=tokens.DARK['text_dim']),
            QLineEdit.LeadingPosition)
        self.search_box.textChanged.connect(self.search_logs)

        self.count_label = QLabel("0/0")
        self.count_label.setObjectName('logSearchCount')
        self.count_label.setMinimumWidth(46)

        self.prev_btn = self._make_button('fa5s.angle-up', '上一个匹配项', self.search_previous)
        self.next_btn = self._make_button('fa5s.angle-down', '下一个匹配项', self.search_next)
        self.close_btn = self._make_button('fa5s.times', '关闭搜索', self.close_search,
                                           object_name='logSearchClose')

        for widget in (self.search_box, self.count_label,
                       self.prev_btn, self.next_btn, self.close_btn):
            self.addWidget(widget)

    @staticmethod
    def _make_button(icon_name, tooltip, slot, object_name='logSearchButton'):
        button = QToolButton()
        button.setObjectName(object_name)
        button.setIcon(icons.toolbar_icon(icon_name))
        button.setToolTip(tooltip)
        button.clicked.connect(slot)
        return button

    # ── 显隐 ────────────────────────────────────────────
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

    # ── 搜索与高亮 ──────────────────────────────────────
    def search_logs(self, search_text):
        """搜索日志内容并高亮全部匹配项"""
        if not search_text:
            self.clear_search_highlights()
            self.count_label.setText("0/0")
            return

        self.search_matches = self._find_all(search_text)
        total = len(self.search_matches)
        if total:
            self.current_match_index = 0
            self._apply_extra_selections()
            self._scroll_to_current()
            self.count_label.setText(f"1/{total}")
        else:
            self.current_match_index = -1
            self._apply_extra_selections()
            self.count_label.setText("0/0")

    def _find_all(self, text):
        """在文档中查找全部非重叠匹配，返回 [(位置, 长度)]"""
        document = self._log_text.document()
        matches = []
        cursor = QTextCursor(document)
        while len(matches) < MAX_MATCHES:
            cursor = document.find(text, cursor)
            if cursor.isNull():
                break
            matches.append((cursor.selectionStart(), len(text)))
            cursor.setPosition(cursor.selectionEnd())
        return matches

    def clear_search_highlights(self):
        """清除全部搜索高亮（只清叠加层，不动文档）"""
        self.search_matches = []
        self.current_match_index = -1
        self._log_text.setExtraSelections([])

    def _apply_extra_selections(self):
        """用 ExtraSelection 渲染高亮：当前项实心，其它项半透明"""
        dim_format = QTextCharFormat()
        dim_format.setBackground(QColor(tokens.rgba(tokens.DARK['search_highlight'], 0.32)))

        current_format = QTextCharFormat()
        current_format.setBackground(QColor(tokens.DARK['search_highlight']))
        current_format.setForeground(QColor(tokens.DARK['search_text']))

        document = self._log_text.document()
        selections = []
        for index, (start, length) in enumerate(self.search_matches):
            cursor = QTextCursor(document)
            cursor.setPosition(start)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, length)

            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format = current_format if index == self.current_match_index else dim_format
            selections.append(selection)

        self._log_text.setExtraSelections(selections)

    def highlight_current_match(self):
        """重绘高亮并定位当前项"""
        self._apply_extra_selections()
        self._scroll_to_current()

    def _scroll_to_current(self):
        """把视图滚动到当前匹配项"""
        if not self.search_matches or self.current_match_index < 0:
            return
        start, length = self.search_matches[self.current_match_index]
        cursor = QTextCursor(self._log_text.document())
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, length)
        self._log_text.setTextCursor(cursor)
        self._log_text.ensureCursorVisible()

    def search_next(self):
        """下一个匹配项"""
        if not self.search_matches:
            return
        self.current_match_index = (self.current_match_index + 1) % len(self.search_matches)
        self._update_count()
        self.highlight_current_match()

    def search_previous(self):
        """上一个匹配项"""
        if not self.search_matches:
            return
        self.current_match_index = (self.current_match_index - 1) % len(self.search_matches)
        self._update_count()
        self.highlight_current_match()

    def _update_count(self):
        self.count_label.setText(f"{self.current_match_index + 1}/{len(self.search_matches)}")
