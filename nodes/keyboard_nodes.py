# -*- coding: utf-8 -*-
"""
keyboard_nodes.py
作者: reformLi
创建日期: 2026/4/28
最后修改: 2026/4/28
版本: 1.0.0

功能描述: 
"""
from automation.keyboard_controller import KeyboardController
from nodes.base_node import WorkflowNode
kb_ctrl = KeyboardController()

class HotkeyNode(WorkflowNode):
    """开始节点"""
    __identifier__ = 'workflow'
    NODE_NAME = '键盘输入'

    def __init__(self):
        super().__init__()
        self.add_input('in')
        self.add_output('out')
        self.create_property('keys', 'ctrl+c')  # 用户可配置

    def execute(self, inputs):
        keys = str(self.get_property('keys')).split('+')
        kb_ctrl.hotkey(*[k.strip() for k in keys])
        return {},'out'