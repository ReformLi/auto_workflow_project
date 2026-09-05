# -*- coding: utf-8 -*-
"""
node_mouse_widget.py
功能描述: 鼠标点击节点的自定义属性编辑器（MouseClickEditor）：
- 组合框：按键、点击类型、坐标模式、执行模式；文本：坐标/偏移/双击间隔/前后等待；
  复选框：点击前移动、点击后恢复、调试红点。
- "捕获"按钮：全屏半透明十字准星，点击屏幕回填坐标到 pos_x/pos_y。
- 双击间隔字段随「点击类型=双击」联动显隐。
"""
import logging

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget,
)

from ui import tokens

_logger = logging.getLogger(__name__)

_BUTTONS = ['左键', '右键', '中键']
_CLICK_TYPES = ['单击', '双击']
_COORD_MODES = ['绝对屏幕', '相对窗口客户区']
_EXEC_MODES = ['自动', '前台', '后台']


# ---------------------------------------------------------------
# 坐标点采集器（全屏半透明十字准星，左键点击，Esc 取消）
# 结果信号：finished((x, y) | None) 屏幕绝对坐标。
# ---------------------------------------------------------------
class CoordPicker(QWidget):
    finished = QtCore.pyqtSignal(object)

    def __init__(self):
        super(CoordPicker, self).__init__(
            None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)
        self._bg = QtGui.QColor(100, 110, 130, 60)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), self._bg)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 先隐藏遮罩再取点，避免命中自身
            self.hide()
            QtCore.QCoreApplication.processEvents()
            self._finish((event.globalPos().x(), event.globalPos().y()))
        elif event.button() == Qt.RightButton:
            self._finish(None)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._finish(None)
        else:
            super(CoordPicker, self).keyPressEvent(event)

    def _finish(self, pt):
        self.hide()
        self.finished.emit(pt)
        self.close()

    @classmethod
    def pick(cls):
        """阻塞式采点：返回 (x, y) 或 None。"""
        picker = cls()
        picker.setGeometry(QtGui.QGuiApplication.primaryScreen().availableGeometry())
        picker.show()

        loop = QtCore.QEventLoop()
        result = {}

        def _on_finished(pt):
            result['pt'] = pt
            loop.quit()

        picker.finished.connect(_on_finished)
        loop.exec_()
        return result.get('pt')


def _build_row(cur, label, widget):
    row = cur.rowCount()
    cur.addWidget(QLabel(label), row, 0)
    if isinstance(widget, QWidget):
        cur.addWidget(widget, row, 1)
    cur.setRowStretch(row, 1)


class MouseClickEditor(QWidget):
    """鼠标点击属性编辑器：接管按键/点击类型/坐标/执行模式与各选项。"""

    def __init__(self, node, parent=None):
        super(MouseClickEditor, self).__init__(parent)
        self.node = node
        self._widgets = {}
        self._build_ui()
        self._reload_from_node()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(1, 1)

        def combo(label, prop, items):
            c = QComboBox()
            c.addItems(items)
            c.currentTextChanged.connect(
                lambda text: self.node.set_property(prop, text))
            self._widgets[prop] = c
            _build_row(grid, label, c)
            return c

        def text(label, prop, ph=''):
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.textChanged.connect(
                lambda t, p=prop: self.node.set_property(p, t))
            self._widgets[prop] = e
            _build_row(grid, label, e)
            return e

        def check(label, prop):
            c = QCheckBox(label)
            c.toggled.connect(
                lambda on, p=prop: self.node.set_property(p, '1' if on else '0'))
            self._widgets[prop] = c
            _build_row(grid, '', c)
            return c

        self._button_combo = combo('按键', 'button', _BUTTONS)
        self._click_combo = combo('点击类型', 'click_type', _CLICK_TYPES)
        self._dbl_edit = text('双击间隔(ms)', 'dbl_interval', '300')

        self._coord_combo = combo('坐标模式', 'coord_mode', _COORD_MODES)

        # 坐标行：X / Y 输入 + “捕获”按钮（回填 pos_x/pos_y）
        x_edit = QLineEdit()
        x_edit.setPlaceholderText('X')
        y_edit = QLineEdit()
        y_edit.setPlaceholderText('Y')
        self._pos_x_edit = x_edit
        self._pos_y_edit = y_edit
        self._widgets['pos_x'] = x_edit
        self._widgets['pos_y'] = y_edit
        x_edit.textChanged.connect(lambda t: self.node.set_property('pos_x', t))
        y_edit.textChanged.connect(lambda t: self.node.set_property('pos_y', t))

        cap_btn = QPushButton('捕获')
        cap_btn.setCursor(Qt.PointingHandCursor)
        cap_btn.setToolTip('点击后选择屏幕坐标，自动回填 X/Y')
        cap_btn.setStyleSheet(self._secondary_button_style())
        cap_btn.clicked.connect(self._on_capture)
        coord_row = QHBoxLayout()
        coord_row.setSpacing(4)
        coord_row.addWidget(x_edit, 1)
        coord_row.addWidget(y_edit, 1)
        coord_row.addWidget(cap_btn)
        coord_wrap = QWidget()
        coord_wrap.setLayout(coord_row)
        _build_row(grid, '坐标', coord_wrap)

        text('偏移 X', 'offset_x', '0')
        text('偏移 Y', 'offset_y', '0')
        combo('执行模式', 'exec_mode', _EXEC_MODES)
        check('点击前移动鼠标', 'move_before')
        check('点击后恢复鼠标位置', 'restore_mouse')
        check('调试：点击前显示红点', 'show_marker')
        text('前置等待(秒)', 'pre_wait', '0')
        text('后置等待(秒)', 'post_wait', '0')

        grid.setRowStretch(grid.rowCount(), 1)
        root.addLayout(grid)
        root.addStretch(1)

        # 双击间隔随点击类型联动
        self._click_combo.currentTextChanged.connect(
            lambda _: self._sync_dbl_visibility())

    # ---------------- 数据读写 ----------------
    def _reload_from_node(self):
        for prop in ('button', 'click_type', 'coord_mode', 'exec_mode'):
            combo = self._widgets.get(prop)
            if combo is not None:
                val = self.node.get_property(prop)
                idx = combo.findText(str(val or ''))
                if idx >= 0:
                    combo.setCurrentIndex(idx)
        for prop in ('dbl_interval', 'pos_x', 'pos_y', 'offset_x', 'offset_y',
                     'pre_wait', 'post_wait'):
            edit = self._widgets.get(prop)
            if edit is not None:
                edit.setText(str(self.node.get_property(prop) or '0'))
        for prop, other in (('button', None),):
            pass
        for prop in ('move_before', 'restore_mouse', 'show_marker'):
            cb = self._widgets.get(prop)
            if cb is not None:
                cb.setChecked(str(self.node.get_property(prop)).strip() in ('1', 'true'))
        self._sync_dbl_visibility()

    def _sync_dbl_visibility(self):
        double = (self._click_combo.currentText() or '单击') == '双击'
        self._widgets['dbl_interval'].setVisible(double)

    # ---------------- 捕获 ----------------
    def _on_capture(self):
        top = self.window()
        minimizable = top is not None and top is not self
        if minimizable:
            top.showMinimized()
        try:
            pt = CoordPicker.pick()
        finally:
            if minimizable:
                top.showNormal()
                top.raise_()
                top.activateWindow()
        if not pt:
            return
        self._pos_x_edit.setText(str(pt[0]))
        self._pos_y_edit.setText(str(pt[1]))
        self.node.set_property('pos_x', str(pt[0]))
        self.node.set_property('pos_y', str(pt[1]))

    def _secondary_button_style(self):
        elev = tokens.DARK['bg_elevated']
        border = tokens.DARK['border_strong']
        text = tokens.DARK['text']
        return (f"QPushButton {{ background:{elev}; color:{text};"
                f"border:1px solid {border}; border-radius:4px;"
                f"padding:4px 12px; }}"
                f"QPushButton:hover {{ background:{tokens.DARK['bg_hover']}; }}")