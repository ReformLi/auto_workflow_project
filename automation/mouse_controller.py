# -*- coding: utf-8 -*-
"""
mouse_controller.py
作者: reformLi
创建日期: 2026/4/27
最后修改: 2026/4/27
版本: 1.0.0

功能描述: 鼠标控制器
"""
# automation/mouse_controller.py
import ctypes
import time
from ctypes import wintypes

user32 = ctypes.windll.user32

# 坐标结构
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]

# 鼠标事件常量（仅点击，不含 MOVE）
MOUSEEVENTF_LEFTDOWN   = 0x0002
MOUSEEVENTF_LEFTUP     = 0x0004
MOUSEEVENTF_RIGHTDOWN  = 0x0008
MOUSEEVENTF_RIGHTUP    = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP   = 0x0040
MOUSEEVENTF_WHEEL      = 0x0800

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("mi", MOUSEINPUT),
    ]

def _send_input(*inputs):
    n = len(inputs)
    arr = (INPUT * n)(*inputs)
    user32.SendInput(n, arr, ctypes.sizeof(INPUT))

class MouseController:
    """准确、无DPI困扰的鼠标控制器"""

    def __init__(self, default_delay: float = 0.05):
        self.default_delay = default_delay

    def _ensure_coords(self, target):
        # ... 与之前相同，将目标转为 (x, y) 屏幕物理坐标 ...
        if isinstance(target, (tuple, list)) and len(target) == 2:
            return target[0], target[1]
        if hasattr(target, 'rectangle') or hasattr(target, 'bounding_rectangle'):
            try:
                rect = target.bounding_rectangle()
                return rect.left + rect.width() // 2, rect.top + rect.height() // 2
            except Exception:
                pass
        if hasattr(target, 'center'):
            center = target.center()
            if callable(center):
                center = center()
            if isinstance(center, (tuple, list)):
                return center
            return center.x, center.y
        if hasattr(target, 'x') and hasattr(target, 'y'):
            return target.x, target.y
        raise ValueError(f"无法从对象 {target} 提取坐标")

    def _move_cursor_to(self, x, y):
        """直接设置光标到绝对屏幕像素，无任何映射"""
        user32.SetCursorPos(int(x), int(y))
        time.sleep(0.01)  # 让系统处理移动

    def move(self, target, duration=0.0):
        x, y = self._ensure_coords(target)
        self._move_cursor_to(x, y)
        time.sleep(self.default_delay)

    def click(self, target=None, button='left', clicks=1, interval=0.1):
        if target:
            x, y = self._ensure_coords(target)
            self._move_cursor_to(x, y)

        if button == 'left':
            down, up = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
        elif button == 'right':
            down, up = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
        elif button == 'middle':
            down, up = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
        else:
            raise ValueError(f"不支持的按钮: {button}")

        for i in range(clicks):
            _send_input(INPUT(type=0, mi=MOUSEINPUT(dwFlags=down)))
            time.sleep(0.02)
            _send_input(INPUT(type=0, mi=MOUSEINPUT(dwFlags=up)))
            if i < clicks - 1:
                time.sleep(interval)
        time.sleep(self.default_delay)

    def double_click(self, target=None, button='left', interval=0.1):
        self.click(target, button, clicks=2, interval=interval)

    def right_click(self, target=None):
        self.click(target, button='right')

    def drag(self, start, end, duration=0.5, button='left'):
        x1, y1 = self._ensure_coords(start)
        x2, y2 = self._ensure_coords(end)

        self._move_cursor_to(x1, y1)
        if button == 'left':
            down, up = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
        else:
            down, up = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
        _send_input(INPUT(type=0, mi=MOUSEINPUT(dwFlags=down)))
        time.sleep(0.02)

        steps = 20
        for i in range(1, steps + 1):
            cx = int(x1 + (x2 - x1) * i / steps)
            cy = int(y1 + (y2 - y1) * i / steps)
            self._move_cursor_to(cx, cy)
            time.sleep(duration / steps)

        _send_input(INPUT(type=0, mi=MOUSEINPUT(dwFlags=up)))
        time.sleep(self.default_delay)

    def scroll(self, clicks: int, target=None):
        if target:
            x, y = self._ensure_coords(target)
            self._move_cursor_to(x, y)
        # 滚轮数据 WHEEL_DELTA = 120，正数向上
        mi = MOUSEINPUT(mouseData=120 * clicks, dwFlags=MOUSEEVENTF_WHEEL)
        _send_input(INPUT(type=0, mi=mi))
        time.sleep(self.default_delay)

    def get_position(self):
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)