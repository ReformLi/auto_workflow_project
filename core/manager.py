# -*- coding: utf-8 -*-
"""
manager.py
作者: reformLi
创建日期: 2026/4/25
最后修改: 2026/4/25
版本: 1.0.0

功能描述: 核心管理器--CoreManager 是核心业务层的对外门面，负责初始化 NodeGraphManager 和 WorkflowExecutor，并将它们与 UI 所需信号接通。
"""
# core/manager.py
from core.graph import NodeGraphManager
from core.executor import WorkflowExecutor
from core.events import event_bus
from nodes import discover_nodes


class CoreManager:
    """核心业务管理器，是 UI 层与核心层的唯一交互接口"""

    def __init__(self):
        # 初始化图管理器（widget 将在稍后由 UI 嵌入）
        self.graph_manager = NodeGraphManager()
        # 初始化执行引擎
        self._executor = WorkflowExecutor(self.graph_manager.node_graph)

        # 动态发现并注册所有节点
        self._node_classes = discover_nodes()
        self.graph_manager.register_node_classes(self._node_classes)

        # 可在此处连接内部信号，执行额外的业务逻辑
        event_bus.execution_finished.connect(self._on_execution_finished)

    def execute_workflow(self):
        """执行当前工作流（由 UI 触发）"""
        self._executor.start()

    def new_workflow(self):
        """清空并新建工作流"""
        self.graph_manager.node_graph.clear_session()

    def save_workflow(self, filepath: str):
        return self.graph_manager.save_to_file(filepath)

    def load_workflow(self, filepath: str):
        return self.graph_manager.load_from_file(filepath)

    def clear_all(self):
        """清空所有节点和连接"""
        self.graph_manager.clear()
        # 可选：发射图变更事件
        event_bus.graph_changed.emit()

    def undo(self):
        """撤销操作"""
        self.graph_manager.undo()
        # 可选：发射图变更事件
        event_bus.graph_changed.emit()

    def redo(self):
        """重做操作"""
        self.graph_manager.redo()
        # 可选：发射图变更事件
        event_bus.graph_changed.emit()

    def cleanup(self):
        """清理节点图管理器"""
        self.graph_manager.cleanup()

    def copy_selected_nodes(self):
        """复制选中的节点"""
        self.graph_manager.copy_selected_nodes()

    def paste_nodes(self):
        """粘贴节点"""
        self.graph_manager.paste_nodes()

    def delete_selected(self):
        """删除选中的节点和连接"""
        self.graph_manager.delete_selected()

    def _on_execution_finished(self, success: bool):
        """执行结束后的清理或通知（可扩展）"""
        print(f"工作流执行完成: {'成功' if success else '失败'}")

    def get_available_nodes(self):
        """返回所有可用节点的菜单信息列表"""
        nodes_info = []
        for cls in self._node_classes:
            nodes_info.append({
                'node_type': cls.type_,                  # node_type  格式为："workflow.StartNode"
                'type': cls.__name__,                    # 类名
                'name': cls.NODE_NAME,                   # 显示名称
                # 'category': cls.NODE_CATEGORY,           # 分类
            })
        return nodes_info

    def get_node_property_defs(self, node_type: str):
        """返回指定节点类型的属性定义列表"""
        for cls in self._node_classes:
            if cls.__name__ == node_type:
                return cls.get_property_defs()
        return []

    def get_view(self):
        return self.graph_manager.view