# -*- coding: utf-8 -*-
"""
manager.py
功能描述: 节点图管理器宿主——封装 NodeGraphQt.NodeGraph 实例的生命周期与节点注册，
         组装序列化/编辑/剪贴板三个 mixin
"""
import logging

from NodeGraphQt import NodeGraph
from PyQt5.QtWidgets import QTextEdit

from core.graph.signals import GraphSignalManager
from core.graph.serialization import GraphSerializerMixin
from core.graph.editing import GraphEditingMixin
from core.graph.clipboard import GraphClipboardMixin


class NodeGraphManager(GraphSerializerMixin, GraphEditingMixin, GraphClipboardMixin):
    """封装 NodeGraphQt 实例，管理节点图的生命周期"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        self.node_graph = None
        self.graph_widget = None
        self.view = None
        self._signals = None

        self.setup_node_graph()

    def setup_node_graph(self):
        try:
            self.node_graph = NodeGraph()
            # 允许节点循环
            self.node_graph.set_acyclic(mode=False)
            self.graph_widget = self.node_graph.widget
            self.graph_widget.resize(1000, 600)

            self.view = self.node_graph.viewer()

            # 结构信号的集中管理
            self._signals = GraphSignalManager(self.node_graph)
            self._signals.connect_all()

            self.logger.info('节点图管理器初始化成功')

        except Exception as e:
            self.logger.error(f'节点图管理器初始化失败: {str(e)}')
            self.graph_widget = QTextEdit()
            self.graph_widget.setPlainText(f"节点图编辑器加载失败: {str(e)}\n\n请确保 NodeGraphQt 已正确安装。")

    def get_view(self):
        return self.view

    def register_node_classes(self, classes):
        """注册节点类型（从节点注册表获取）"""
        try:
            for cls in classes:
                # NodeGraphQt.NodeGraph.register_node 要求类有 NODE_NAME 属性
                self.node_graph.register_node(cls)
            self.logger.info('节点类型注册成功')
        except Exception as e:
            self.logger.error(f'节点类型注册失败: {str(e)}')
            import traceback
            self.logger.error(traceback.format_exc())

    def get_all_nodes(self):
        """返回图中所有节点对象"""
        return self.node_graph.all_nodes()

    def clear(self):
        """清空节点图（期间抑制结构信号回调）"""
        if not self.node_graph:
            return

        try:
            with self._signals.suppressed():
                # 使用官方方法清空
                if hasattr(self.node_graph, 'clear_session'):
                    self.node_graph.clear_session()
                elif hasattr(self.node_graph, 'clear'):
                    self.node_graph.clear()
                else:
                    # 手动删除所有节点
                    nodes = []
                    if hasattr(self.node_graph, 'all_nodes'):
                        nodes = self.node_graph.all_nodes()
                    elif hasattr(self.node_graph, '_nodes'):
                        nodes = list(self.node_graph._nodes.values())
                    for node in nodes:
                        self.node_graph.delete_node(node)
        except Exception as e:
            self.logger.error(f"清空失败: {e}")

        self.logger.info("节点图已清空")

    def cleanup(self):
        """清理节点图资源，断开信号，移除事件过滤器"""
        if not self.node_graph:
            return

        # 断开所有结构信号
        if self._signals:
            self._signals.dispose()

        # 移除事件过滤器（视口）
        if self.view:
            viewport = self.view.viewport()
            if viewport:
                try:
                    viewport.removeEventFilter(self)
                except Exception:
                    pass
            # 可选：移除视图本身的过滤器（如果之前安装过）
            try:
                self.view.removeEventFilter(self)
            except Exception:
                pass

        # 删除图形部件
        if self.graph_widget:
            self.graph_widget.deleteLater()

        # 释放引用
        self.node_graph = None
        self.graph_widget = None
        self.view = None
