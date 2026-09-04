# -*- coding: utf-8 -*-
"""
title_bar.py
功能描述: Dock 面板自定义标题栏（替代系统 QDockWidget::title）
         左：分类色小图标 + 面板名；右：可选的折叠/关闭按钮（qtawesome 图标）
         见 UI_DESIGN.md §5.3 / §5.5
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QWidget, QLabel

from ui import icons, tokens


class DockTitleBar(QWidget):
    """Dock 面板标题栏，通过 dock.setTitleBarWidget() 挂载"""

    toggled = pyqtSignal(bool)   # True=展开，False=收起

    def __init__(self, title, icon_name=None, accent_color=None,
                 collapsible=True, parent=None):
        super().__init__(parent)
        self.setObjectName('dockTitleBar')
        self.setFixedHeight(tokens.DOCK_TITLE_HEIGHT)
        self._collapsed = False
        self._content_widget = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(6)

        accent = accent_color or tokens.DARK['text_2nd']

        if icon_name:
            mark = QLabel()
            mark.setPixmap(icons.tile_pixmap(icon_name, accent, size=14, radius=3))
            mark.setFixedSize(14, 14)
            layout.addWidget(mark)

        self._title_label = QLabel(title)
        self._title_label.setObjectName('dockTitleText')
        layout.addWidget(self._title_label)

        layout.addStretch(1)

        if collapsible:
            self._toggle_btn = QPushButton(self)
            self._toggle_btn.setObjectName('dockTitleButton')
            self._toggle_btn.setCursor(Qt.PointingHandCursor)
            self._toggle_btn.setFixedSize(20, 20)
            self._toggle_btn.setIcon(icons.icon('fa5s.chevron-up', scale=0.75))
            self._toggle_btn.setIconSize(self._toggle_btn.size())
            self._toggle_btn.clicked.connect(self._on_toggle)
            layout.addWidget(self._toggle_btn)
        else:
            self._toggle_btn = None

        size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setSizePolicy(size_policy)

    # ── 对外接口 ────────────────────────────────────────
    def bind_content(self, widget):
        """绑定被折叠的内容部件（通常是 dock 的 widget）"""
        self._content_widget = widget

    def set_title(self, title):
        self._title_label.setText(title)

    def is_collapsed(self):
        return self._collapsed

    # ── 内部 ────────────────────────────────────────────
    def _on_toggle(self):
        self._collapsed = not self._collapsed
        if self._content_widget is not None:
            self._content_widget.setVisible(not self._collapsed)
        if self._toggle_btn is not None:
            icon_name = 'fa5s.chevron-down' if self._collapsed else 'fa5s.chevron-up'
            self._toggle_btn.setIcon(icons.icon(icon_name, scale=0.75))
        self.toggled.emit(not self._collapsed)
