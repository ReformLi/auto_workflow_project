# -*- coding: utf-8 -*-
"""
keyboard_controller.py
作者: reformLi
创建日期: 2026/4/28
最后修改: 2026/4/28
版本: 1.0.0

功能描述: 键盘控制
"""
# automation/keyboard_controller.py
import ctypes
import time
import pyperclip
import uiautomation as auto

user32 = ctypes.windll.user32

# ---------- 虚拟键码表 ----------
VK_CODE = {
    'backspace': 0x08, 'tab': 0x09, 'enter': 0x0D, 'shift': 0x10,
    'ctrl': 0x11, 'alt': 0x12, 'pause': 0x13, 'caps_lock': 0x14,
    'esc': 0x1B, 'space': 0x20, 'page_up': 0x21, 'page_down': 0x22,
    'end': 0x23, 'home': 0x24, 'left': 0x25, 'up': 0x26,
    'right': 0x27, 'down': 0x28, 'print_screen': 0x2C, 'insert': 0x2D,
    'delete': 0x2E, '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33,
    '4': 0x34, '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46,
    'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C,
    'm': 0x4D, 'n': 0x4E, 'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52,
    's': 0x53, 't': 0x54, 'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58,
    'y': 0x59, 'z': 0x5A, 'f1': 0x70, 'f2': 0x71, 'f3': 0x72,
    'f4': 0x73, 'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
    'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
    'num_lock': 0x90, 'scroll_lock': 0x91, ';': 0xBA, '=': 0xBB,
    ',': 0xBC, '-': 0xBD, '.': 0xBE, '/': 0xBF, '`': 0xC0,
    '[': 0xDB, '\\': 0xDC, ']': 0xDD, "'": 0xDE
}

class KeyboardController:
    """基于 keybd_event 的键盘模拟器，支持全局按键和文本输入"""

    def __init__(self, default_delay: float = 0.05):
        self.default_delay = default_delay

    # ========== 内部辅助 ==========
    def _get_vk(self, key: str) -> int:
        key_lower = key.lower()
        if key_lower in VK_CODE:
            return VK_CODE[key_lower]
        if len(key) == 1:
            upper = key.upper()
            if upper in VK_CODE:
                return VK_CODE[upper]
        raise ValueError(f"未识别的按键: {key}")

    def _key_event(self, vk: int, flags: int = 0):
        """flags: 0=按下, 2=释放"""
        user32.keybd_event(vk, 0, flags, 0)
        time.sleep(0.01)

    # ========== 单键操作 ==========
    def press(self, key: str):
        self._key_event(self._get_vk(key), 0)

    def release(self, key: str):
        self._key_event(self._get_vk(key), 2)

    def tap(self, key: str, duration: float = 0.05):
        self.press(key)
        time.sleep(duration)
        self.release(key)
        time.sleep(self.default_delay)

    # ========== 组合键 ==========
    def hotkey(self, *keys, duration: float = 0.05):
        for k in keys:
            self.press(k)
            time.sleep(0.02)
        for k in reversed(keys):
            self.release(k)
            time.sleep(0.02)
        time.sleep(self.default_delay)

    # ========== 文本输入（全局） ==========
    def type_text(self, text: str, interval: float = 0.02):
        """
        自动选择最佳全局输入方式：
        - 仅 ASCII 文本 → 模拟键盘逐字输入
        - 含中文 → 剪贴板粘贴
        """
        if self._is_ascii(text):
            self._type_ascii(text, interval)
        else:
            self._type_via_clipboard(text)

    def _is_ascii(self, text: str) -> bool:
        try:
            text.encode('ascii')
            return True
        except UnicodeEncodeError:
            return False

    def _type_ascii(self, text: str, interval: float):
        """逐字符模拟 ASCII 输入，处理大小写"""
        for ch in text:
            if ch.isupper():
                self.press('shift')
                self.tap(ch.lower())
                self.release('shift')
            elif ch.islower():
                self.tap(ch)
            else:
                # 数字/符号：直接 tap（VK_CODE 支持）
                self.tap(ch)
            time.sleep(interval)
        time.sleep(self.default_delay)

    def _type_via_clipboard(self, text: str):
        """通过剪贴板粘贴文本（支持中文）"""
        # 保存原剪贴板内容（可选）
        try:
            old_content = pyperclip.paste()
        except:
            old_content = None

        pyperclip.copy(text)
        time.sleep(0.05)
        self.hotkey('ctrl', 'v')
        # 恢复原剪贴板（如果不希望污染剪贴板）
        if old_content is not None:
            pyperclip.copy(old_content)

    # ========== 后台输入方法（新增） ==========
    def tap_to_window(self, target, key: str, duration: float = 0.05):
        """自动定位编辑控件后，发送单个按键"""
        hwnd = self._get_edit_hwnd(target)  # 统一取编辑控件句柄
        vk = self._get_vk(key)
        self._send_key_to_window(hwnd, vk, True)
        time.sleep(duration)
        self._send_key_to_window(hwnd, vk, False)
        time.sleep(self.default_delay)

    def hotkey_to_window(self, target, *keys, duration: float = 0.05):
        """自动定位编辑控件后，发送组合键"""
        print(f'发送按键到句柄: {self._get_edit_hwnd(target)}')
        hwnd = self._get_edit_hwnd(target)
        for k in keys:
            vk = self._get_vk(k)
            self._send_key_to_window(hwnd, vk, True)
            time.sleep(0.02)
        for k in reversed(keys):
            vk = self._get_vk(k)
            self._send_key_to_window(hwnd, vk, False)
            time.sleep(0.02)
        time.sleep(self.default_delay)

    def type_text_to_window(self, target, text: str, interval: float = 0.01):
        """后台文本输入，自动定位可编辑控件"""
        hwnd = self._get_edit_hwnd(target)
        for ch in text:
            user32.PostMessageW(hwnd, 0x0102, ord(ch), 0)
            time.sleep(interval)
        time.sleep(self.default_delay)

    def _send_key_to_window(self, hwnd: int, vk: int, press: bool):
        """发送 WM_KEYDOWN / WM_KEYUP 消息"""
        msg = 0x0100 if press else 0x0101  # WM_KEYDOWN, WM_KEYUP
        # lParam 可以简单传 0，但为了更准确，可构造标准 lParam
        # 这里直接传 0，绝大多数情况已足够
        user32.PostMessageW(hwnd, msg, vk, 0)

    def _get_edit_hwnd(self, target):
        """
        自动查找第一个可编辑控件的句柄。
        target: 窗口句柄(int) 或 uiautomation 控件对象。
        """
        if isinstance(target, int):
            target = auto.ControlFromHandle(target)

        # 已知的可编辑控件类型（备选，如果模式检测不到可以回退）
        EDIT_TYPES = {
            'EditControl', 'DocumentControl', 'MozillaWindowClass',
            'RichEdit', 'TextField', 'TextArea', 'Terminal'
        }

        def find_editable(ctrl):
            # 1. 先检查是否是可聚焦控件（排除单纯文本标签等）
            if not ctrl.IsKeyboardFocusable:
                pass  # 不返回，继续在子控件中找
            else:
                # 2. 检查是否拥有 ValuePattern 或 TextPattern
                value_pattern = ctrl.GetPattern(auto.PatternId.ValuePattern)
                text_pattern = ctrl.GetPattern(auto.PatternId.TextPattern)
                if value_pattern or text_pattern:
                    return ctrl

                # 3. 如果模式获取失败，回退检查 ControlTypeName
                if ctrl.ControlTypeName in EDIT_TYPES:
                    return ctrl

            # 递归查找子控件
            for child in ctrl.GetChildren():
                res = find_editable(child)
                if res:
                    return res
            return None

        editable = find_editable(target)
        if editable:
            return editable.NativeWindowHandle
        # 找不到时回退到顶层句柄
        return target.NativeWindowHandle

