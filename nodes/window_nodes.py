# -*- coding: utf-8 -*-
"""
window_nodes.py
作者: reformLi
创建日期: 2026/4/27
最后修改: 2026/9/4
版本: 2.0.0

功能描述: 窗口操作节点——查找窗口 / 激活窗口
"""
from automation.window_manager import WindowManager
from nodes.base_node import WorkflowNode

wm = WindowManager()

# 标题匹配方式：下拉框选项 → WindowManager 参数
_MATCH_MODE_ITEMS = ['包含', '完全匹配', '正则表达式']
_MATCH_MODE_MAP = {'包含': 'contains', '完全匹配': 'exact', '正则表达式': 'regex'}


class _WindowSearchMixin:
    """窗口查找公共逻辑：属性定义 + 条件读取 + 按属性查找（非 WorkflowNode，不被自动注册）"""

    def _add_search_properties(self, title_label='窗口标题'):
        self.add_text_input('title', title_label, '',
                            placeholder_text='窗口标题')
        self.mark_property_capture('title')
        self.add_combo_menu('match_mode', '标题匹配', _MATCH_MODE_ITEMS)
        self.add_text_input('class_name', '类名(可选)', '',
                            placeholder_text='如 Notepad，留空忽略')
        self.add_text_input('process_name', '进程名(可选)', '',
                            placeholder_text='如 notepad.exe，留空忽略')

    def _add_title_property(self, title_label='窗口标题'):
        """仅添加标题搜索属性（匹配方式固定为'包含'，无类名/进程名筛选）。"""
        self.add_text_input('title', title_label, '',
                            placeholder_text='窗口标题')
        self.mark_property_capture('title')

    def _search_window_by_title(self):
        """仅按标题（固定'包含'匹配）查找窗口。"""
        title = (self.get_property('title') or '').strip()
        if not title:
            raise RuntimeError("请填写窗口标题（匹配方式固定为'包含'）")
        window = wm.find_window(title=title, match_mode='contains')
        if not window:
            raise RuntimeError(f"未找到窗口（标题包含\"{title}\"）")
        return window

    def _read_search_conditions(self):
        """读取并归一化查找条件 → (title, match_mode, class_name, process_name)"""
        title = (self.get_property('title') or '').strip()
        class_name = (self.get_property('class_name') or '').strip()
        process_name = (self.get_property('process_name') or '').strip()
        match_mode = _MATCH_MODE_MAP.get(self.get_property('match_mode'), 'contains')
        return title, match_mode, class_name, process_name

    @staticmethod
    def _describe_conditions(title, match_mode, class_name, process_name):
        """生成供错误信息使用的条件描述"""
        mode_text = {'exact': '完全匹配', 'contains': '包含', 'regex': '正则'}[match_mode]
        parts = []
        if title:
            parts.append(f"标题{mode_text}\"{title}\"")
        if class_name:
            parts.append(f"类名={class_name}")
        if process_name:
            parts.append(f"进程={process_name}")
        return '，'.join(parts) or '无条件'

    def _search_window(self):
        """按节点属性查找窗口，条件为空或未找到时抛出 RuntimeError"""
        title, match_mode, class_name, process_name = self._read_search_conditions()
        if not any([title, class_name, process_name]):
            raise RuntimeError("请至少填写窗口标题 / 类名 / 进程名之一")
        window = wm.find_window(title=title or None, match_mode=match_mode,
                                class_name=class_name or None,
                                process_name=process_name or None)
        if not window:
            raise RuntimeError(
                f"未找到窗口（{self._describe_conditions(title, match_mode, class_name, process_name)}）")
        return window

    def _flow_port(self, candidates=('窗口对象', '窗口句柄')):
        """返回用于流转的输出端口名：优先取有连接的候选端口"""
        for name in candidates:
            try:
                port = self.get_output(name)
                if port and port.connected_ports():
                    return name
            except Exception:
                continue
        return candidates[0]


class FindWindowNode(_WindowSearchMixin, WorkflowNode):
    """查找窗口节点：按标题/类名/进程名查找，输出窗口对象与窗口句柄"""
    __identifier__ = 'workflow'
    NODE_NAME = '查找窗口'
    NODE_ICON = 'fa5s.window-restore'
    NODE_CATEGORY = "窗口操作"

    def __init__(self):
        super().__init__()
        self.add_input('in')
        self.add_output('窗口对象')
        self.add_output('窗口句柄')
        self.add_fail_output()   # 失败分支：未找到窗口等异常时可接补救流程
        self._add_search_properties()

    def execute(self, inputs):
        window = self._search_window()
        hwnd = int(window.NativeWindowHandle)
        return {'窗口对象': window, '窗口句柄': hwnd}, self._flow_port()


class ActivateWindowNode(_WindowSearchMixin, WorkflowNode):
    """激活窗口节点：优先使用上游传入的窗口对象，未连接时按属性查找后激活"""
    __identifier__ = 'workflow'
    NODE_NAME = "激活窗口"
    NODE_ICON = 'fa5s.layer-group'
    NODE_CATEGORY = "窗口操作"

    def __init__(self):
        super().__init__()
        self.add_input('窗口对象')
        self.add_output('out')
        self.add_fail_output()   # 失败分支：激活失败时可接补救流程
        self._add_title_property(title_label='窗口标题(未连上游时)')

    def execute(self, inputs):
        # 优先使用上游传入的窗口对象（连接 查找窗口.窗口对象 → 激活窗口.窗口对象）
        window = inputs.get('窗口对象')
        if window is None or not hasattr(window, 'SetFocus'):
            window = self._search_window_by_title()
        if not wm.activate_window(window):
            raise RuntimeError(f"窗口激活失败: {window.Name}")
        return {}, 'out'
