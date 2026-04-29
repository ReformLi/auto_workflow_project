# -*- coding: utf-8 -*-
"""
end_node.py
作者: reformLi
创建日期: 2026/3/25
最后修改: 2026/3/25
版本: 1.0.0

功能描述: 结束节点
"""
from nodes.base_node import WorkflowNode

class EndNode(WorkflowNode):
    """结束节点"""
    __identifier__ = 'workflow'
    NODE_NAME = '结束'

    def __init__(self):
        super(EndNode, self).__init__()
        self.add_input('in')

    def execute(self, inputs):
        print("工作流执行结束")
        return {}, None   # None 表示没有下一个节点

    @classmethod
    def is_end_node(cls):
        return True