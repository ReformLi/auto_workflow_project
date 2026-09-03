# -*- coding: utf-8 -*-
"""
clipboard.py
功能描述: 节点的复制/粘贴（基于系统剪贴板传递 JSON）
"""
import json

from PyQt5.QtCore import QMimeData, QPointF
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication


class GraphClipboardMixin:
    """宿主协议：self.node_graph / self.view / self.logger"""

    def copy_selected_nodes(self):
        """复制选中的节点"""
        if not self.node_graph:
            return
        selected = self.node_graph.selected_nodes()
        if not selected:
            self.logger.debug("没有选中节点，无法复制")
            return

        # 序列化选中的节点（手动提取必要信息）
        nodes_data = []
        for node in selected:
            # 获取节点类型标识符（如 workflow.StartNode）
            node_type = node.type_
            # 获取节点属性（位置等）
            pos = node.pos()
            properties = {}
            nodes_data.append({
                'type': node_type,
                'x': pos[0],
                'y': pos[1],
                'properties': properties,
                # 可选：保存节点名称（可能重复）
                'name': node.name(),
            })

        # 转换为 JSON 并存入剪贴板
        data_str = json.dumps(nodes_data)
        mime_data = QMimeData()
        mime_data.setText(data_str)
        QApplication.clipboard().setMimeData(mime_data)
        self.logger.info(f"已复制 {len(selected)} 个节点")

    def paste_nodes(self, scene_pos=None):
        """粘贴节点到场景指定位置（默认鼠标位置）"""
        if not self.node_graph:
            return

        mime_data = QApplication.clipboard().mimeData()
        if not mime_data or not mime_data.hasText():
            self.logger.debug("剪贴板无节点数据")
            return

        try:
            nodes_data = json.loads(mime_data.text())
        except Exception as e:
            self.logger.error(f"解析剪贴板数据失败: {e}")
            return

        # 获取粘贴位置（场景坐标）
        if scene_pos is None:
            # 获取鼠标的全局位置（使用 QCursor）
            global_pos = QCursor.pos()
            # 转换为视图坐标
            view_pos = self.view.mapFromGlobal(global_pos)
            # 转换为场景坐标
            scene_pos = self.view.mapToScene(view_pos)
            # 如果场景坐标无效（例如视图外），则使用视图中心
            if not scene_pos or (scene_pos.x() == 0 and scene_pos.y() == 0):
                rect = self.view.sceneRect()
                scene_pos = rect.center() if rect.isValid() else QPointF(0, 0)

        offset_x, offset_y = 30, 30
        created_nodes = []
        for i, data in enumerate(nodes_data):
            try:
                node_type = data.get('type')
                if not node_type:
                    self.logger.warning(f"数据缺少 'type' 字段: {data}")
                    continue

                # 创建节点
                node = self.node_graph.create_node(node_type)
                if not node:
                    self.logger.warning(f"无法创建节点类型: {node_type}")
                    continue

                # 设置位置（以鼠标位置为基准，网格偏移）
                new_x = scene_pos.x() + (i % 5) * offset_x
                new_y = scene_pos.y() + (i // 5) * offset_y
                node.set_pos(new_x, new_y)

                # 设置其他属性（如名称）
                new_name = data.get('name')
                if new_name and new_name != node.name():
                    node.set_name(new_name)

                created_nodes.append(node)
                self.logger.debug(f"粘贴节点 {node_type} 成功，位置 ({new_x}, {new_y})")
            except Exception as e:
                self.logger.error(f"粘贴单个节点失败: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                # 继续处理下一个节点

        self.logger.info(f"已粘贴 {len(created_nodes)} 个节点")
        return created_nodes
