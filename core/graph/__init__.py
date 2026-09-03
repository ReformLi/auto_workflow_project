# -*- coding: utf-8 -*-
"""
core/graph 包入口
功能描述: 节点图管理模块（生命周期/信号/序列化/编辑/剪贴板），re-export 保持
         `from core.graph import NodeGraphManager` 兼容
"""
from core.graph.manager import NodeGraphManager

__all__ = ['NodeGraphManager']
