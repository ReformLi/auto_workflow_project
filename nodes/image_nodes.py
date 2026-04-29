# -*- coding: utf-8 -*-
"""
image_nodes.py
作者: reformLi
创建日期: 2026/4/28
最后修改: 2026/4/28
版本: 1.0.0

功能描述: 查找图片节点
"""

from automation.image_finder import ImageFinder
from nodes.base_node import WorkflowNode

finder = ImageFinder(confidence=0.9)

class FindImageNode(WorkflowNode):
    __identifier__ = 'workflow'
    NODE_NAME = "查找图片"
    NODE_CATEGORY = "图像操作"

    def __init__(self):
        super().__init__()
        self.add_input('窗口对象', multi_input=False)
        self.add_text_input('img_path', 'img_path', 'E:\\code\\python\\auto_workflow_project\\static\\imgs\\1.png')
        self.add_output('坐标')
        self.add_output('中心坐标')

    def execute(self, inputs):
        template = self.get_property('img_path')
        # target_window = inputs.get('窗口对象', None)
        # target_window = '计算器'
        # if target_window:
        #     center = finder.find_on_screen(template)
        # else:
        center = finder.find_on_screen(template)

        if center is None:
            raise RuntimeError(f"未找到匹配的图片: {template}")
        return {'坐标': center, '中心坐标': center},'坐标'