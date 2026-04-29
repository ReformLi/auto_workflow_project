# -*- coding: utf-8 -*-
"""
window_nodes.py
作者: reformLi
创建日期: 2026/4/27
最后修改: 2026/4/27
版本: 1.0.0

功能描述: 窗口节点
"""
from automation.window_manager import WindowManager
from nodes.base_node import WorkflowNode
from core.context import get_context

wm = WindowManager()
class FindWindowNode(WorkflowNode):
    """开始节点"""
    __identifier__ = 'workflow'
    NODE_NAME = '查找窗口'
    NODE_CATEGORY = "窗口操作"

    def __init__(self):
        super().__init__()
        self.add_input('in')
        self.add_output('out')
        self.add_text_input('title', 'title', '计算器')

    def execute(self, inputs):
        title = self.get_property('title')
        # class_name = self.get_property('class_name')
        window = wm.find_window(title=title)
        if window:
            return {'窗口对象': window},'out'
        else:
            raise RuntimeError(f"未找到窗口: {title}")

class ActivateWindowNode(WorkflowNode):
    __identifier__ = 'workflow'
    NODE_NAME = "激活窗口"
    NODE_CATEGORY = "窗口操作"

    def __init__(self):
        super().__init__()
        self.add_input('in')
        self.add_text_input('window_title','窗口名', '无标题 - Notepad')
        self.add_output('out')

    def execute(self, inputs):
        title = self.get_property('window_title')
        wm = WindowManager()
        window = wm.find_window(title=title)
        if not window:
            return {f"error-未找到窗口": title}, None
            # raise RuntimeError(f"未找到窗口: {title}")
        # 激活窗口
        wm.activate_window(window)
        hwnd = window.NativeWindowHandle  # 获取原生句柄
        # 存入全局上下文
        ctx = get_context()
        ctx.set("title_hwnd", hwnd)
        return {'窗口句柄': hwnd},'out'

# class GetContextWindowNode(WorkflowNode):
#     NODE_NAME = "获取上下文变量"
#     NODE_CATEGORY = "工具"
#
#     def __init__(self):
#         super().__init__()
#         self.add_input('in')
#         # self.create_property('context_key', 'active_window')
#         self.add_output('值')
#         self.add_text_input('title1', '计算器')
#
#     def execute(self, inputs):
#         key = 'active_window'
#         ctx = get_context()
#         self.set_property('title1',ctx.get(key))
#         return {'值': ctx.get(key)},'值'