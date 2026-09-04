# -*- coding: utf-8 -*-
"""
log_filter_bar.py
功能描述: 日志工具条——级别过滤胶囊 + 清空 + 导出（位于日志正文上方）
         见 UI_DESIGN.md §5.5
"""
import logging

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import QAction, QActionGroup, QToolBar

from ui import icons, tokens

# (显示名, logging 级别, 色 token)
_LEVELS = [
    ('全部', logging.NOTSET,  'text_2nd'),
    ('DEBUG', logging.DEBUG,  'text_dim'),
    ('INFO', logging.INFO,    'info'),
    ('WARN', logging.WARNING, 'warning'),
    ('ERROR', logging.ERROR,  'error'),
]


class LogFilterBar(QToolBar):
    """日志级别过滤条 + 清空/导出命令"""

    level_changed = pyqtSignal(int)      # logging 级别（NOTSET 表示全部）
    clear_requested = pyqtSignal()
    export_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('logFilterBar')
        self.setMovable(False)
        self.setFloatable(False)
        self.setIconSize(QSize(12, 12))
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._build()

    def _build(self):
        group = QActionGroup(self)
        group.setExclusive(True)
        self._level_actions = {}

        for name, level, color_key in _LEVELS:
            action = QAction(f' {name}', self)
            action.setIcon(icons.tinted('fa5s.circle', tokens.DARK[color_key], scale=0.55))
            action.setCheckable(True)
            action.setToolTip(f'只显示 {name} 及以上级别' if level != logging.NOTSET else '显示全部级别')
            action.triggered.connect(lambda checked, lv=level: self.level_changed.emit(lv))
            group.addAction(action)
            self.addAction(action)
            self._level_actions[level] = action

        self._level_actions[logging.NOTSET].setChecked(True)

        self.addSeparator()

        self.clear_action = QAction(' 清空', self)
        self.clear_action.setIcon(icons.toolbar_icon('fa5s.eraser'))
        self.clear_action.setToolTip('清空日志显示')
        self.clear_action.triggered.connect(self.clear_requested)
        self.addAction(self.clear_action)

        self.export_action = QAction(' 导出', self)
        self.export_action.setIcon(icons.toolbar_icon('fa5s.file-export'))
        self.export_action.setToolTip('把日志导出到文件')
        self.export_action.triggered.connect(self.export_requested)
        self.addAction(self.export_action)

    # ── 对外接口 ────────────────────────────────────────
    def current_level(self):
        for level, action in self._level_actions.items():
            if action.isChecked():
                return level
        return logging.NOTSET

    def set_level(self, level):
        """以代码方式切换过滤级别（不触发信号回环）"""
        action = self._level_actions.get(level, self._level_actions[logging.NOTSET])
        if not action.isChecked():
            action.trigger()
