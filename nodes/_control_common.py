# -*- coding: utf-8 -*-
"""
_control_common.py
功能描述: 控制流节点共享基础设施（模块名以 _ 开头，不参与节点自动发现）。
- StopFlag: 终止/暂停响应器。长耗时节点（等待、重试、子工作流）在执行循环中
  调用 check()/wait()，保证用户点「终止/暂停」后能及时生效。
  使用 Qt.DirectConnection：信号在主线程发射时立即在本槽执行（仅改布尔值），
  不依赖工作线程的事件循环（工作线程被 time.sleep 阻塞时队列投递不会送达）。
- WorkflowInterrupted: 用户主动终止引发的中断异常（不应路由到 fail 分支）。
- run_graph / run_subgraph_from_dict: 子工作流执行器。复刻 WorkflowWorker 的
  推进逻辑（端口流转、循环入口回流、fail 失败分支），但同步执行、不发事件总线。
"""
import logging
import time

from PyQt5.QtCore import Qt

from core.events import event_bus

_logger = logging.getLogger(__name__)

_MAX_SUBFLOW_DEPTH = 8      # 子工作流最大嵌套深度（防自调用死循环）
_depth = 0


class WorkflowInterrupted(RuntimeError):
    """用户终止/工作流被中断（不应路由到 fail 分支，直接终止）。"""


class StopFlag:
    """终止/暂停响应器。长耗时节点在循环中定期 check() / wait()。"""

    def __init__(self):
        self.stopped = False
        self.paused = False
        event_bus.stop_signal.connect(self._on_stop, Qt.DirectConnection)
        event_bus.pause_signal.connect(self._on_pause, Qt.DirectConnection)
        event_bus.resume_signal.connect(self._on_resume, Qt.DirectConnection)

    def _on_stop(self):
        self.stopped = True

    def _on_pause(self):
        self.paused = True

    def _on_resume(self):
        self.paused = False

    def check(self):
        """快速检查点：已终止则抛 WorkflowInterrupted；暂停则阻塞等待恢复。"""
        if self.stopped:
            raise WorkflowInterrupted('工作流已被终止')
        while self.paused and not self.stopped:
            time.sleep(0.05)
        if self.stopped:
            raise WorkflowInterrupted('工作流已被终止')

    def wait(self, seconds):
        """可中断睡眠：期间响应终止与暂停。"""
        end = time.monotonic() + max(0.0, float(seconds))
        while True:
            remaining = end - time.monotonic()
            if remaining <= 0:
                return
            if self.stopped:
                raise WorkflowInterrupted('工作流已被终止')
            time.sleep(min(0.05, remaining))

    def close(self):
        """解除信号连接（execute 结束时调用，防泄漏）。"""
        try:
            event_bus.stop_signal.disconnect(self._on_stop)
            event_bus.pause_signal.disconnect(self._on_pause)
            event_bus.resume_signal.disconnect(self._on_resume)
        except TypeError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


# ---------------- 子工作流图数据加载 ----------------

def load_graph_dict(file_path):
    """加载 .awflow / .json 工作流文件 → 可反序列化的图数据 dict。"""
    import os
    path = (file_path or '').strip()
    if not path:
        raise RuntimeError('未设置子工作流文件路径')
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise RuntimeError(f'子工作流文件不存在: {path}')

    from core.graph import awflow
    if awflow.is_awflow(path):
        return awflow.unpack_workflow(path)
    import json
    with open(path, 'r', encoding='utf-8') as f:
        graph_dict = json.load(f)
    awflow.resolve_relative_resources(
        graph_dict, os.path.dirname(path))
    return graph_dict


# ---------------- 子工作流同步执行器 ----------------

def collect_inputs(node, node_outputs):
    """收集节点输入（与 WorkflowWorker._collect_inputs 同规则：每端口取第一条连接）。"""
    inputs = {}
    for port in node.input_ports():
        connections = port.connected_ports()
        if connections:
            src_port = connections[0]
            src_node = src_port.node()
            if src_node in node_outputs:
                inputs[port.name()] = node_outputs[src_node].get(src_port.name())
    return inputs


def _fail_target(node):
    """返回节点 fail 出口连接的下游 (node, input_port)，未连接返回 (None, None)。"""
    for port in node.output_ports():
        if port.name() == 'fail':
            conns = port.connected_ports()
            if conns:
                return conns[0].node(), conns[0]
            break
    return None, None


def run_graph(graph, stop_flag):
    """在已反序列化的图上从「开始」节点同步执行到结束（复刻 WorkflowWorker 语义）。

    返回结束节点（或末节点）的输出 dict。节点抛异常且未连接 fail 分支时向上抛出。
    """
    start = None
    for n in graph.all_nodes():
        if n.is_start_node():
            start = n
            break
    if start is None:
        raise RuntimeError('子工作流缺少「开始」节点')
    for n in graph.all_nodes():
        if hasattr(n, 'reset'):
            n.reset()

    node_outputs = {}
    current = start
    inputs = collect_inputs(current, node_outputs)
    while current is not None:
        stop_flag.check()
        node_name = current.name()
        try:
            outputs, next_port = current.execute(inputs)
        except WorkflowInterrupted:
            raise
        except Exception as e:
            next_node, next_in = _fail_target(current)
            if next_node is None:
                raise RuntimeError(f'子流程节点「{node_name}」执行失败: {e}') from e
            _logger.info('子流程节点「%s」执行失败，转入 fail 分支: %s', node_name, e)
        else:
            node_outputs[current] = outputs
            next_node = next_in = None
            if next_port is not None:
                next_node, next_in = None, None
                for port in current.output_ports():
                    if port.name() == next_port:
                        conns = port.connected_ports()
                        if conns:
                            next_in = conns[0]
                            next_node = next_in.node()
                        break
            if (getattr(current, 'is_loop_entry', False)
                    and inputs.get('__trigger__') == 'next'):
                next_node = current.get_decision_node()
                next_in = None
        # 为下一步收集输入
        if next_node is None:
            break
        inputs = collect_inputs(next_node, node_outputs)
        inputs['__trigger__'] = next_in.name() if next_in is not None else None
        current = next_node
    return node_outputs.get(current) or {}


def run_subgraph_from_dict(graph_dict, stop_flag):
    """构建临时无头图并同步执行子工作流。嵌套深度超限时抛错。"""
    global _depth
    if _depth >= _MAX_SUBFLOW_DEPTH:
        raise RuntimeError(f'子工作流嵌套过深（>{_MAX_SUBFLOW_DEPTH} 层），请检查是否存在自调用')
    _depth += 1
    try:
        from NodeGraphQt import NodeGraph
        from nodes import discover_nodes

        graph = NodeGraph()
        for cls in discover_nodes():
            graph.register_node(cls)
        try:
            graph.deserialize_session(graph_dict)
            return run_graph(graph, stop_flag)
        finally:
            try:
                graph.clear_session()
            except Exception:
                pass
    finally:
        _depth -= 1
