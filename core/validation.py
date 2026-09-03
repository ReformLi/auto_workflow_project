# -*- coding: utf-8 -*-
"""
validation.py
功能描述: 工作流结构验证的唯一权威实现（CoreManager 与执行器共用）
"""


class WorkflowValidator:
    """工作流结构验证器：基于节点类型标记（is_start_node/is_end_node）判定"""

    @staticmethod
    def validate(nodes) -> dict:
        """验证节点列表构成的工作流结构

        Args:
            nodes: 节点对象列表

        Returns:
            {'success': bool, 'message': str}
        """
        if not nodes:
            return {'success': False, 'message': '工作流为空，请添加节点'}

        start_nodes = [n for n in nodes if hasattr(n, 'is_start_node') and n.is_start_node()]
        if not start_nodes:
            return {'success': False, 'message': '工作流缺少开始节点'}

        end_nodes = [n for n in nodes if hasattr(n, 'is_end_node') and n.is_end_node()]
        if not end_nodes:
            return {'success': False, 'message': '工作流缺少结束节点'}

        return {'success': True, 'message': '工作流验证通过'}
