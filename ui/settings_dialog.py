# -*- coding: utf-8 -*-
"""
settings_dialog.py
功能描述: 设置对话框（外观 + 日志）
         只保留「真正会生效」的选项：主题、网格线、日志捕获级别、日志最大行数。
         旧版本里的「自动保存 / 执行超时」未接线，本次重设计一并移除，避免假 UI。
         见 UI_DESIGN.md §5.7
"""
import logging

from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QVBoxLayout
)

from ui import qss

# 显示文本 → logging 级别
_LOG_LEVELS = [
    ('DEBUG（排障）', logging.DEBUG),
    ('INFO（默认）', logging.INFO),
    ('WARNING', logging.WARNING),
    ('ERROR', logging.ERROR),
]

# 显示文本 → 最大行数（None = 不限制）
_MAX_LINES = [
    ('1000 行', 1000),
    ('5000 行', 5000),
    ('10000 行', 10000),
    ('不限制', None),
]


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, theme_state, parent=None):
        super().__init__(parent)
        self.theme_state = theme_state
        self.setWindowTitle('设置')
        self.setMinimumWidth(420)

        self._build()
        self._load()

    # ── 构建 ────────────────────────────────────────────
    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # 外观
        appearance = QGroupBox('外观')
        form = QFormLayout()
        form.setSpacing(8)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['深色主题（专业工具风）'])
        self.theme_combo.setEnabled(False)   # 本次重设计仅提供深色
        self.theme_combo.setToolTip('浅色主题未在重设计中提供')
        form.addRow('主题模式:', self.theme_combo)

        self.grid_check = QCheckBox('显示画布网格线')
        form.addRow('', self.grid_check)

        appearance.setLayout(form)
        layout.addWidget(appearance)

        # 日志
        log_group = QGroupBox('日志')
        log_form = QFormLayout()
        log_form.setSpacing(8)

        self.level_combo = QComboBox()
        for text, _ in _LOG_LEVELS:
            self.level_combo.addItem(text)
        self.level_combo.setToolTip('低于该级别的日志不会被记录到面板（影响 DEBUG 排障）')
        log_form.addRow('捕获级别:', self.level_combo)

        self.lines_combo = QComboBox()
        for text, _ in _MAX_LINES:
            self.lines_combo.addItem(text)
        self.lines_combo.setToolTip('超出后自动丢弃最早的日志')
        log_form.addRow('最大行数:', self.lines_combo)

        log_group.setLayout(log_form)
        layout.addWidget(log_group)

        layout.addStretch(1)

        # 按钮
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        self.buttons.button(QDialogButtonBox.Ok).setText('确定')
        self.buttons.button(QDialogButtonBox.Cancel).setText('取消')
        self.buttons.button(QDialogButtonBox.Apply).setText('应用')
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        qss.set_kind(self.buttons.button(QDialogButtonBox.Ok), 'primary')
        layout.addWidget(self.buttons)

    # ── 读写 ────────────────────────────────────────────
    def _load(self):
        """用当前状态填充控件"""
        self.grid_check.setChecked(self.theme_state.grid_display)
        self._select_by_value(self.level_combo, self.theme_state.log_capture_level, _LOG_LEVELS)
        self._select_by_value(self.lines_combo, self.theme_state.max_log_lines, _MAX_LINES)

    @staticmethod
    def _select_by_value(combo, value, mapping):
        for index, (_text, mapped) in enumerate(mapping):
            if mapped == value:
                combo.setCurrentIndex(index)
                return
        combo.setCurrentIndex(0)

    def apply_settings(self):
        """把设置写回状态并通知主窗口生效"""
        self.theme_state.grid_display = self.grid_check.isChecked()

        capture_level = _LOG_LEVELS[self.level_combo.currentIndex()][1]
        max_lines = _MAX_LINES[self.lines_combo.currentIndex()][1]

        parent = self.parent()
        if parent is None:
            return
        if hasattr(parent, 'update_grid'):
            parent.update_grid(self.theme_state.grid_display)
        if hasattr(parent, 'apply_log_settings'):
            parent.apply_log_settings(capture_level=capture_level, max_lines=max_lines)

    def _on_accept(self):
        self.apply_settings()
        self.accept()

    def get_settings(self):
        """返回当前对话框中的设置（便于测试与后续持久化）"""
        return {
            'theme': self.theme_state.current_theme,
            'grid_display': self.grid_check.isChecked(),
            'log_capture_level': _LOG_LEVELS[self.level_combo.currentIndex()][1],
            'max_log_lines': _MAX_LINES[self.lines_combo.currentIndex()][1],
        }
