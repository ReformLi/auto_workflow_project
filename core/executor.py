# -*- coding: utf-8 -*-
"""
executor.py
作者: reformLi
创建日期: 2026/4/9
最后修改: 2026/4/9
版本: 1.0.0

功能描述:
"""
import logging
import time
from typing import Dict

from PyQt5.QtCore import QObject, QThread

from core.events import event_bus
from nodes import WorkflowNode

logger = logging.getLogger(__name__)


# ================= 工作流工作器（运行在子线程） =================
class WorkflowWorker(QObject):

    def __init__(self, node_graph, thread):
        super().__init__()
        self.node_graph = node_graph
        self._thread = thread
        self._stop_flag = False
        self._pause_flag = False
        # 连接控制信号（来自事件总线，但仍会在子线程中执行槽函数）
        event_bus.stop_signal.connect(self._on_stop)

    def run(self):
        """线程启动后自动执行（通过 started 信号触发）"""
        event_bus.execution_started.emit()
        try:
            start_node = self._find_start_node()
            if not start_node:
                event_bus.error_occurred.emit("", "未找到开始节点")
                return
            self._execute_graph(start_node)
            event_bus.execution_finished.emit(True)
        except Exception as e:
            event_bus.error_occurred.emit(str(e))
            event_bus.execution_finished.emit(False)
        finally:
            self._thread.quit()

    # ---------- 核心执行逻辑 ----------
    def _execute_graph(self, start_node):
        node_outputs = {}
        current_node = start_node
        while current_node and not self._stop_flag:
            # 暂停检查
            while self._pause_flag and not self._stop_flag:
                time.sleep(0.1)

            node_id = current_node.get_node_id()   # 获取唯一ID
            node_name = current_node.name()

            # 发射节点开始信号（传递节点ID）
            event_bus.node_exec_started.emit(node_id)
            event_bus.node_started.emit(node_name)   # 兼容旧版事件

            start_time = time.time()
            try:
                inputs = self._collect_inputs(current_node, node_outputs)
                outputs, next_port = current_node.execute(inputs)
                elapsed = time.time() - start_time
                node_outputs[current_node] = outputs
                # 发射节点成功结束信号（传递节点ID和耗时）
                event_bus.node_exec_finished.emit(node_id, elapsed, False)
                event_bus.node_finished.emit(node_name, outputs)
                # 根据 next_port 找到下一个节点
                if next_port is None:
                    break
                current_node = self._get_next_node(current_node, next_port)
            except Exception as e:
                elapsed = time.time() - start_time
                event_bus.node_exec_finished.emit(node_id, elapsed, True)
                event_bus.error_occurred.emit(f"节点 {node_name} 执行失败:{str(e)}")
                break

    def _collect_inputs(self, node, node_outputs: Dict) -> Dict:
        """收集节点的输入数据（从上游节点输出）"""
        inputs = {}
        for port in node.input_ports():
            connections = port.connected_ports()
            if connections:
                # 取第一个连接（假设单连接）
                src_port = connections[0]
                src_node = src_port.node()
                if src_node in node_outputs:
                    outputs = node_outputs[src_node]
                    # 根据端口名称获取数据（简单实现）
                    # 实际需要根据端口标识符匹配
                    data = outputs.get(src_port.name(), None)
                    inputs[port.name()] = data
                else:
                    # 上游节点尚未执行（不应该发生）
                    logger.warning(f"节点 {node.name()} 的输入端口 {port.name()} 连接的上游节点 {src_node.name()} 尚未执行")
        return inputs

    def _get_next_node(self, node, port_name):
        """根据节点和输出端口名获取下游连接的节点"""
        for port in node.output_ports():
            if port.name() == port_name:
                connections = port.connected_ports()
                if connections:
                    next_port = connections[0]
                    return next_port.node()
        return None

    def _find_start_node(self):
        for node in self.node_graph.all_nodes():
            if hasattr(node, 'is_start_node') and node.is_start_node():
                return node
        return None

    def finished(self):
        pass

    # ---------- 控制槽（在子线程中执行，安全修改标志）----------
    def _on_stop(self):
        self._stop_flag = True
        logger.info("工作流终止请求")

    def _on_pause(self):
        self._pause_flag = True
        logger.info("工作流已暂停")

    def _on_resume(self):
        self._pause_flag = False
        logger.info("工作流已恢复")

    def _validate_workflow(self) -> bool:
        """验证工作流完整性：必须包含一个开始节点和一个结束节点，且开始节点无输入，结束节点无输出"""
        all_nodes = self.node_graph.all_nodes()
        start_nodes = [n for n in all_nodes if hasattr(n, 'is_start_node') and n.is_start_node()]
        end_nodes = [n for n in all_nodes if hasattr(n, 'is_end_node') and n.is_end_node()]

        if len(start_nodes) == 0:
            event_bus.error_occurred.emit("工作流缺少开始节点")
            return False
        if len(start_nodes) > 1:
            event_bus.error_occurred.emit("工作流包含多个开始节点，请确保只有一个")
            return False
        if len(end_nodes) == 0:
            event_bus.error_occurred.emit("工作流缺少结束节点")
            return False
        if len(end_nodes) > 1:
            event_bus.error_occurred.emit("工作流包含多个结束节点，请确保只有一个")
            return False

        # 可选：检查开始节点没有输入端口连接
        start_node = start_nodes[0]
        if start_node.input_ports() and any(
                start_node.input_ports()[i].connected_ports() for i in range(len(start_node.input_ports()))):
            event_bus.error_occurred.emit("开始节点不应有输入连接")
            return False

        # 检查结束节点没有输出端口连接
        end_node = end_nodes[0]
        if end_node.output_ports() and any(
                end_node.output_ports()[i].connected_ports() for i in range(len(end_node.output_ports()))):
            event_bus.error_occurred.emit("结束节点不应有输出连接")
            return False

        return True

# ================= 工作流执行器（运行在主线程） =================
class WorkflowExecutor(QObject):
    def __init__(self, node_graph):
        super().__init__()
        self.node_graph = node_graph
        self._thread = None
        self._worker = None

    def start(self):
        if self._thread is not None and self._thread.isRunning():
            logger.warning("工作流已在执行中")
            return
        self._cleanup()

        self._thread = QThread()
        self._worker = WorkflowWorker(self.node_graph, self._thread)
        self._worker.moveToThread(self._thread)

        # 连接工作器的信号到本执行器的槽（这些槽将在主线程执行）
        event_bus.node_exec_started.connect(self._on_node_started)
        event_bus.node_exec_finished.connect(self._on_node_finished)

        # 线程生命周期管理
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.started.connect(self._worker.run)

        self._thread.start()
        logger.debug("工作流线程已启动")

    def _cleanup(self):
        """清理旧的线程和worker"""
        if self._thread:
            try:
                self._thread.started.disconnect()
            except TypeError:
                pass
            try:
                self._thread.finished.disconnect()
            except TypeError:
                pass
            if self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(1000)
        self._worker = None

    def stop(self):
        if self._worker:
            event_bus.stop_signal.emit()

    # ---------- 以下槽函数在主线程中执行，安全更新节点UI ----------
    def _on_node_started(self, node_id: str):
        """节点开始执行时，将状态显示为“运行中”"""
        node = WorkflowNode.get_node_by_id(node_id)
        if node:
            node.update_status("▶ 运行中...")

    def _on_node_finished(self, node_id: str, elapsed: float, is_error: bool):
        """节点执行结束时，显示成功/失败及耗时"""
        node = WorkflowNode.get_node_by_id(node_id)
        if not node:
            return
        if is_error:
            node.update_status("❌ 执行失败", is_error=True)
        else:
            # 显示成功和耗时（保留两位小数）
            html = f"✓ 成功<br>⏱ {elapsed:.2f} 秒"
            node.update_status(html)

    def _on_thread_finished(self):
        """线程完全结束后自动清理"""
        logger.debug("工作流线程结束，清理资源")
        if self._thread:
            self._thread.deleteLater()
            self._thread = None
        if self._worker:
            self._worker.deleteLater()
            self._worker = None

    def _on_worker_error(self, error_msg):
        logger.error(f"工作流错误: {error_msg}")
        # event_bus.error_occurred.emit(error_msg) 已经在 worker 中发射过了