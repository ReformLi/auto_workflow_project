# -*- coding: utf-8 -*-
"""
start_node.py
作者: reformLi
创建日期: 2026/3/25
最后修改: 2026/3/25
版本: 1.0.0

功能描述: 开始节点
"""
from nodes.base_node import WorkflowNode

class StartNode(WorkflowNode):
    """开始节点"""
    __identifier__ = 'workflow'
    NODE_NAME = '开始'

    def __init__(self):
        super().__init__()
        # self.add_input('in')
        self.add_output('out')

    @classmethod
    def is_start_node(cls):
        return True

    def execute(self, inputs):
        return {'out': True}, 'out'