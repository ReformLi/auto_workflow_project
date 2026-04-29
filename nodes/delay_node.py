# -*- coding: utf-8 -*-
"""
delay_node.py
作者: reformLi
创建日期: 2026/3/25
最后修改: 2026/3/25
版本: 1.0.0

功能描述: 延时节点
"""
import time

from nodes.base_node import WorkflowNode

class DelayNode(WorkflowNode):
    """延时节点"""
    __identifier__ = 'workflow'
    NODE_NAME = '等待'

    def __init__(self):
        super(DelayNode, self).__init__()
        self.add_input('in')
        self.add_output('out')
        self.set_name('延时')
        # 添加文本输入属性，并显式设置默认值
        self.add_text_input('duration_sec', '持续时间(秒)', '1')
        self.set_property('duration_sec', '1')  # 关键：初始化属性值

    def execute(self, inputs):
        # 获取属性值，确保不为 None
        duration_str = self.get_property('duration_sec')
        if duration_str is None:
            duration_str = '1'
        try:
            duration = float(duration_str)
        except ValueError:
            duration = 1.0
        time.sleep(duration)
        return {'out': True},'out'