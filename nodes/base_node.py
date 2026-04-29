# -*- coding: utf-8 -*-
"""
base_node.py
作者: reformLi
创建日期: 2026/3/25
最后修改: 2026/3/25
版本: 1.0.0

功能描述: 基础节点类 -工作流节点基类
"""
from NodeGraphQt import BaseNode
from abc import ABC, abstractmethod

class WorkflowNode(BaseNode, ABC):
    """
    工作流节点基类，扩展执行功能
    """
    __identifier__ = 'workflow'  # 默认标识，子类可覆盖
    NODE_NAME = 'WorkflowNode'

    def __init__(self):
        super(WorkflowNode, self).__init__()
        # 初始化执行状态
        self._executed = False
        self._output_data = None
        self.set_disabled(False)

    def _run(self, context):
        """子类实现具体执行逻辑"""
        raise NotImplementedError

    def reset(self):
        """重置节点状态（用于多次执行）"""
        self._executed = False
        self._output_data = None

    @abstractmethod
    def execute(self, inputs: dict) -> (dict, str):
        """
        执行节点逻辑，返回输出数据和下一个要执行的端口名（默认为 None）
        返回格式: (outputs, next_port_name)
        """
        pass

    @classmethod
    def is_start_node(cls) -> bool:
        return False

    @classmethod
    def is_end_node(cls) -> bool:
        return False