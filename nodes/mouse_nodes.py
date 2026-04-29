# -*- coding: utf-8 -*-
"""
mouse_nodes.py
作者: reformLi
创建日期: 2026/4/27
最后修改: 2026/4/27
版本: 1.0.0

功能描述: 鼠标点击节点
"""
from automation.mouse_controller import MouseController
from nodes.base_node import WorkflowNode

# 在节点类外部创建控制器（可共享，也可每次创建）
mouse_ctrl = MouseController(default_delay=0.05)

class ClickNode(WorkflowNode):
    """开始节点"""
    __identifier__ = 'workflow'
    NODE_NAME = '点击'

    # PROPERTY_DEFS = [
    #     {
    #         'name': 'button',
    #         'type': 'combo',  # 下拉框
    #         'default': 'left',
    #         'description': '鼠标按键',
    #         'choices': ['left', 'right', 'middle']
    #     },
    #     {
    #         'name': 'clicks',
    #         'type': 'int',
    #         'default': 1,
    #         'description': '点击次数（1~5）',
    #         'min': 1,
    #         'max': 5
    #     },
    #     {
    #         'name': 'delay',
    #         'type': 'float',
    #         'default': 0.1,
    #         'description': '点击后延迟（秒）'
    #     }
    # ]

    def __init__(self):
        super().__init__()
        self.add_input('in', multi_input=False) # multi_input=True：允许端口有多个连接。
        self.add_output('out')
        self.add_text_input('pos_x', 'x', '100')
        self.add_text_input('pos_y', 'y', '200')

        # for prop in self.PROPERTY_DEFS:
        #     self.create_property(prop['name'], prop['default'])

    def execute(self, inputs):
        # 获取输入的目标坐标
        pos_x = self.get_property('pos_x')
        pos_y = self.get_property('pos_y')
        target = (pos_x,pos_y)
        # 如果没有输入，则使用节点自身存储的属性（可从属性面板设置）
        if target is None:
            target = (0,0) # 默认值如 (100, 200)
        mouse_ctrl.click(target=target)
        return {'out': target}, 'out'