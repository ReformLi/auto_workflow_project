# -*- coding: utf-8 -*-
"""
__init__.py
作者: reformLi
创建日期: 2026/3/25
最后修改: 2026/3/25
版本: 1.0.0

功能描述: 扫描当前包内所有 Python 模块（排除 __init__ 和基类模块），并收集 AutomationBaseNode 的子类
"""
# nodes/__init__.py
import os
import importlib
import inspect
from .base_node import WorkflowNode

def discover_nodes():
    """
    自动发现当前包下所有继承自 WorkflowNode 的节点类。
    返回一个节点类列表。
    """
    nodes_dir = os.path.dirname(__file__)
    node_classes = []

    # 遍历当前目录下的所有 .py 文件
    for filename in os.listdir(nodes_dir):
        if filename.startswith('_') or not filename.endswith('.py'):
            continue
        module_name = filename[:-3]  # 去除 .py 后缀

        # 动态导入模块
        module = importlib.import_module(f'.{module_name}', package=__package__)

        # 从模块中提取 WorkflowNode 的子类
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, WorkflowNode) and obj is not WorkflowNode:
                node_classes.append(obj)

    return node_classes