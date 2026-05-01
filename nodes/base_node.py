# -*- coding: utf-8 -*-
"""
base_node.py
作者: reformLi
创建日期: 2026/3/25
最后修改: 2026/3/25
版本: 1.0.0

功能描述: 基础节点类 -工作流节点基类
"""
import weakref
from abc import ABC, abstractmethod

from NodeGraphQt import BaseNode
from PyQt5 import QtWidgets, QtGui


class WorkflowNode(BaseNode, ABC):
    """
    工作流节点基类，扩展执行功能 + 线程安全的状态显示
    """
    __identifier__ = 'workflow'  # 默认标识，子类可覆盖
    NODE_NAME = 'WorkflowNode'

    # 全局弱引用字典：{node_id: node_instance}
    _instances = weakref.WeakValueDictionary()

    def __init__(self):
        super(WorkflowNode, self).__init__()
        # 原有初始化
        self._executed = False
        self._output_data = None
        self.set_disabled(False)

        # ========== 新增：状态显示相关 ==========
        # 生成唯一标识（使用Python对象id，也可用uuid）
        self._node_id = str(id(self))
        WorkflowNode._instances[self._node_id] = self

        # 创建用于显示状态的小型文本组件（作为节点的子项，自动跟随移动）
        font = QtGui.QFont()
        font.setPointSize(6)
        self.status_text = QtWidgets.QGraphicsTextItem(self.view) # type: ignore  #在代码行添加type: ignore注释，仅屏蔽当前行的警告：
        self.status_text.setFont(font)
        self.status_text.document().setDefaultStyleSheet(
            "div { margin:0; padding:0; } br { line-height: 0.6; }"
        )
        self.status_text.setDefaultTextColor(QtGui.QColor(255, 255, 255))
        self.status_text.setVisible(False)

    def get_node_id(self) -> str:
        """返回节点的唯一标识（供工作流线程使用）"""
        return self._node_id

    def update_status(self, html: str, is_error: bool = False):
        """
        在主线程中安全更新节点状态UI。
        该方法应由 WorkflowExecutor 在主线程中调用。
        """
        if not self.view:  # 节点可能已被销毁
            return
        self.status_text.setHtml(html)
        self.status_text.setVisible(bool(html))
        color = QtGui.QColor(255, 80, 80) if is_error else QtGui.QColor(80, 200, 80)
        self.status_text.setDefaultTextColor(color)

        # 重新计算位置（节点内部右上角，留4像素边距）
        node_rect = self.view.boundingRect()
        text_rect = self.status_text.boundingRect()
        x = node_rect.width() - text_rect.width() - 2
        y = -32
        self.status_text.setPos(x, y)
        self.update()

    @classmethod
    def get_node_by_id(cls, node_id: str):
        """通过节点ID安全获取节点实例（若节点已销毁则返回None）"""
        return cls._instances.get(node_id, None)

    # ========== 原有抽象方法 ==========
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