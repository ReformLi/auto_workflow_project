# -*- coding: utf-8 -*-
"""
serialization.py
功能描述: 工作流序列化/反序列化与文件读写
         保存: .awflow（ZIP 容器，默认） / .json（旧格式/导出）
         打开: .awflow 与 .json 均支持
"""
import os

from core.workflow import WorkflowModel
from core.graph import awflow


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
        """保存为 .awflow（默认，ZIP 打包）或 .json（纯 JSON + 外部 resources 文件夹导出）"""
        if not self.node_graph:
            self.logger.warning("节点图未初始化，无法保存")
            return False
        try:
            if awflow.is_awflow(file_path):
                graph_dict = self.node_graph.serialize_session()
                awflow.pack_workflow(graph_dict, file_path)
            else:
                graph_dict = self.node_graph.serialize_session()
                awflow.export_json_resources(graph_dict, file_path)
            self.logger.info(f"节点图已保存到: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"保存节点图失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def load_from_file(self, file_path: str):
        """从 .awflow 或 .json 文件加载工作流（加载期间抑制结构信号回调）"""
        if not self.node_graph:
            self.logger.warning("节点图未初始化，无法加载")
            return False
        try:
            with self._signals.suppressed():
                if awflow.is_awflow(file_path):
                    graph_dict = awflow.unpack_workflow(file_path)
                    self.node_graph.deserialize_session(graph_dict)
                else:
                    # 旧 .json：先重定位相对资源路径到文件所在目录，再反序列化
                    graph_dict = self._read_json_session(file_path)
                    awflow.resolve_relative_resources(
                        graph_dict, os.path.dirname(os.path.abspath(file_path)))
                    self.node_graph.deserialize_session(graph_dict)
            self.logger.info(f"从文件加载节点图: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"加载节点图失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    @staticmethod
    def _read_json_session(file_path: str):
        """读取 .json 会话内容（沿用 NodeGraphQt load_session 的读取方式）"""
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
