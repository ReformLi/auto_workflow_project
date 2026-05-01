# -*- coding: utf-8 -*-
"""
events.py
作者: reformLi
创建日期: 2026/4/25
最后修改: 2026/4/25
版本: 1.0.0

功能描述: 事件总线：事件总线使用 PyQt5 信号机制，将执行过程中的关键事件统一广播出去。UI 层和 core 内部均通过订阅这些信号来响应状态变化，而不需要直接持有其他对象的引用。
"""
# core/events.py
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal


class WorkflowEvents(QObject):
    """全局工作流执行事件信号"""
    # 工作流执行开始/结束
    execution_started = pyqtSignal()
    execution_finished = pyqtSignal(bool)# 参数: 是否成功

    # 节点执行状态
    node_started = pyqtSignal(str)  # 节点名称
    node_finished = pyqtSignal(str, dict)  # 节点名称, 输出数据

    # 操作
    execution_paused = pyqtSignal()
    execution_resumed = pyqtSignal()
    execution_stopped = pyqtSignal()

    # 错误信息
    error_occurred = pyqtSignal(str)      #  错误信息

    # 图结构变更（供 UI 同步）
    graph_changed = pyqtSignal()

    # 线程生命周期
    finished = pyqtSignal()  # 线程结束

    stop_signal = pyqtSignal()

    # 拖拽创建节点时使用  str:节点类型,QtCore.QPointF:节点创建坐标
    node_dropped = pyqtSignal(str, QtCore.QPointF)

    # 新增两个信号，用于向主线程传递节点执行开始/结束信息（携带节点ID）
    node_exec_started = pyqtSignal(str)  # node_id
    node_exec_finished = pyqtSignal(str, float, bool)  # node_id, elapsed_seconds, is_error



    def __init__(self, parent=None):
        super().__init__(parent)


# 全局单例（仅此一份，通过导入使用）
event_bus = WorkflowEvents()