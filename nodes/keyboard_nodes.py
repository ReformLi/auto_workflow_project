# -*- coding: utf-8 -*-
"""
keyboard_nodes.py
作者: reformLi
创建日期: 2026/4/28
最后修改: 2026/9/5
版本: 2.0.0

功能描述: 键盘操作节点——键盘快捷键 / 文本输入。
- 键盘快捷键(HotkeyNode)：解析组合键字符串，支持前台 SendInput / 后台 PostMessage。
- 文本输入(TypeTextNode)：前台逐字输入 / 中文剪贴板，后台选中粘贴。
共同：可选 window 输入端口（后台目标窗口）、自动/前台/后台执行模式、
      前置/后置等待，属性页使用通用声明式渲染。
"""
import time

from automation.keyboard_controller import KeyboardController
from nodes.base_node import WorkflowNode

kb_ctrl = KeyboardController()

_EXEC_MODES = ['自动', '前台', '后台']
_CUSTOM_MARK = '(使用上方自定义快捷键)'

# 常用按键下拉：显示名 → 键 token（供解析）
_QUICK_KEY_ITEMS = [
    _CUSTOM_MARK,
    '回车 Enter', '制表 Tab', '退出 Esc', '空格 Space',
    '退格 Backspace', '删除 Delete', 'Home', 'End',
    '上方向键', '下方向键', '左方向键', '右方向键',
    'F1', 'F2', 'F3', 'F4', 'F5', 'F6',
    'F7', 'F8', 'F9', 'F10', 'F11', 'F12',
]
_QUICK_KEY_MAP = {
    '回车 Enter': 'enter', '制表 Tab': 'tab', '退出 Esc': 'esc',
    '空格 Space': 'space', '退格 Backspace': 'backspace',
    '删除 Delete': 'delete', 'Home': 'home', 'End': 'end',
    '上方向键': 'up', '下方向键': 'down', '左方向键': 'left', '右方向键': 'right',
    'F1': 'f1', 'F2': 'f2', 'F3': 'f3', 'F4': 'f4', 'F5': 'f5', 'F6': 'f6',
    'F7': 'f7', 'F8': 'f8', 'F9': 'f9', 'F10': 'f10', 'F11': 'f11', 'F12': 'f12',
}


def resolve_hwnd(inputs):
    """从 window 输入端口取窗口句柄：int 直接用，对象取 NativeWindowHandle。"""
    w = inputs.get('window')
    if w is None:
        return None
    if isinstance(w, int):
        return w
    hw = getattr(w, 'NativeWindowHandle', None)
    return int(hw) if hw else None


def _int_prop(value):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 0


def _bool_prop(value):
    return str(value).strip() in ('1', 'true', 'True', '是')


class HotkeyNode(WorkflowNode):
    """键盘快捷键节点：模拟组合键 / 功能键。"""
    __identifier__ = 'workflow'
    NODE_NAME = '键盘快捷键'
    NODE_CATEGORY = '输入操作'
    NODE_ICON = 'fa5s.keyboard'

    def __init__(self):
        super().__init__()
        self.add_input('window', multi_input=False)   # 可选：后台目标窗口句柄
        self.add_output('out')

        self.add_text_input('keys', '快捷键组合', 'ctrl+c',
                            placeholder_text='如 ctrl+shift+a / enter / f5，用 + 连接')
        self.add_combo_menu('quick_key', '常用按键', _QUICK_KEY_ITEMS)
        self.add_combo_menu('exec_mode', '执行模式', _EXEC_MODES)
        self.add_text_input('repeat', '发送次数', '1', placeholder_text='连续发送次数，默认 1')
        self.add_text_input('interval', '按键间隔(ms)', '50',
                            placeholder_text='多次发送之间的间隔(毫秒)')
        self._add_wait_properties()

    # ---------------- 快捷键解析 ----------------
    @staticmethod
    def parse_shortcut(raw):
        """把快捷键字符串解析为有序键列表（含修饰键，如 'ctrl+shift+a' → [ctrl,shift,a]）。"""
        raw = (raw or '').strip().lower()
        if not raw:
            raise RuntimeError('请填写快捷键组合，或用常用按键下拉选择')
        for sep in ('+', ' '):
            if sep in raw:
                parts = [p.strip() for p in raw.split(sep) if p.strip()]
                break
        else:
            parts = [raw]
        tokens = []
        for key in parts:
            kb_ctrl._get_vk(key)  # 校验存在，非法则抛 ValueError
            tokens.append(key)
        if not tokens:
            raise RuntimeError('快捷键为空')
        return tokens

    def _resolve_keys(self):
        """常用按键下拉 与 自定义组合 二选一：下拉优先。"""
        qp = (self.get_property('quick_key') or _CUSTOM_MARK)
        if qp != _CUSTOM_MARK:
            return [_QUICK_KEY_MAP.get(qp, qp)]
        return self.parse_shortcut(self.get_property('keys'))

    # ---------------- 执行 ----------------
    def execute(self, inputs):
        self._apply_wait(None, 'pre_wait')

        keys = self._resolve_keys()
        exec_mode = self.get_property('exec_mode') or _EXEC_MODES[0]
        hwnd = resolve_hwnd(inputs)
        use_background = (exec_mode == '后台') or (exec_mode == '自动' and hwnd is not None)
        if exec_mode == '后台' and hwnd is None:
            raise RuntimeError('后台模式需要连接 window 输入提供窗口句柄')

        repeat = max(1, _int_prop(self.get_property('repeat')))
        interval = max(0.0, _int_prop(self.get_property('interval')) / 1000.0)

        for i in range(repeat):
            if use_background:
                kb_ctrl.hotkey_to_hwnd(hwnd, *keys)
            else:
                kb_ctrl.hotkey(*keys)
            if i < repeat - 1 and interval > 0:
                time.sleep(interval)

        self._apply_wait(None, 'post_wait')
        return {}, 'out'


class TypeTextNode(WorkflowNode):
    """文本输入节点：向前台焦点窗口 / 后台目标窗口输入字符串。"""
    __identifier__ = 'workflow'
    NODE_NAME = '文本输入'
    NODE_CATEGORY = '输入操作'
    NODE_ICON = 'fa5s.font'

    def __init__(self):
        super().__init__()
        self.add_input('text', multi_input=False)      # 可选：上游字符串，覆盖手动内容
        self.add_input('window', multi_input=False)    # 可选：后台目标窗口句柄
        self.add_output('out')

        self.add_multiline_input('content', '文本内容', '',
                                 tooltip='要输入的文本；若连接了 text 输入则忽略此处')
        self.add_combo_menu('exec_mode', '执行模式', _EXEC_MODES)
        self.add_text_input('interval', '键间间隔(ms)', '20',
                            placeholder_text='前台逐键输入的间隔(毫秒)')
        self.add_bool_option('restore_clipboard', '粘贴后恢复原剪贴板', default=True)
        self.add_bool_option('send_enter', '输入完成后回车', default=False)
        self._add_wait_properties()

    def _resolve_text(self, inputs):
        text = inputs.get('text')
        if text is not None:
            return str(text)
        return str(self.get_property('content') or '')

    def execute(self, inputs):
        self._apply_wait(None, 'pre_wait')

        text = self._resolve_text(inputs)
        exec_mode = self.get_property('exec_mode') or _EXEC_MODES[0]
        hwnd = resolve_hwnd(inputs)
        use_background = (exec_mode == '后台') or (exec_mode == '自动' and hwnd is not None)
        if exec_mode == '后台' and hwnd is None:
            raise RuntimeError('后台模式需要连接 window 输入提供窗口句柄')

        interval = max(0.0, _int_prop(self.get_property('interval')) / 1000.0)
        restore = _bool_prop(self.get_property('restore_clipboard'))

        if use_background:
            kb_ctrl.paste_to_window(hwnd, text, restore)
        elif text:
            kb_ctrl.type_text(text, interval)

        if _bool_prop(self.get_property('send_enter')):
            if use_background:
                kb_ctrl.hotkey_to_hwnd(hwnd, 'enter')
            else:
                kb_ctrl.tap('enter')

        self._apply_wait(None, 'post_wait')
        return {'out': text}, 'out'