# -*- coding: utf-8 -*-
"""
editing.py
功能描述: undo/redo 与选中节点/连接的删除操作
"""


class GraphEditingMixin:
    """宿主协议：self.node_graph / self.view / self.logger / self._signals(GraphSignalManager)"""

    def undo(self):
        """安全撤销（期间抑制结构信号回调）"""
        if not self.node_graph:
            return

        try:
            with self._signals.suppressed():
                stack = self.node_graph.undo_stack()
                if stack and stack.canUndo():
                    stack.undo()
                else:
                    self.logger.warning("无法找到撤销方法")
        except Exception as e:
            self.logger.error(f"撤销失败: {e}")

    def redo(self):
        """安全重做（期间抑制结构信号回调）"""
        if not self.node_graph:
            return

        try:
            with self._signals.suppressed():
                stack = self.node_graph.undo_stack()
                if stack and stack.canRedo():
                    stack.redo()
                else:
                    self.logger.warning("无法找到重做方法")
        except Exception as e:
            self.logger.error(f"重做失败: {e}")

    def delete_selected_nodes(self):
        """删除所有选中的节点（同时自动删除相关连接）"""
        if not self.node_graph:
            return
        selected_nodes = self.node_graph.selected_nodes()
        if not selected_nodes:
            self.logger.debug("没有选中的节点")
            return

        try:
            with self._signals.suppressed():
                for node in selected_nodes:
                    self.node_graph.delete_node(node)
            self.logger.info(f"已删除 {len(selected_nodes)} 个节点")
        except Exception as e:
            self.logger.error(f"删除节点失败: {e}")

    def delete_selected_connections(self):
        """删除所有选中的连接线"""
        if not self.node_graph:
            return
        # NodeGraphQt 中获取选中连接的方法通常是 selected_connections()
        if hasattr(self.node_graph, 'selected_connections'):
            selected_conns = self.node_graph.selected_connections()
        else:
            selected_conns = []
        if not selected_conns:
            self.logger.debug("没有选中的连接")
            return

        try:
            with self._signals.suppressed():
                for conn in selected_conns:
                    # 获取端口并断开
                    if hasattr(conn, 'source_port') and hasattr(conn, 'target_port'):
                        src_port = conn.source_port
                        trg_port = conn.target_port
                        if src_port and trg_port:
                            src_port.disconnect(trg_port)
            self.logger.info(f"已删除 {len(selected_conns)} 条连接")
        except Exception as e:
            self.logger.error(f"删除连接失败: {e}")

    def delete_selected(self):
        """删除所有选中的节点和连接（综合）"""
        # 删除选中连接（先删连接，再删节点，避免节点删除时重复触发）
        self.delete_selected_connections()
        self.delete_selected_nodes()
