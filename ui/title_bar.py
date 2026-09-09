# -*- coding: utf-8 -*-
"""
title_bar.py
功能描述: Dock 面板自定义标题栏（替代系统 QDockWidget::title）
         左：分类色小图标 + 面板名；右：可选的折叠/关闭按钮（qtawesome 图标）
         见 UI_DESIGN.md §5.3 / §5.5
"""

from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QPainter
from PyQt5.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QWidget, QLabel

from ui import icons, tokens


class PanelStrip(QWidget):
    """面板折叠后的贴边细条：显示面板名 + 展开箭头，点击展开。

    side='left'/'right' 为竖条（宽 24，文字旋转 90°），side='bottom' 为横条（高 24）。
    """

    def __init__(self, title, icon_name=None, accent_color=None,
                 side='left', expand_cb=None, parent=None):
        super().__init__(parent)
        self._title = title
        self._accent = QColor(accent_color or tokens.DARK['text_2nd'])
        self._side = side
        self._expand_cb = expand_cb
        self.setCursor(Qt.PointingHandCursor)
        if side == 'bottom':
            self.setFixedHeight(24)
        else:
            self.setFixedWidth(24)

    def sizeHint(self):
        if self._side == 'bottom':
            return QSize(160, 24)
        return QSize(24, 120)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._expand_cb is not None:
            self._expand_cb()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor(tokens.DARK['bg_panel']))

        # 与相邻区域的分界线
        p.setPen(QColor(tokens.DARK['border']))
        if self._side == 'left':
            p.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        elif self._side == 'right':
            p.drawLine(0, 0, 0, self.height())
        else:
            p.drawLine(0, 0, self.width(), 0)

        # 展开箭头（指向展开方向）
        arrow = {'left': 'fa5s.chevron-right',
                 'right': 'fa5s.chevron-left',
                 'bottom': 'fa5s.chevron-up'}[self._side]
        icon = icons.icon(arrow, color=tokens.DARK['text_2nd'], scale=0.7)
        if self._side == 'bottom':
            icon.paint(p, 8, (self.height() - 14) // 2, 14, 14)
        else:
            icon.paint(p, (self.width() - 14) // 2, 8, 14, 14)

        # 面板名
        p.setPen(QColor(tokens.DARK['text_2nd']))
        fm = QFontMetrics(QFont(tokens.FONT_FAMILY_UI, tokens.FONT_SIZE_UI))
        if self._side == 'bottom':
            p.drawText(28, (self.height() + fm.ascent()) // 2 - 1, self._title)
        else:
            p.save()
            p.translate(self.width() / 2, self.height() / 2)
            p.rotate(-90 if self._side == 'left' else 90)
            w = fm.horizontalAdvance(self._title)
            p.drawText(int(-w / 2), int(fm.ascent() / 2), self._title)
            p.restore()


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
        self._collapse_cb = None      # 整体折叠回调：cb(collapsed=True) 由宿主隐藏整个面板

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

    def set_collapse_callback(self, cb):
        """
        设置「整体折叠」回调：设置后点箭头不再只藏内容，
        而是回调 cb(True) 由宿主把整个面板（含标题栏）从分割器收起；
        再展开由外部（视图菜单/自动唤起）调用 reset()。
        """
        self._collapse_cb = cb

    def set_title(self, title):
        self._title_label.setText(title)

    def is_collapsed(self):
        return self._collapsed

    def reset(self):
        """面板被外部重新显示时复位为展开态（内容可见、箭头朝上）。"""
        self._collapsed = False
        if self._content_widget is not None:
            self._content_widget.setVisible(True)
        self._update_chevron()

    # ── 内部 ────────────────────────────────────────────
    def _update_chevron(self):
        if self._toggle_btn is not None:
            icon_name = 'fa5s.chevron-down' if self._collapsed else 'fa5s.chevron-up'
            self._toggle_btn.setIcon(icons.icon(icon_name, scale=0.75))

    def _on_toggle(self):
        self._collapsed = not self._collapsed
        if self._collapse_cb is not None:
            # 整体折叠：宿主负责隐藏整个面板并同步视图菜单勾选态
            self._update_chevron()
            self._collapse_cb(self._collapsed)
            return
        if self._content_widget is not None:
            self._content_widget.setVisible(not self._collapsed)
        self._update_chevron()
        self.toggled.emit(not self._collapsed)
