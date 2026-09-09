# -*- coding: utf-8 -*-
"""
node_properties_panel.py
功能描述: 节点属性面板——内嵌在主窗口右侧的属性编辑区（取代独立属性窗口）
         - 默认隐藏；双击节点 / 右键→属性 唤醒
         - 面板可见时单击选中其他节点切换内容，点击画布空白处整体隐藏
         - 就地写回 + 「还原」按钮回滚到选中时刻的快照
         - 图片 / OCR / 鼠标 / 子工作流节点由专用编辑器接管（同原属性弹窗）
         见 UI_DESIGN.md §10.2（属性对话框改造为面板）
"""
import logging

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLineEdit,
    QLabel, QPushButton, QVBoxLayout, QWidget, QScrollArea,
)

from automation.window_manager import WindowManager
from ui import icons, qss, tokens

_logger = logging.getLogger(__name__)
_wm = WindowManager()

_EMPTY_TIP = "双击节点或在节点上右键 → 属性\n即可在此编辑节点配置"


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


class NodePropertiesPanel(QWidget):
    """
    节点属性面板（主窗口右侧内嵌）。

    - show_node(node): 选中/双击/右键属性时显示该节点的配置（就地写回）
    - clear_node():    清空面板（画布空白点击时）
    - 「还原」按钮:     回滚到该节点被选中时刻的快照
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('propertiesPanel')
        self.node = None
        self._widgets = {}       # name -> QWidget
        self._snapshot = {}      # 选中时刻的属性快照（「还原」用）
        self._editor = None      # 图片/OCR/鼠标专用编辑器
        # 常驻布局：内容切换只换子项，不重建布局本身
        host_layout = QVBoxLayout(self)
        host_layout.setContentsMargins(10, 10, 10, 10)
        host_layout.setSpacing(8)
        self.setMinimumWidth(260)
        self._build_empty()

    # ── 对外接口 ────────────────────────────────────────
    def show_node(self, node):
        """显示指定节点的属性（同一节点重复选中不重建）。"""
        if node is None:
            self.clear_node()
            return
        if self.node is node and getattr(self, '_built_for', None) is node:
            return

        self._detach_editor()
        self._clear_layout()
        self.node = node
        self._widgets = {}
        self._defs = node.get_property_defs()
        self._snapshot = {d['name']: node.get_property(d['name'])
                          for d in self._defs if d['name'] != '_custom'}
        self._build_content()
        self._built_for = node

    def clear_node(self):
        """清空面板回到空态（画布空白点击 / 节点删除时调用）。"""
        if self.node is None and self._editor is None:
            return
        self._detach_editor()
        self._clear_layout()
        self.node = None
        self._widgets = {}
        self._snapshot = {}
        self._built_for = None
        self._build_empty()

    def _clear_layout(self):
        """
        清空面板内容：只移除布局里的控件与子布局，布局本身常驻复用。

        两点教训：
        1) 不能 `QWidget().setLayout(old)`——临时控件无父级即顶层窗口，
           搬入可见子控件时会闪一下（就是那个一闪而过的小弹框）；
        2) 也不能把布局从面板上摘掉——之后 `QVBoxLayout(self)` 会因
           "已有布局"被 Qt 拒绝，新内容全成孤儿、面板停在旧状态。
        """
        layout = self.layout()
        if layout is not None:
            self._take_out(layout)

    @staticmethod
    def _take_out(layout):
        """递归取出布局内的全部控件与子布局并安全销毁。"""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # 必须先 hide：可见控件 setParent(None) 会立刻变成无框顶层
                # 窗口留在屏幕上一帧（deleteLater 要到下个事件循环才执行），
                # 这就是切换节点时"瞬间闪现的弹框"
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
                continue
            sub = item.layout()
            if sub is not None:
                NodePropertiesPanel._take_out(sub)
                sub.setParent(None)
                sub.deleteLater()

    # ── 构建 ────────────────────────────────────────────
    def _build_empty(self):
        layout = self.layout()
        tip = QLabel(_EMPTY_TIP)
        tip.setAlignment(Qt.AlignCenter)
        tip.setWordWrap(True)
        tip.setStyleSheet(f"color:{tokens.DARK['text_dim']};")
        layout.addStretch(2)
        layout.addWidget(tip)
        layout.addStretch(3)

    def _build_content(self):
        layout = self.layout()

        # 标题行：分类色图标块 + 节点名 + 还原按钮
        header = QHBoxLayout()
        header.setSpacing(6)
        icon_label = QLabel()
        icon_label.setPixmap(self._header_pixmap())
        icon_label.setFixedSize(20, 20)
        title = QLabel(self.node.name())
        title.setStyleSheet(
            f"color:{tokens.DARK['text']};font-weight:bold;")
        restore_btn = QPushButton("还原")
        restore_btn.setCursor(Qt.PointingHandCursor)
        restore_btn.setToolTip("还原到选中该节点时的配置")
        restore_btn.setStyleSheet(self._secondary_button_style())
        restore_btn.clicked.connect(self._restore)
        # 编辑器接管节点（图片/OCR/鼠标）的属性不在表单快照内，还原无效 → 隐藏
        has_form_props = any(d['name'] != '_custom' for d in self._defs)
        restore_btn.setVisible(has_form_props)
        header.addWidget(icon_label)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(restore_btn)
        layout.addLayout(header)

        # 通用表单（跳过 _custom 占位定义）。等待图片这类节点既有专用编辑器
        # 又有自己的属性（超时/轮询间隔），表单与编辑器可共存。
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._vis_rows = []
        has_rows = False
        for d in self._defs:
            if d['name'] == '_custom':
                continue        # 专用编辑器节点的占位定义，不渲染通用表单行
            row = self._add_prop_row(d)
            if row is None:
                continue
            has_rows = True
            label_w, field_w = row
            if label_w is None:                      # 独占整行（复选框等）
                form.addRow(field_w)
            else:
                form.addRow(label_w, field_w)
                if d.get('vis_when'):
                    self._vis_rows.append((d['vis_when'], label_w, field_w))
        self._wire_visibility()

        editor = None
        if getattr(self.node, 'IMAGE_NODE', False):
            from ui.node_image_widget import ImageNodeEditor
            editor = ImageNodeEditor(self.node, self)
        elif getattr(self.node, 'OCR_NODE', False):
            from ui.node_ocr_widget import OcrNodeEditor
            editor = OcrNodeEditor(self.node, self)
        elif getattr(self.node, 'MOUSE_NODE', False):
            from ui.node_mouse_widget import MouseClickEditor
            editor = MouseClickEditor(self.node, self)
        elif getattr(self.node, 'SUBFLOW_NODE', False):
            from ui.node_subflow_widget import SubflowNodeEditor
            editor = SubflowNodeEditor(self.node, self)
        self._editor = editor

        # 表单与编辑器统一装进一个上下滚动容器：面板固定宽、内容超高即滚动，
        # 不再要求内容适配面板高度
        body = QVBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(6)
        if has_rows:
            body.addLayout(form)
        if editor is not None:
            body.addWidget(editor)
        host = QWidget()
        host.setLayout(body)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(host)
        layout.addWidget(scroll, 1)

    def _detach_editor(self):
        """切换/清空前：等待编辑器后台线程结束，避免运行中销毁导致崩溃。"""
        ed = self._editor
        thread = getattr(ed, '_thread', None) if ed is not None else None
        if thread is not None and thread.isRunning():
            thread.wait(3000)
        if ed is not None:
            ed.hide()               # 先隐藏，防止 setParent(None) 闪现顶层窗口
            ed.setParent(None)
            ed.deleteLater()
        self._editor = None

    def _header_pixmap(self):
        category = getattr(self.node, 'NODE_CATEGORY', None) or ''
        icon_name = (getattr(self.node, 'NODE_ICON', None)
                     or tokens.category_icon(category))
        return icons.tile_pixmap(icon_name, tokens.category_color(category),
                                 size=20, radius=5)

    # ── 属性行渲染 ──────────────────────────────────────
    def _add_prop_row(self, d):
        """渲染一个属性行，返回 (label, field)；label 为 None 表示独占整行。"""
        name, kind, value, items = d['name'], d['kind'], d['value'], d['items']

        if kind == 'check':
            cb = QCheckBox(d['label'])
            cb.setChecked(str(value) in ('1', 'true', 'True'))
            cb.toggled.connect(
                lambda on, n=name: self.node.set_property(n, '1' if on else '0'))
            self._widgets[name] = cb
            return None, cb                          # 独占整行

        label_w = QLabel(d['label'])
        label_w.setWordWrap(True)
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
            field_w = combo
        elif d.get('multiline'):
            from PyQt5.QtWidgets import QPlainTextEdit
            container = QWidget()
            vbox = QVBoxLayout(container)
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(4)
            edit = QPlainTextEdit(str(value) if value is not None else '')
            edit.setMinimumHeight(90)
            edit.textChanged.connect(
                lambda: self.node.set_property(name, edit.toPlainText()))
            self._widgets[name] = edit
            vbox.addWidget(edit)
            if d.get('templates'):
                # 2 列网格排布（窄面板下 4 个按钮一行会被裁）
                from PyQt5.QtWidgets import QGridLayout
                tgrid = QGridLayout()
                tgrid.setSpacing(4)
                for idx, (tlabel, tpl) in enumerate(d['templates']):
                    btn = QPushButton(tlabel)
                    btn.setCursor(Qt.PointingHandCursor)
                    btn.setStyleSheet(self._secondary_button_style())
                    btn.clicked.connect(
                        lambda _=False, t=tpl: edit.setPlainText(t))
                    tgrid.addWidget(btn, idx // 2, idx % 2)
                vbox.addLayout(tgrid)
            field_w = container
        else:
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
                field_w = holder
            else:
                field_w = edit

        return label_w, field_w

    def _wire_visibility(self):
        """根据 mode 组合框的值联动显隐（vis_when=(mode属性, 期望值)）的字段行。"""
        for (mode_prop, expected), label_w, field_w in self._vis_rows:
            mode_w = self._widgets.get(mode_prop)
            if not isinstance(mode_w, QComboBox):
                continue

            def sync(mp=mode_prop, exp=expected, lw=label_w, fw=field_w, mw=mode_w):
                visible = mw.currentText() == exp
                lw.setVisible(visible)
                fw.setVisible(visible)

            mode_w.currentIndexChanged.connect(lambda _=None: sync())
            sync()  # 初始按当前值设置

    # ── 还原 / 捕获 ────────────────────────────────────
    def _restore(self):
        """把属性回滚到选中该节点时刻的快照。"""
        if self.node is None:
            return
        for name, value in self._snapshot.items():
            if name == '_custom':
                continue
            self.node.set_property(name, value)
        # 同步控件显示（部分控件不直接监听模型）
        for name, value in self._snapshot.items():
            w = self._widgets.get(name)
            if w is None:
                continue
            if isinstance(w, QComboBox):
                idx = w.findText(str(value))
                if idx >= 0:
                    w.setCurrentIndex(idx)
            elif hasattr(w, 'toPlainText'):
                w.setPlainText(str(value) if value is not None else '')
            elif isinstance(w, QCheckBox):
                w.setChecked(str(value) in ('1', 'true', 'True'))
            else:
                w.setText(str(value) if value is not None else '')

    def _set_widget_value(self, name, value):
        w = self._widgets.get(name)
        if w is None:
            return
        if isinstance(w, QComboBox):
            idx = w.findText(str(value))
            if idx >= 0:
                w.setCurrentIndex(idx)
        elif hasattr(w, 'toPlainText'):
            w.setPlainText(str(value) if value is not None else '')
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
        applied = False
        for field in ('title', 'class_name', 'process_name'):
            if field in self._widgets:
                self._set_widget_value(field, info.get(field, ''))
                self.node.set_property(field, info.get(field, ''))
                applied = True
        if not applied:
            _logger.warning('捕获节点属性面板无可回填字段')

    # ── 编辑器依赖的样式辅助 ────────────────────────────
    def _accent_button_style(self):
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
