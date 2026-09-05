# -*- coding: utf-8 -*-
"""
node_ocr_widget.py
功能描述: OCR 识别节点的自定义属性编辑器（OcrNodeEditor）。
- 渲染识别语言 / 识别区域 / 预处理 / 置信度 / 分割模式。
- 识别区域支持两种鼠标框选（全屏半透明十字准星拖拽）：
    · 窗口内框选：框选后自动抓取框选矩形覆盖的顶层窗口，存相对窗口偏移 (dx,dy,宽,高)；
    · 屏幕框选：存屏幕绝对坐标 (x,y,宽,高)。
- 用 pywin32 取窗口矩形（与 automation 层一致的 Win32 定位方式）。
"""
import logging

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
    QWidget,
)

from ui import tokens

_logger = logging.getLogger(__name__)

_LANGS = ['简体中文', '英文', '简体中文+英文']
_REGIONS = ['全屏', '窗口全部', '窗口内框选', '屏幕框选']
_PREPROCESS = ['无', '灰度', '二值化']
_PSMS = ['自动', '单行文本', '单字', '稀疏']


# ---------------------------------------------------------------
# 屏幕区域框选采集器（十字准星，左键拖拽框选，右键/Esc 取消）
# 结果信号：finished(QRect | None)，QRect 为屏幕绝对坐标。
# ---------------------------------------------------------------
class RegionSelectPicker(QWidget):
    finished = QtCore.pyqtSignal(object)

    def __init__(self):
        super(RegionSelectPicker, self).__init__(
            None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)
        self._bg = QtGui.QColor(20, 24, 32, 175)
        self._origin = None
        self._rect = None

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), self._bg)
        if self._rect is not None and not self._rect.isEmpty():
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
            painter.fillRect(self._rect, Qt.transparent)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
            painter.setPen(QtGui.QPen(QtGui.QColor('#4c8dff'), 1))
            painter.drawRect(self._rect)
            painter.setPen(QtGui.QColor('#e8eaed'))
            painter.drawText(self._rect.x(), self._rect.y() - 6,
                             '释放鼠标完成框选，右键或 Esc 取消')

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._origin = event.pos()
            self._rect = None
        elif event.button() == Qt.RightButton:
            self._finish(None)

    def mouseMoveEvent(self, event):
        if self._origin is not None:
            self._rect = QtCore.QRect(self._origin, event.pos()).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._origin is not None:
            self._rect = QtCore.QRect(self._origin, event.pos()).normalized()
            self._finish(self._rect if not self._rect.isEmpty() else None)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._finish(None)
        else:
            super(RegionSelectPicker, self).keyPressEvent(event)

    def _finish(self, rect):
        """结束框选：隐藏遮罩并发出结果信号。"""
        self.hide()
        self.finished.emit(rect)
        self.close()

    @classmethod
    def pick(cls):
        """阻塞式框选：返回 QRect 或 None。"""
        picker = cls()
        picker.setGeometry(QtGui.QGuiApplication.primaryScreen().availableGeometry())
        picker.show()

        loop = QtCore.QEventLoop()
        result = {}

        def _on_finished(rect):
            result['rect'] = rect
            loop.quit()

        picker.finished.connect(_on_finished)
        loop.exec_()
        picker.close()
        return result.get('rect')


def _window_at_point(x, y):
    """返回屏幕点 (x,y) 处的顶层窗口矩形 (left, top, right, bottom) 及标题；取不到返回 None。"""
    try:
        import win32gui
    except ImportError:
        return None
    try:
        hwnd = win32gui.WindowFromPoint((int(x), int(y)))
        if not hwnd:
            return None
        rect = win32gui.GetWindowRect(hwnd)
        title = win32gui.GetWindowText(hwnd)
        return rect, title
    except Exception as e:
        _logger.warning('获取窗口矩形失败: %s', e)
        return None


class OcrNodeEditor(QWidget):
    """OCR 属性编辑器：接管识别语言 / 区域 / 预处理 / 置信度 / 分割模式。"""

    def __init__(self, node, parent=None):
        super(OcrNodeEditor, self).__init__(parent)
        self.node = node
        self._mode_combo = None
        self._region_info = None
        self._build_ui()
        self._reload_from_node()

    # ---------------- UI ----------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 识别语言
        layout.addLayout(self._combo_row('识别语言', _LANGS, 'lang'))

        # 识别区域
        region_box = QGroupBox('识别区域')
        region_layout = QVBoxLayout(region_box)
        region_layout.setContentsMargins(8, 8, 8, 8)
        region_layout.setSpacing(6)

        mode_row = QHBoxLayout()
        mode_label = QLabel('模式')
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(_REGIONS)
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self._mode_combo, 1)
        region_layout.addLayout(mode_row)

        select_row = QHBoxLayout()
        self._select_btn = QPushButton('框选…')
        self._select_btn.setCursor(Qt.PointingHandCursor)
        self._select_btn.clicked.connect(self._on_pick_region)
        self._region_info = QLabel('')
        self._region_info.setWordWrap(True)
        self._region_info.setStyleSheet(
            f"color:{tokens.DARK['text_dim']};font-size:9px;")
        select_row.addWidget(self._select_btn)
        select_row.addWidget(self._region_info, 1)
        region_layout.addLayout(select_row)

        layout.addWidget(region_box)

        # 预处理 / 置信度 / 分割模式
        layout.addLayout(self._combo_row('预处理', _PREPROCESS, 'preprocess'))
        layout.addLayout(self._numeric_row('最低置信度', 'min_conf'))
        layout.addLayout(self._combo_row('分割模式', _PSMS, 'psm'))

        layout.addStretch(1)

    def _combo_row(self, label, items, prop):
        row = QHBoxLayout()
        lab = QLabel(label)
        combo = QComboBox()
        combo.addItems(items)
        combo.currentTextChanged.connect(
            lambda text: self.node.set_property(prop, text))
        row.addWidget(lab)
        row.addWidget(combo, 1)
        setattr(self, f'_{prop}_combo', combo)
        return row

    def _numeric_row(self, label, prop):
        from PyQt5.QtWidgets import QLineEdit
        row = QHBoxLayout()
        lab = QLabel(label)
        edit = QLineEdit()
        edit.setPlaceholderText('0-100，0 表示不过滤')
        edit.setFixedWidth(70)
        edit.textChanged.connect(
            lambda text: self.node.set_property(prop, text))
        row.addWidget(lab)
        row.addWidget(edit)
        row.addStretch(1)
        setattr(self, f'_{prop}_edit', edit)
        return row

    # ---------------- 数据读写 ----------------
    def _reload_from_node(self):
        """打开属性页时，把节点当前属性同步到控件。"""
        for prop, combo_attr in (('lang', '_lang_combo'),
                                 ('preprocess', '_preprocess_combo'),
                                 ('psm', '_psm_combo')):
            combo = getattr(self, combo_attr, None)
            if combo is None:
                continue
            val = self.node.get_property(prop)
            idx = combo.findText(str(val or ''))
            if idx >= 0:
                combo.setCurrentIndex(idx)
        mode = self.node.get_region_mode()
        idx = self._mode_combo.findText(mode)
        if idx >= 0:
            self._mode_combo.setCurrentIndex(idx)
        conf = self.node.get_property('min_conf')
        self._min_conf_edit.setText(str(conf or '0'))
        self._refresh_region_info()

    def _on_mode_changed(self, mode):
        self.node.set_property('region_mode', mode)
        # 切换模式后原框选语义可能不符，清空并提示
        self.node.set_frame_region('')
        self._refresh_region_info()

    def _refresh_region_info(self):
        mode = self.node.get_region_mode()
        rect = self.node.get_property('region_rect') or ''
        anchor = self.node.get_property('region_anchor') or ''
        if not rect:
            self._region_info.setText('未框选')
        elif mode == '窗口内框选':
            a, b, w, h = self._parse(rect)
            text = f"相对窗口 ({a}, {b}, {w}, {h})"
            if anchor:
                text += f" · 锚点：{anchor}"
            self._region_info.setText(text)
        elif mode == '屏幕框选':
            a, b, w, h = self._parse(rect)
            self._region_info.setText(f"屏幕 ({a}, {b}, {w}, {h})")
        else:
            self._region_info.setText(rect)

    @staticmethod
    def _parse(rect_str):
        parts = (rect_str or '').split(',')
        try:
            return tuple(int(float(p.strip())) for p in parts[:4])
        except ValueError:
            return (0, 0, 0, 0)

    # ---------------- 框选 ----------------
    def _on_pick_region(self):
        mode = self.node.get_region_mode()
        if mode not in ('窗口内框选', '屏幕框选'):
            self._region_info.setText('当前模式无需框选')
            return

        # 最小化主窗口再框选，方便看到全屏
        top = self.window()
        minimizable = top is not None and top is not self
        if minimizable:
            top.showMinimized()
        try:
            rect = RegionSelectPicker.pick()
        finally:
            if minimizable:
                top.showNormal()
                top.raise_()
                top.activateWindow()
        if not rect:
            return

        if mode == '屏幕框选':
            self.node.set_frame_region(
                f"{rect.x()},{rect.y()},{rect.width()},{rect.height()}")
        else:  # 窗口内框选：锚到框选矩形覆盖的窗口，转相对偏移
            win = _window_at_point(rect.center().x(), rect.center().y())
            if win is None:
                _logger.warning('未找到框选区域覆盖的窗口')
                return
            (wl, wt, _wr, _wb), title = win
            dx = rect.x() - wl
            dy = rect.y() - wt
            self.node.set_frame_region(
                f"{dx},{dy},{rect.width()},{rect.height()}", anchor=title)
        self._refresh_region_info()