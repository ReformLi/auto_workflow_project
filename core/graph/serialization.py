# -*- coding: utf-8 -*-
"""
serialization.py
功能描述: 工作流序列化/反序列化与文件读写
"""
from core.workflow import WorkflowModel


class GraphSerializerMixin:
    """宿主协议：self.node_graph / self.logger / self._signals(GraphSignalManager)"""

    def to_workflow_model(self) -> WorkflowModel:
        """将当前图导出为 WorkflowModel"""
        graph_dict = self.node_graph.serialize_session()  # NodeGraphQt 内置序列化
        model = WorkflowModel()
        model.nodes = graph_dict.get("nodes", {})
        model.connections = graph_dict.get("connections", [])
        return model

    def from_workflow_model(self, model: WorkflowModel):
        """清空当前图，并从 WorkflowModel 重建"""
        self.node_graph.clear_session()
        self.node_graph.deserialize_session({
            "nodes": model.nodes,
            "connections": model.connections,
        })

    def save_to_file(self, file_path: str):
        """保存为 .json 工作流文件"""
        if not self.node_graph:
            self.logger.warning("节点图未初始化，无法保存")
            return False
        try:
            self.node_graph.save_session(file_path)
            self.logger.info(f"节点图已保存到: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"保存节点图失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def load_from_file(self, file_path: str):
        """从文件加载工作流（加载期间抑制结构信号回调）"""
        if not self.node_graph:
            self.logger.warning("节点图未初始化，无法加载")
            return False
        try:
            with self._signals.suppressed():
                # 加载会话（内部会清空现有图并重新创建节点）
                self.node_graph.load_session(file_path)
            self.logger.info(f"从文件加载节点图: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"加载节点图失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
