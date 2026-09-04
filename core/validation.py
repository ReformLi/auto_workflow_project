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

        warnings = WorkflowValidator._check_loop_wiring(nodes)
        message = '工作流验证通过'
        if warnings:
            message += '\n' + '\n'.join('⚠ ' + w for w in warnings)
        return {'success': True, 'message': message, 'warnings': warnings}

    @staticmethod
    def _check_loop_wiring(nodes) -> list:
        """检查循环入口节点的连接是否符合规则，返回警告列表（不阻断执行）。"""
        warnings = []
        entries = [n for n in nodes
                   if getattr(n, 'is_loop_entry', False)]
        for ent in entries:
            in_map = {p.name(): p for p in ent.input_ports()}
            enter_p = in_map.get('enter')
            next_p = in_map.get('next')
            body_p = next((p for p in ent.output_ports() if p.name() == 'body'), None)
            # enter 必须连接任意一个"判断型"节点的 true 输出
            if enter_p and enter_p.connected_ports():
                src_port = enter_p.connected_ports()[0]
                src = src_port.node()
                has_true_or_false = any('true' == p.name() or 'false' == p.name()
                                        for p in src.output_ports())
                if not has_true_or_false:
                    warnings.append(f"循环入口「{ent.name()}」的 enter 应连接具备 true/false 输出的判断节点")
                elif src_port.name() != 'true':
                    warnings.append(f"循环入口「{ent.name()}」的 enter 应连接判断节点的 true 输出（当前连的是 {src_port.name()}）")
            else:
                warnings.append(f"循环入口「{ent.name()}」的 enter 未连接，无法开启循环")
            # next 必须连接循环体末尾节点的输出
            if next_p and next_p.connected_ports() and body_p and body_p.connected_ports():
                body_first = body_p.connected_ports()[0].node()
                next_src = next_p.connected_ports()[0].node()
                if next_src is body_first:
                    warnings.append(f"循环入口「{ent.name()}」的 next 接回了循环体首节点，建议连接循环体末尾节点")
            elif not (next_p and next_p.connected_ports()):
                warnings.append(f"循环入口「{ent.name()}」的 next 未连接（应接循环体末尾节点的输出）")
            if body_p and not body_p.connected_ports():
                warnings.append(f"循环入口「{ent.name()}」的 body 未连接循环体首个节点")
        return warnings
