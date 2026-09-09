# -*- coding: utf-8 -*-
"""
mouse_nodes.py
功能描述: 鼠标点击节点（MouseClickNode，显示名「鼠标点击」）。
- 多按键（左/右/中）、单击/双击、双击间隔。
- 坐标来源优先级：coords 输入端口（tuple/dict） > 手动（pos_x/pos_y，含捕获回填）。
- 绝对屏幕 / 相对窗口客户区坐标，可加偏移。
- 执行模式：自动 / 前台 / 后台（后台用 PostMessage 合成，需 window 端口提供句柄）。
- 前置/后置等待、前台移动选项、调试红点标记。
属性页由自定义编辑器 MouseClickEditor 接管（见 ui/node_mouse_widget.py）。
"""
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QApplication, QWidget

from automation.mouse_controller import MouseController
from nodes.base_node import WorkflowNode

mouse_ctrl = MouseController(default_delay=0.05)

_BUTTONS = ['左键', '右键', '中键']
_BUTTON_CODE = {'左键': 'left', '右键': 'right', '中键': 'middle'}
_CLICK_TYPES = ['单击', '双击']
_COORD_MODES = ['绝对屏幕', '相对窗口客户区']
_EXEC_MODES = ['自动', '前台', '后台']


class _ClickMarker(QWidget):
    """全屏透明红点标记（不拦截鼠标事件），用于点击前可视化确认位置。"""

    def __init__(self, x, y):
        super(_ClickMarker, self).__init__(
            None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setGeometry(QApplication.primaryScreen().availableGeometry())
        self._pos = (int(x), int(y))

    def paintEvent(self, event):
        painter = QPainter(self)
        pen = painter.pen()
        pen.setWidth(3)
        pen.setColor(QColor('#ff3b30'))
        painter.setPen(pen)
        painter.setBrush(QColor(255, 59, 48, 120))
        x, y = self._pos
        painter.drawEllipse(x - 7, y - 7, 14, 14)
        painter.drawLine(x - 14, y, x + 14, y)
        painter.drawLine(x, y - 14, x, y + 14)


class MouseClickNode(WorkflowNode):
    __identifier__ = 'workflow'
    NODE_NAME = '鼠标点击'
    NODE_ICON = 'fa5s.mouse-pointer'
    NODE_CATEGORY = '输入操作'
    MOUSE_NODE = True  # 自定义属性编辑器接管

    def __init__(self):
        super().__init__()
        self.add_input('coords', multi_input=False)
        self.add_input('window', multi_input=False)
        self.add_output('out')
        self.add_fail_output()   # 失败分支（未连接时异常终止）

        self._register_storage('button', _BUTTONS[0])
        self._register_storage('click_type', _CLICK_TYPES[0])
        self._register_storage('dbl_interval', '300')     # 双击间隔(ms)
        self._register_storage('coord_mode', _COORD_MODES[0])
        self._register_storage('pos_x', '0')
        self._register_storage('pos_y', '0')
        self._register_storage('offset_x', '0')
        self._register_storage('offset_y', '0')
        self._register_storage('exec_mode', _EXEC_MODES[0])
        self._register_storage('move_before', '0')
        self._register_storage('restore_mouse', '0')
        self._register_storage('show_marker', '0')
        self._register_storage('pre_wait', '0')
        self._register_storage('post_wait', '0')

    def _register_storage(self, name, value):
        """注册为可序列化的模型属性，但不进入属性页通用行（由 MouseClickEditor 接管）。"""
        self.create_property(name, value=value)

    # ---------------- 属性读取辅助 ----------------
    @staticmethod
    def _int_prop(value):
        try:
            return int(float(str(value).strip()))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _bool_prop(value):
        return str(value).strip() in ('1', 'true', 'True', '是')

    def _apply_button(self):
        return _BUTTON_CODE.get(self.get_property('button') or _BUTTONS[0], 'left')

    def _apply_clicks(self):
        clicks = 2 if (self.get_property('click_type') or '单击') == '双击' else 1
        return clicks, max(0.0, self._int_prop(self.get_property('dbl_interval')) / 1000.0)

    def _resolve_hwnd(self, inputs):
        """从 window 端口取 hwnd：int 直接用；对象取 NativeWindowHandle。"""
        w = inputs.get('window')
        if w is None:
            return None
        if isinstance(w, int):
            return w
        hw = getattr(w, 'NativeWindowHandle', None)
        return int(hw) if hw else None

    @staticmethod
    def _extract_xy(data):
        if isinstance(data, dict):
            return data.get('x'), data.get('y')
        if isinstance(data, (tuple, list)) and len(data) >= 2:
            return data[0], data[1]
        return None, None

    def _resolve_xy(self, inputs):
        """解析基础坐标 (x, y)，语义由 coord_mode 决定；附带偏移。"""
        data = inputs.get('coords')
        if data is not None:
            x, y = self._extract_xy(data)
            if x is not None and y is not None:
                return self._int_prop(x), self._int_prop(y)
        x = self._int_prop(self.get_property('pos_x'))
        y = self._int_prop(self.get_property('pos_y'))
        return x, y

    # ---------------- 执行 ----------------
    def execute(self, inputs):
        self._apply_wait(None, 'pre_wait')

        raw_x, raw_y = self._resolve_xy(inputs)
        offset_x = self._int_prop(self.get_property('offset_x'))
        offset_y = self._int_prop(self.get_property('offset_y'))
        x, y = raw_x + offset_x, raw_y + offset_y

        coord_mode = self.get_property('coord_mode') or _COORD_MODES[0]
        exec_mode = self.get_property('exec_mode') or _EXEC_MODES[0]
        hwnd = self._resolve_hwnd(inputs)
        is_relative = coord_mode == _COORD_MODES[1]

        if is_relative and hwnd is None:
            raise RuntimeError('「相对窗口客户区」坐标需要连接 window 输入提供窗口句柄')

        use_background = (exec_mode == '后台') or (exec_mode == '自动' and hwnd is not None)
        if exec_mode == '后台' and hwnd is None:
            raise RuntimeError('后台模式需要连接 window 输入提供窗口句柄')

        button = self._apply_button()
        clicks, interval = self._apply_clicks()

        # 统一换算到最终屏幕绝对坐标（用于输出/前台/红点定位）
        final_abs = (x, y)
        client_xy = None
        if hwnd is not None:
            if is_relative:
                result = mouse_ctrl.client_to_screen(hwnd, (x, y))
                final_abs = result if result else (x, y)
                client_xy = (x, y)
            else:
                result = mouse_ctrl.screen_to_client(hwnd, (x, y))
                client_xy = result if result else (x, y)

        if self._bool_prop(self.get_property('show_marker')):
            _show_marker(*final_abs)

        if use_background:
            if client_xy is None:
                raise RuntimeError('无法计算客户区坐标')
            mouse_ctrl.click_background(hwnd, client_xy[0], client_xy[1],
                                        button=button, clicks=clicks,
                                        interval=interval)
        else:
            # 前台
            restore = self._bool_prop(self.get_property('restore_mouse'))
            orig = mouse_ctrl.get_position() if restore else None
            move_before = self._bool_prop(self.get_property('move_before'))
            if move_before:
                mouse_ctrl.click(target=final_abs, button=button,
                                 clicks=clicks, interval=interval)
            else:
                # 不移动鼠标，在当前光标位置点击
                mouse_ctrl.click(button=button, clicks=clicks, interval=interval)
            if orig is not None:
                mouse_ctrl.move(orig)

        # 后置等待
        self._apply_wait(None, 'post_wait')
        return {'out': final_abs}, 'out'


def _show_marker(x, y, hold=0.35):
    """在屏幕 (x,y) 短暂显示红点标记；仅在 Qt GUI 线程可用时执行，否则静默跳过。"""
    import threading
    app = QApplication.instance()
    if app is None or threading.current_thread() is not app.thread():
        return
    try:
        marker = _ClickMarker(x, y)
        marker.show()
        QTimer.singleShot(int(hold * 1000), marker.close)
        step = 0.04
        for _ in range(int(hold / step)):
            app.processEvents()
            import time
            time.sleep(step)
    except Exception:
        pass