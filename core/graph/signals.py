# -*- coding: utf-8 -*-
"""
signals.py
功能描述: NodeGraphQt 结构信号的集中管理——连接/断开/日志回调/临时抑制上下文管理器
"""
import logging
from contextlib import contextmanager


class GraphSignalManager:
    """集中管理 node_graph 的四个结构信号：
    node_created / nodes_deleted / port_connected / port_disconnected
    """

    def __init__(self, node_graph):
        self._node_graph = node_graph
        self.logger = logging.getLogger(__name__)
        self._bindings = (
            ('node_created', self.on_node_created),
            ('nodes_deleted', self.on_node_deleted),
            ('port_connected', self.on_node_connected),
            ('port_disconnected', self.on_node_disconnected),
        )

    def connect_all(self):
        """幂等地恢复全部连接（先断后连，防止重复叠加）"""
        for name, slot in self._bindings:
            sig = getattr(self._node_graph, name, None)
            if sig is None:
                continue
            try:
                sig.disconnect(slot)
            except (TypeError, AttributeError):
                pass
            try:
                sig.connect(slot)
            except (TypeError, AttributeError):
                pass

    def disconnect_all(self):
        """断开全部连接"""
        for name, slot in self._bindings:
            try:
                getattr(self._node_graph, name).disconnect(slot)
            except (TypeError, AttributeError):
                pass

    @contextmanager
    def suppressed(self):
        """临时断开全部结构信号；块内无论是否抛异常，退出时保证恢复连接。

        约定：不可嵌套使用。
        """
        self.disconnect_all()
        try:
            yield
        finally:
            self.connect_all()

    def dispose(self):
        """永久断开全部连接（仅在 cleanup 时调用）"""
        self.disconnect_all()

    # --------------- 日志回调 ---------------
    def on_node_created(self, node):
        try:
            self.logger.info(f'创建节点: {node.name()}')
        except Exception as e:
            self.logger.debug(f"节点创建回调异常: {e}")

    def on_node_deleted(self, node):
        try:
            # 节点可能已部分销毁，直接记录名称可能失败
            if node:
                self.logger.info(f'删除节点: {node.name()}')
        except Exception:
            self.logger.info('删除节点（无法获取名称）')

    def on_node_connected(self, src_port, trg_port):
        try:
            src_node = src_port.node().name()
            trg_node = trg_port.node().name()
            self.logger.info(f'连接节点: {src_node} -> {trg_node}')
        except Exception as e:
            self.logger.debug(f"连接回调异常: {e}")

    def on_node_disconnected(self, src_port, trg_port):
        try:
            src_node = src_port.node().name()
            trg_node = trg_port.node().name()
            self.logger.info(f'断开节点: {src_node} -> {trg_node}')
        except Exception as e:
            self.logger.debug(f"断开回调异常: {e}")
