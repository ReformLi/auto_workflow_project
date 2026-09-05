# -*- coding: utf-8 -*-
"""
node_image_widget.py
功能描述: 查找图片节点的属性编辑器（ImageNodeEditor）——
         图片粘贴/拖拽/浏览预览、模板匹配与颜色定位模式切换、阈值/偏移、
         颜色点采集、"测试识别"（后台线程，避免卡顿 UI）。
"""
import base64
import json
import logging

import cv2

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout,
    QWidget, QDoubleSpinBox, QFileDialog, QGridLayout, QCheckBox, QComboBox,
)

from automation.image_finder import ImageFinder
from ui import tokens

_logger = logging.getLogger(__name__)
_finder = ImageFinder()


# =============================================================
# 多点颜色采集器（全屏半透明十字准星，左键采点、右键/Esc 结束）
# =============================================================
class PointColorPicker(QWidget):
    """
    采集屏幕上的多个点：每个点记录屏幕坐标与颜色。
    结束信号：points=[{sx, sy, r, g, b}]（先后顺序）。
    """
    finished = QtCore.pyqtSignal(list)

    def __init__(self):
        super(PointColorPicker, self).__init__(
            None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)
        self._bg = QtGui.QColor(20, 24, 32, 190)
        self._points = []
        self._hint = None

    def _refresh_hint(self):
        hint = QLabel(
            f"当前已采集 {len(self._points)} 个点 · 左键添加 / 加号追加：左键继续 · 右键或 Esc 结束", self)
        hint.setStyleSheet(
            f"color:{tokens.DARK['text']};font-size:14px;"
            f"background:{tokens.DARK['bg_elevated']};"
            f"border:1px solid {tokens.DARK['border_strong']};"
            f"border-radius:6px;padding:8px 14px;")
        hint.adjustSize()
        screen = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        hint.move(screen.center().x() - hint.width() // 2, screen.top() + 40)
        if self._hint:
            self._hint.setParent(None)
            self._hint.deleteLater()
        hint.show()
        self._hint = hint

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_hint()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), self._bg)
        pen = QtGui.QPen(QtGui.QColor('#4c8dff'), 1)
        painter.setPen(pen)
        for p in self._points:
            painter.drawEllipse(p['sx'] - 4, p['sy'] - 4, 8, 8)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            sx, sy = event.globalPos().x(), event.globalPos().y()
            rgb = _finder.pixel_bgr((sx, sy))
            if rgb:
                b, g, r = rgb
                self._points.append({'sx': sx, 'sy': sy, 'r': r, 'g': g, 'b': b})
                self._refresh_hint()
                self.update()
        elif event.button() == Qt.RightButton:
            self._finish()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._finish()
        else:
            super(PointColorPicker, self).keyPressEvent(event)

    def _finish(self):
        self.hide()
        self.finished.emit(list(self._points))


# =============================================================
# 屏幕区域裁剪采集器（十字准星，左键拖拽框选，右键/Esc 取消）
# =============================================================
class RegionCapturePicker(QWidget):
    """在屏幕上框选一片区域作为模板图片。结果信号：finished(pixmap | None)。"""
    finished = QtCore.pyqtSignal(object)

    def __init__(self):
        super(RegionCapturePicker, self).__init__(
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
            # 露出选区、绘制描边
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
            painter.fillRect(self._rect, Qt.transparent)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
            pen = QtGui.QPen(QtGui.QColor('#4c8dff'), 1)
            painter.setPen(pen)
            painter.drawRect(self._rect)
            hint = "释放鼠标完成截图，右键或 Esc 取消"
            painter.setPen(QtGui.QColor('#e8eaed'))
            painter.drawText(self._rect.x(), self._rect.y() - 6, hint)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._origin = event.pos()
            self._rect = None
        elif event.button() == Qt.RightButton:
            self._finish(None)

    def mouseMoveEvent(self, event):
        if self._origin is not None:
            self._rect = self._rect_normalized(event.pos())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._origin is not None:
            self._rect = self._rect_normalized(event.pos())
            # 先隐藏遮罩再截图，否则画面被半透明覆盖
            self.hide()
            QtCore.QCoreApplication.processEvents()
            self._finish(self._snapshot())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._finish(None)
        else:
            super(RegionCapturePicker, self).keyPressEvent(event)

    def _rect_normalized(self, pos):
        r = QtCore.QRect(self._origin, pos)
        return r.normalized()

    def _snapshot(self):
        r = self._rect
        if r is None or r.isEmpty():
            return None
        try:
            import numpy as np
            import pyautogui
            region = (r.x(), r.y(), r.width(), r.height())
            pil = pyautogui.screenshot(region=region)
            rgb = np.array(pil)                 # HxWx3, RGB
            h, w = rgb.shape[:2]
            img = QtGui.QImage(rgb.data, w, h, rgb.strides[0],
                               QtGui.QImage.Format_RGB888)
            pixmap = QtGui.QPixmap.fromImage(img).copy()  # copy 避免数据释放
            return pixmap
        except Exception:
            return None

    def _finish(self, pixmap):
        self.hide()
        self.finished.emit(pixmap)


class _TestThread(QtCore.QThread):
    """后台执行测试识别，避免阻塞属性页 UI。结果信号返回 dict。"""
    done = QtCore.pyqtSignal(dict)

    def __init__(self, node):
        super(_TestThread, self).__init__()
        self.node = node

    @staticmethod
    def _pp(img, mode):
        """应用灰度/二值化预处理，与执行引擎保持一致。"""
        if mode == '灰度':
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if mode == '二值化':
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, th = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            return th
        return img

    def run(self):
        try:
            result = self._run_test()
        except Exception as e:
            result = {'ok': False, 'text': f'测试出错：{e}', 'thumb': None}
        self.done.emit(result)

    def _run_test(self):
        mode = self.node.get_property('mode') or '模板匹配'
        if mode == '颜色定位':
            pts = self.node.get_colored_points()
            if not pts:
                return {'ok': False, 'text': '尚未采集颜色点', 'thumb': None}
            try:
                tolerance = int(float(self.node.get_property('tolerance') or '40'))
            except (TypeError, ValueError):
                tolerance = 40
            hits = _finder.find_color_points(pts, tolerance=tolerance)
            if not hits:
                return {'ok': False, 'text': f'未找到匹配的颜色点组合（容差 {tolerance}）',
                        'thumb': None}
            best = hits[0]
            cx, cy = best['base_center']
            dev = best['max_dev']
            return {'ok': True,
                    'text': f"匹配度：{1.0 - dev / 255.0:.2f}　坐标：( {cx}, {cy} )"
                            f"（对齐第 1 个点）",
                    'thumb': None}
        # 模板匹配
        template = self.node.get_template()
        if template is None:
            return {'ok': False, 'text': '未设置模板图片', 'thumb': None}
        try:
            threshold = float(self.node.get_property('threshold') or 0.8)
        except (TypeError, ValueError):
            threshold = 0.8
        pre = self.node.get_property('preprocess') or '无'
        if pre != '无':
            screen = _finder.capture_screen()
            results = _finder.match_from_array(
                self._pp(screen, pre), self._pp(template, pre), threshold)
        else:
            results = _finder.find_on_screen_array(template, threshold)
        if not results:
            return {'ok': False, 'text': f'未找到匹配（阈值 {threshold:.2f}）', 'thumb': None}
        best = results[0]
        cx, cy = best['center']
        screen = _finder.capture_screen()
        tw, th = best['size']
        tl = best['top_left']
        thumb = screen[tl[1]:tl[1] + th, tl[0]:tl[0] + tw]
        return {'ok': True,
                'text': f"匹配度：{best['max_val']:.2f}　坐标：( {cx}, {cy} )",
                'thumb': thumb}


class ImageNodeEditor(QGroupBox):
    """查找图片节点的属性面板：模板预览/来源、模式、阈值/偏移、颜色采集、测试识别。"""

    def __init__(self, node, dialog, parent=None):
        super(ImageNodeEditor, self).__init__("图片属性", parent)
        self.node = node
        self.dialog = dialog
        self.setStyleSheet("QGroupBox { font-weight:bold; } "
                           "QGroupBox > QWidget { font-weight:normal; }")
        self._build_ui()
        self._load_state()

    # ---------------- UI 构建 ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        root.addLayout(self._mode_row())

        # 模板匹配区域
        self.template_box = QGroupBox("模板图片")
        tbox = QVBoxLayout(self.template_box)
        tbox.setContentsMargins(6, 6, 6, 6)
        tbox.setSpacing(6)
        self.preview = QLabel("可拖入图片、粘贴(Ctrl+V)或浏览…")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setFixedSize(140, 140)
        self.preview.setStyleSheet(self._preview_style())
        self.preview.setAcceptDrops(True)
        self.preview.setWordWrap(True)
        self.preview.setScaledContents(False)
        self.preview.dragEnterEvent = self._on_drag_enter
        self.preview.dropEvent = self._on_drop
        btns = QHBoxLayout()
        self.btn_browse = QPushButton("浏览…")
        self.btn_paste = QPushButton("粘贴")
        self.btn_capture_region = QPushButton("截屏…")
        self.btn_clear = QPushButton("清除")
        for b in (self.btn_browse, self.btn_paste, self.btn_capture_region,
                  self.btn_clear):
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(self.dialog._secondary_button_style())
        self.btn_browse.clicked.connect(self._on_browse)
        self.btn_paste.clicked.connect(self._on_paste)
        self.btn_capture_region.clicked.connect(self._on_capture_region)
        self.btn_clear.clicked.connect(self._on_clear)
        btns.addWidget(self.btn_browse)
        btns.addWidget(self.btn_paste)
        btns.addWidget(self.btn_capture_region)
        btns.addWidget(self.btn_clear)
        btns.addStretch(1)
        tbox.addWidget(self.preview, 0, Qt.AlignHCenter)
        tbox.addLayout(btns)
        root.addWidget(self.template_box)

        # 颜色定位区域
        self.color_box = QGroupBox("颜色定位")
        cbox = QVBoxLayout(self.color_box)
        cbox.setContentsMargins(6, 6, 6, 6)
        cbox.setSpacing(6)
        self.point_dots = QLabel()
        self.point_dots.setFixedHeight(56)
        self.point_dots.setStyleSheet(self._preview_style())
        self.point_dots.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.point_count = QLabel("未采集")
        self.point_count.setStyleSheet(
            f"color:{tokens.DARK['text_dim']};font-size:9pt;")
        self.btn_capture = QPushButton("开始采集（左键加点，右键结束）")
        self.btn_clear_pts = QPushButton("清除要点")
        for b in (self.btn_capture, self.btn_clear_pts):
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(self.dialog._secondary_button_style())
        self.btn_capture.clicked.connect(self._on_capture)
        self.btn_clear_pts.clicked.connect(self._on_clear_points)
        crow = QHBoxLayout()
        crow.addWidget(self.btn_capture)
        crow.addWidget(self.btn_clear_pts)
        crow.addStretch(1)
        cbox.addWidget(self.point_dots)
        cbox.addWidget(self.point_count)
        cbox.addLayout(crow)
        tol_row = QHBoxLayout()
        tol_row.addWidget(QLabel("容差"))
        self.tolerance_spin = QSpinBox()
        self.tolerance_spin.setRange(0, 255)
        self.tolerance_spin.setValue(40)
        self.tolerance_spin.setToolTip("逐通道颜色偏差允许范围（0-255）")
        self.tolerance_spin.valueChanged.connect(self._on_tolerance)
        tol_row.addWidget(self.tolerance_spin)
        tol_row.addStretch(1)
        cbox.addLayout(tol_row)
        root.addWidget(self.color_box)

        # 参数：阈值 / 偏移
        param = QHBoxLayout()
        param.addWidget(QLabel("阈值"))
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.0, 1.0)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setValue(0.8)
        self.threshold_spin.valueChanged.connect(self._on_threshold)
        param.addWidget(self.threshold_spin)
        param.addSpacing(12)
        param.addWidget(QLabel("偏移 X"))
        self.offset_x = QSpinBox()
        self.offset_x.setRange(-2000, 2000)
        self.offset_x.valueChanged.connect(
            lambda v: self.node.set_property('offset_x', str(v)))
        param.addWidget(self.offset_x)
        param.addWidget(QLabel("Y"))
        self.offset_y = QSpinBox()
        self.offset_y.setRange(-2000, 2000)
        self.offset_y.valueChanged.connect(
            lambda v: self.node.set_property('offset_y', str(v)))
        param.addWidget(self.offset_y)
        param.addStretch(1)
        root.addLayout(param)

        # 预处理 + 命中后自动点击
        opt = QHBoxLayout()
        opt.addWidget(QLabel("预处理"))
        self.preprocess_combo = QComboBox()
        self.preprocess_combo.addItems(['无', '灰度', '二值化'])
        self.preprocess_combo.currentTextChanged.connect(self._on_preprocess)
        self.preprocess_combo.setToolTip("灰度/二值化可增强特定场景的匹配效果")
        opt.addWidget(self.preprocess_combo)
        opt.addSpacing(16)
        self.click_after = QCheckBox("命中后自动点击")
        self.click_after.setToolTip("识别成功后自动在偏移后的中心坐标处点击")
        self.click_after.setCursor(Qt.PointingHandCursor)
        self.click_after.stateChanged.connect(self._on_click_after)
        opt.addWidget(self.click_after)
        opt.addStretch(1)
        root.addLayout(opt)

        # 后台离屏识别（PrintWindow）
        bg_row = QHBoxLayout()
        self.bg_check = QCheckBox("后台离屏识别（PrintWindow 抓取目标窗口内容）")
        self.bg_check.setToolTip(
            "开启后使用 PrintWindow 离屏抓取「窗口对象」输入端口对应窗口的内容，"
            "即使窗口被遮挡/最小化也能识别；输出坐标为【相对窗口客户区】坐标，"
            "可直接连入「鼠标点击」的 coords（配合相对客户区 + 后台执行）。")
        self.bg_check.setCursor(Qt.PointingHandCursor)
        self.bg_check.stateChanged.connect(self._on_bg_toggle)
        bg_row.addWidget(self.bg_check)
        bg_row.addStretch(1)
        root.addLayout(bg_row)

        # 测试识别
        self.btn_test = QPushButton("测试识别（在当前屏幕执行匹配）")
        self.btn_test.setCursor(Qt.PointingHandCursor)
        self.btn_test.setStyleSheet(self.dialog._accent_button_style())
        self.btn_test.clicked.connect(self._on_test)
        root.addWidget(self.btn_test, 0, Qt.AlignHCenter)
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet(
            f"color:{tokens.DARK['text_2nd']};font-size:9pt;")
        root.addWidget(self.result_label)
        self.thumb_label = QLabel()
        self.thumb_label.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.thumb_label, 0, Qt.AlignHCenter)

    def _mode_row(self):
        row = QHBoxLayout()
        row.addWidget(QLabel("模式"))
        from PyQt5.QtWidgets import QComboBox
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(['模板匹配', '颜色定位'])
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        row.addWidget(self.mode_combo)
        row.addStretch(1)
        return row

    # ---------------- 样式 ----------------
    @staticmethod
    def _preview_style():
        return (f"background:{tokens.DARK['bg_elevated']};"
                f"border:1px dashed {tokens.DARK['border_strong']};"
                f"border-radius:6px;color:{tokens.DARK['text_dim']};"
                f"font-size:9pt;padding:4px;")

    # ---------------- 状态同步 ----------------
    def _load_state(self):
        mode = self.node.get_property('mode') or '模板匹配'
        self.mode_combo.setCurrentText(mode)
        try:
            self.threshold_spin.setValue(float(self.node.get_property('threshold') or 0.8))
        except (TypeError, ValueError):
            pass
        try:
            self.offset_x.setValue(int(float(self.node.get_property('offset_x') or 0)))
            self.offset_y.setValue(int(float(self.node.get_property('offset_y') or 0)))
        except (TypeError, ValueError):
            pass
        try:
            self.tolerance_spin.setValue(
                int(float(self.node.get_property('tolerance') or '40')))
        except (TypeError, ValueError):
            pass
        pre = self.node.get_property('preprocess') or '无'
        if pre in ('无', '灰度', '二值化'):
            self.preprocess_combo.setCurrentText(pre)
        self.click_after.setChecked(
            (self.node.get_property('click_after') or '0') in ('1', 'true', 'yes'))
        self.bg_check.setChecked(
            (self.node.get_property('bg_mode') or '0') in ('1', 'true', 'yes'))
        self.refresh()
        self._on_mode_changed(mode)

    def _on_mode_changed(self, mode):
        self.template_box.setVisible(mode == '模板匹配')
        self.color_box.setVisible(mode == '颜色定位')
        self.preprocess_combo.setEnabled(mode == '模板匹配')
        self.node.set_property('mode', mode)

    def refresh(self):
        """刷新预览与颜色点展示。"""
        # 模板预览
        self._refresh_preview()
        # 颜色点展示
        pts = self.node.get_colored_points()
        if pts:
            dots = '<span style="margin-left:6px;">'
            for i, p in enumerate(pts):
                col = f"rgb({p['r']},{p['g']},{p['b']})"
                dots += (f"<span style='display:inline-block;margin:2px;"
                         f"width:16px;height:16px;border-radius:8px;"
                         f"background:{col};border:1px solid #555;'></span>")
            dots += '</span>'
            rel = ','.join(
                '({},{})'.format(p.get('dx', 0), p.get('dy', 0))
                for p in pts[1:]) or '仅1点'
            self.point_dots.setText(dots)
            self.point_count.setText("{} 个点（相对第1个点：{}）".format(len(pts), rel))
            self.point_dots.setVisible(True)
        else:
            self.point_dots.setText("未采集颜色点")
            self.point_dots.setVisible(True)
            self.point_count.setText("点击「开始采集」依次采集 ≥1 个点")

    def _refresh_preview(self):
        data = self.node.get_property('template_data')
        path = self.node.get_property('template_path')
        pixmap = None
        if data:
            try:
                raw = base64.b64decode(data)
                pixmap = QtGui.QPixmap()
                pixmap.loadFromData(raw)
            except Exception:
                pixmap = None
        elif path:
            pixmap = QtGui.QPixmap(path)
        if pixmap and not pixmap.isNull():
            p = pixmap.scaled(
                128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview.setPixmap(p)
            self.preview.setToolTip(path or "内嵌图片")
        else:
            self.preview.setText("可拖入图片、粘贴(Ctrl+V)或浏览…")
            self.preview.setPixmap(QtGui.QPixmap())

    # ---------------- 图片来源 ----------------
    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择模板图片", "", "图片 (*.png *.jpg *.jpeg *.bmp)")
        if not path:
            return
        self.node.set_image_source(path=path, data='')
        self.refresh()

    def _on_paste(self):
        img = QtGui.QGuiApplication.clipboard().image()
        if img.isNull():
            self.result_label.setText("剪贴板中没有图片")
            return
        buf = QtCore.QBuffer()
        buf.open(QtCore.QIODevice.WriteOnly)
        img.save(buf, 'PNG')
        data = base64.b64encode(buf.data()).decode('ascii')
        self.node.set_image_source(path='', data=data)
        self.refresh()

    def _on_clear(self):
        self.node.set_image_source(path='', data='')
        self.refresh()

    def _on_capture_region(self):
        """框选屏幕区域作为模板并存储为内嵌 Base64。"""
        top = self.dialog.window()
        if top is not None and top is not self.dialog:
            top.showMinimized()
        picker = RegionCapturePicker()
        picker.setGeometry(
            QtGui.QGuiApplication.primaryScreen().availableGeometry())
        picker.show()
        loop = QtCore.QEventLoop()
        store = {}

        def _on_finish(img):
            store['img'] = img
            loop.quit()

        picker.finished.connect(_on_finish)
        loop.exec_()
        if top is not None and top is not self.dialog:
            top.showNormal()
            top.raise_()
            top.activateWindow()
        pixmap = store.get('img')
        if pixmap is None or pixmap.isNull():
            return
        buf = QtCore.QBuffer()
        buf.open(QtCore.QIODevice.WriteOnly)
        pixmap.save(buf, 'PNG')
        data = base64.b64encode(buf.data()).decode('ascii')
        self.node.set_image_source(path='', data=data)
        self.refresh()

    def _on_drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _on_drop(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self.node.set_image_source(path=path, data='')
                self.refresh()

    # ---------------- 颜色采集 ----------------
    def _on_capture(self):
        top = self.dialog.window()
        if top is not None and top is not self.dialog:
            top.showMinimized()
        picker = PointColorPicker()
        picker.setGeometry(QtGui.QGuiApplication.primaryScreen().availableGeometry())
        picker.show()
        loop = QtCore.QEventLoop()
        store = {}

        def _on_finish(raw_points):
            store['pts'] = raw_points
            loop.quit()

        picker.finished.connect(_on_finish)
        loop.exec_()
        raw = store.get('pts') or []
        if top is not None and top is not self.dialog:
            top.showNormal()
            top.raise_()
            top.activateWindow()
        if not raw:
            return
        # 相对坐标以第一个点为基准
        bx, by = raw[0]['sx'], raw[0]['sy']
        points = []
        for p in raw:
            points.append({
                'dx': p['sx'] - bx, 'dy': p['sy'] - by,
                'r': p['r'], 'g': p['g'], 'b': p['b'],
            })
        self.node.set_colored_points(points)
        self.refresh()

    def _on_clear_points(self):
        self.node.set_colored_points([])
        self.refresh()

    # ---------------- 参数 ----------------
    def _on_threshold(self, value):
        self.node.set_property('threshold', str(round(value, 2)))

    def _on_tolerance(self, value):
        self.node.set_property('tolerance', str(value))

    def _on_preprocess(self, text):
        self.node.set_property('preprocess', text)

    def _on_click_after(self, state):
        self.node.set_property('click_after', '1' if state == Qt.Checked else '0')

    def _on_bg_toggle(self, state):
        self.node.set_property('bg_mode', '1' if state == Qt.Checked else '0')

    # ---------------- 测试识别 ----------------
    def _on_test(self):
        self.btn_test.setEnabled(False)
        self.btn_test.setText("识别中…")
        self.thumb_label.clear()
        self._thread = _TestThread(self.node)
        self._thread.done.connect(self._on_test_done)
        self._thread.start()

    def _on_test_done(self, result):
        self.btn_test.setEnabled(True)
        self.btn_test.setText("测试识别（在当前屏幕执行匹配）")
        if result['ok']:
            self.result_label.setStyleSheet(
                f"color:{tokens.DARK['success']};font-size:9pt;")
        else:
            self.result_label.setStyleSheet(
                f"color:{tokens.DARK['error']};font-size:9pt;")
        self.result_label.setText(result.get('text', ''))
        thumb = result.get('thumb')
        if thumb is not None and thumb.size:
            import cv2
            from PyQt5.QtGui import QImage
            rgb = cv2.cvtColor(thumb, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            img = QImage(rgb.data, w, h, rgb.strides[0],
                         QImage.Format_RGB888)
            self.thumb_label.setPixmap(
                QtGui.QPixmap.fromImage(img).scaled(
                    120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))