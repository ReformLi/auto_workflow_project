# -*- coding: utf-8 -*-
"""
node_properties_dialog.py
功能描述: 节点属性页——按节点的声明式属性定义渲染 QFormLayout 弹窗，
         双击节点或右键→属性 唤醒；对带 capture 标记的属性提供"捕获"按钮
         （取色器式：全屏半透明十字准星选择目标窗口，回填标题/类名/进程名）。
"""
import logging

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QHBoxLayout, QLineEdit,
    QLabel, QPushButton, QVBoxLayout, QWidget,
)

from automation.window_manager import WindowManager
from ui import tokens

_logger = logging.getLogger(__name__)
_wm = WindowManager()


class _WindowPicker(QWidget):
    """全屏半透明十字准星窗口选择器：点击捕获目标窗口信息，Esc 取消。"""

    picked = QtCore.pyqtSignal(object)  # dict 或 None

    def __init__(self):
        super(_WindowPicker, self).__init__(
            None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        self._picker_bg = QtGui.QColor(20, 24, 32, 200)

        hint = QLabel("点击目标窗口以捕获其信息，按 Esc 取消", self)
        hint.setStyleSheet(
            f"color:{tokens.DARK['text']};font-size:14px;"
            f"background:{tokens.DARK['bg_elevated']};"
            f"border:1px solid {tokens.DARK['border_strong']};"
            f"border-radius:6px;padding:8px 14px;")
        hint.adjustSize()
        # 居中屏中央偏上
        screen = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        hint.move(screen.center().x() - hint.width() // 2,
                  screen.top() + 60)
        self._hint = hint

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), self._picker_bg)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 先隐藏遮罩再取点，否则 WindowFromPoint 会命中自身
            self.hide()
            QtCore.QCoreApplication.processEvents()
            info = _wm.capture_window_info((event.globalPos().x(),
                                            event.globalPos().y()))
            self._finish(info)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._finish(None)
        else:
            super(_WindowPicker, self).keyPressEvent(event)

    def _finish(self, info):
        self.hide()
        self.picked.emit(info)
        self.close()

    @classmethod
    def pick(cls):
        """阻塞式捕获：返回 dict 或 None（显示选择器直至点击 / Esc）。"""
        picker = cls()
        picker.setGeometry(QtGui.QGuiApplication.primaryScreen().availableGeometry())
        picker.show()

        loop = QtCore.QEventLoop()
        result = {}

        def _on_picked(info):
            result['info'] = info
            loop.quit()

        picker.picked.connect(_on_picked)
        loop.exec_()
        return result.get('info')


class NodePropertiesDialog(QDialog):
    """节点属性页弹窗：渲染节点 get_property_defs() 定义的属性并就地写回节点。"""

    def __init__(self, node, parent=None):
        super(NodePropertiesDialog, self).__init__(parent)
        self.node = node
        self._widgets = {}   # name -> QWidget
        self._defs = node.get_property_defs()

        self.setWindowTitle(f"{node.name()} · 属性")
        self.setMinimumWidth(360)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self._build_ui()
        self._apply_theme()

    def _build_ui(self):
        title = QLabel(f"{self.node.name()} · 属性")
        title.setStyleSheet(
            f"color:{tokens.DARK['text']};font-size:13px;font-weight:bold;")
        hint = QLabel("修改会自动保存到节点")
        hint.setStyleSheet(f"color:{tokens.DARK['text_dim']};font-size:9px;")

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        for d in self._defs:
            self._add_prop_row(form, d)

        ok_btn = QPushButton("确定")
        ok_btn.setStyleSheet(self._accent_button_style())
        ok_btn.clicked.connect(self.accept)
        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(ok_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addLayout(form)
        layout.addLayout(btns)

    def _add_prop_row(self, form, d):
        name, kind, value, items = d['name'], d['kind'], d['value'], d['items']
        if kind == 'combo':
            combo = QComboBox()
            combo.addItems([str(i) for i in (items or [])])
            if value is not None:
                idx = combo.findText(str(value))
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            combo.currentIndexChanged.connect(
                lambda: self.node.set_property(name, combo.currentText()))
            self._widgets[name] = combo
            form.addRow(QLabel(d['label']), combo)
            return

        edit = QLineEdit(str(value) if value is not None else '')
        edit.textChanged.connect(
            lambda text, n=name: self.node.set_property(n, text))
        self._widgets[name] = edit

        if d.get('capture'):
            cap_btn = QPushButton("捕获")
            cap_btn.setCursor(Qt.PointingHandCursor)
            cap_btn.setStyleSheet(self._secondary_button_style())
            cap_btn.setToolTip("点击后选择目标窗口，自动填入标题/类名/进程名")
            cap_btn.clicked.connect(self._on_capture)
            row = QHBoxLayout()
            row.setSpacing(4)
            row.addWidget(edit, 1)
            row.addWidget(cap_btn)
            holder = QWidget()
            holder.setLayout(row)
            form.addRow(QLabel(d['label']), holder)
        else:
            form.addRow(QLabel(d['label']), edit)

    def _set_widget_value(self, name, value):
        w = self._widgets.get(name)
        if w is None:
            return
        if isinstance(w, QComboBox):
            idx = w.findText(str(value))
            if idx >= 0:
                w.setCurrentIndex(idx)
        else:
            w.setText(str(value) if value is not None else '')

    def _on_capture(self):
        top = self.window()
        minimizable = top is not None and top is not self
        if minimizable:
            top.showMinimized()
        try:
            info = _WindowPicker.pick()
        finally:
            if minimizable:
                top.showNormal()
                top.raise_()
                top.activateWindow()
        if not info:
            return
        mapping = {'title': 'title', 'class_name': 'class_name',
                   'process_name': 'process_name'}
        applied = False
        for field in ('title', 'class_name', 'process_name'):
            prop_name = mapping[field]
            if prop_name in self._widgets:
                self._set_widget_value(prop_name, info.get(field, ''))
                self.node.set_property(prop_name, info.get(field, ''))
                applied = True
        if not applied:
            _logger.warning('捕获节点属性页无可回填字段')

    @staticmethod
    def _accent_button_style():
        accent = tokens.DARK['accent']
        accent_h = tokens.DARK['accent_hover']
        return (f"QPushButton {{ background:{accent}; color:#ffffff;"
                f"border:none; border-radius:4px; padding:5px 14px; }}"
                f"QPushButton:hover {{ background:{accent_h}; }}")

    def _secondary_button_style(self):
        elev = tokens.DARK['bg_elevated']
        border = tokens.DARK['border_strong']
        text = tokens.DARK['text']
        return (f"QPushButton {{ background:{elev}; color:{text};"
                f"border:1px solid {border}; border-radius:4px;"
                f"padding:4px 12px; }}"
                f"QPushButton:hover {{ background:{tokens.DARK['bg_hover']}; }}")

    def _apply_theme(self):
        bg = tokens.DARK['bg_window']
        elev = tokens.DARK['bg_elevated']
        border = tokens.DARK['border_strong']
        text = tokens.DARK['text']
        accent = tokens.DARK['accent']
        self.setStyleSheet(f"""
            QDialog {{ background:{bg}; }}
            QLabel {{ color:{text}; font-size:{tokens.FONT_SIZE_UI}pt; }}
            QLineEdit, QComboBox {{
                background:{elev}; color:{text};
                border:1px solid {border}; border-radius:4px;
                padding:4px 6px; min-height:22px;
            }}
            QLineEdit:focus, QComboBox:focus {{ border:1px solid {accent}; }}
            QComboBox::drop-down {{ border:none; width:18px; }}
        """)