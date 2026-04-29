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
from collections import deque
from typing import Dict, List

from PyQt5.QtCore import QObject, QThread

from core.events import event_bus

logger = logging.getLogger(__name__)


class WorkflowWorker(QObject):
    def __init__(self, node_graph,thread):
        super().__init__()
        self.node_graph = node_graph
        self._thread = thread  # 保存线程引用
        self._stop_flag = False
        self._pause_flag = False

        # 连接控制信号到内部槽（这些槽会在 worker 所在的线程中执行）

        event_bus.stop_signal.connect(self._on_stop)


    def run(self):
        """线程启动后自动执行此方法（通过 started 信号触发）"""
        event_bus.execution_started.emit()
        try:
            start_node = self._find_start_node()
            if not start_node:
                event_bus.error_occurred.emit("","未找到开始节点")
                return
            self._execute_graph(start_node)
        except Exception as e:
            event_bus.error_occurred.emit("",str(e))
        finally:
            event_bus.execution_finished.emit(True)
            self._thread.quit()  # 让事件循环退出，触发 finished 信号

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

    # ---------- 业务逻辑----------
    def _topological_sort(self) -> List:
        """对节点图进行拓扑排序，返回执行顺序列表"""
        # 获取所有节点
        all_nodes = self.node_graph.all_nodes()
        # 构建依赖图：节点 -> 前驱节点列表（输入连接）
        graph = {node: set() for node in all_nodes}
        for node in all_nodes:
            # 遍历节点的输入端口，找到连接到这些端口的源节点
            for port in node.input_ports():
                connections = port.connected_ports()
                for src_port in connections:
                    src_node = src_port.node()
                    graph[node].add(src_node)

        # Kahn算法
        in_degree = {node: len(graph[node]) for node in all_nodes}
        queue = deque([node for node in all_nodes if in_degree[node] == 0])
        result = []
        while queue:
            node = queue.popleft()
            result.append(node)
            # 找到以node为前驱的节点（即node的输出端口连接的节点）
            for other in all_nodes:
                if node in graph[other]:
                    in_degree[other] -= 1
                    if in_degree[other] == 0:
                        queue.append(other)

        if len(result) != len(all_nodes):
            # 存在循环依赖
            return []
        return result

    def _find_start_node(self):
        for node in self.node_graph.all_nodes():
            if hasattr(node, 'is_start_node') and node.is_start_node():
                return node
        return None

    def _execute_graph(self, start_node):
        node_outputs = {}
        current_node = start_node
        while current_node and not self._stop_flag:
            # 暂停检查
            while self._pause_flag and not self._stop_flag:
                time.sleep(0.1)

            node_name = current_node.name()
            event_bus.node_started.emit(node_name)
            try:
                # 收集输入数据
                inputs = self._collect_inputs(current_node, node_outputs)
                # 执行节点
                outputs, next_port = current_node.execute(inputs)
                node_outputs[current_node] = outputs
                event_bus.node_finished.emit(node_name,outputs)

                # 根据 next_port 找到下一个节点
                if next_port is None:
                    break
                current_node = self._get_next_node(current_node, next_port)
            except Exception as e:
                event_bus.error_occurred.emit(f"节点 {node_name} 执行失败: {str(e)}")
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

class WorkflowExecutor(QObject):
    """对外的工作流控制器（运行在主线程）"""
    def __init__(self, node_graph):
        super().__init__()
        self.node_graph = node_graph
        self._thread = None
        self._worker = None

        # 监听全局结束事件来重置状态
        # event_bus.execution_finished.connect(self._on_execution_finished)

    def start(self):
         # 如果有正在运行的线程，拒绝新请求
        if self._thread is not None and self._thread.isRunning():
            logger.warning("工作流已在执行中")
            return
        # 清理已停止但未彻底销毁的旧线程
        self._cleanup()

        # 创建新执行环境
        self._thread = QThread()
        self._worker = WorkflowWorker(self.node_graph,self._thread)
        self._worker.moveToThread(self._thread)

         # 关键：先连接finished信号再启动线程
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.started.connect(self._worker.run)
         # 启动线程
        self._thread.start()
         # 添加调试日志
        logger.debug("工作流线程已启动，thread ID: %s", self._thread.currentThreadId())

    def _cleanup(self):
        """主动清理旧的线程对象（如果还存在且已停止）"""
        if self._thread:
            # 断开所有信号连接，避免残留影响新线程
            try:
                self._thread.started.disconnect()
            except TypeError:
                pass
            try:
                self._thread.finished.disconnect()
            except TypeError:
                pass

            # 确保线程已退出，否则等待
            if self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(1000)

            # 安排删除（注意：不能立即 deleteLater，因为 finished 信号可能还未触发）
            # 但我们会在 finished 中删除，所以这里先保留对象
            # 实际上这里只是断开连接，不删除对象
        if self._worker:
            # worker 会随着 thread 的 finished 一起删除
            self._worker = None

    def pause(self):
        """暂停执行（线程安全）"""
        if self._worker:
            self._worker.pause_signal.emit()   # 通过信号跨线程发送

    def resume(self):
        """恢复执行"""
        if self._worker:
            self._worker.resume_signal.emit()

    def stop(self):
        """终止执行"""
        if self._worker:
            event_bus.stop_signal.emit()

    # def _cleanup_thread(self, immediate=False):
    #     """主动清理线程和worker"""
    #     if self._thread:
    #         # 如果线程还在运行，请求退出并等待
    #         if self._thread.isRunning():
    #             self._thread.quit()
    #             if immediate:
    #                 self._thread.wait(2000)  # 等待最多2秒完全退出
    #
    #         # 断开所有信号连接，避免残留
    #         try:
    #             self._thread.started.disconnect()
    #         except TypeError:
    #             pass
    #         try:
    #             self._thread.finished.disconnect()
    #         except TypeError:
    #             pass
    #
    #         # 安全删除对象（会在事件循环中稍后删除）
    #         self._thread.deleteLater()
    #         self._thread = None
    #
    #     if self._worker:
    #         self._worker.deleteLater()
    #         self._worker = None

    # ---------- 以下槽函数在主线程中执行，用于转发 worker 的信号 ----------
    # def _on_execution_finished(self, success):
    #     """工作流执行结束后立即清理线程（无论成功失败）"""
    #     self._cleanup_thread(immediate=True)

    def _on_thread_finished(self):
        """线程完全结束后自动调用（主线程中执行）"""
        logger.debug("进入_on_thread_finished方法")
        # 删除线程和 worker 对象
        if self._thread:
            self._thread.deleteLater()
            self._thread = None
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        logger.info("工作流线程已完全清理")

    def _on_worker_error(self, error_msg):
        logger.error(f"工作流错误: {error_msg}")
        # event_bus.error_occurred.emit(error_msg) 已经在 worker 中发射过了

    def _on_node_started(self, node_name):
        # 如果需要额外的界面更新，可以在这里做
        pass

    def _on_node_finished(self, node_name, outputs):
        # 同上
        pass