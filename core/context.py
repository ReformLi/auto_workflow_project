# -*- coding: utf-8 -*-
"""
context.py
作者: reformLi
创建日期: 2026/4/28
最后修改: 2026/4/28
版本: 1.0.0

功能描述: 全局上下文模块代码
"""
# core/context.py
"""
工作流执行上下文：提供键值存储，用于节点间共享变量（如窗口句柄）。
使用 threading.local 保证线程安全（后续若将执行器放入线程）。
"""
import threading
from typing import Any, Hashable

_local = threading.local()

class WorkflowContext:
    """工作流全局上下文，可在任何模块通过 get_context() 获取"""

    def __init__(self):
        self._data: dict[Hashable, Any] = {}

    def set(self, key: Hashable, value: Any) -> None:
        self._data[key] = value

    def get(self, key: Hashable, default: Any = None) -> Any:
        return self._data.get(key, default)

    def delete(self, key: str):
        """删除变量"""
        self._data.pop(key, None)

    def clear(self):
        """清空所有变量（工作流结束时使用）"""
        self._data.clear()

    def __contains__(self, key):
        return key in self._data

# 单例工厂（每个线程一个实例）
def get_context() -> WorkflowContext:
    if not hasattr(_local, 'context'):
        _local.context = WorkflowContext()
    return _local.context