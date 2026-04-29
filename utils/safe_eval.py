# -*- coding: utf-8 -*-
"""
safe_eval.py
作者: reformLi
创建日期: 2026/4/22
最后修改: 2026/4/22
版本: 1.0.0

功能描述: 安全求值模块
"""
import ast
import operator

# 支持的操作符映射
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.And: lambda x, y: x and y,
    ast.Or: lambda x, y: x or y,
    ast.Not: operator.not_,
    ast.Is: lambda x, y: x is y,
    ast.IsNot: lambda x, y: x is not y,
    ast.In: lambda x, y: x in y,
    ast.NotIn: lambda x, y: x not in y,
}

class SafeEvalError(Exception):
    pass

def safe_eval(expr: str, context: dict = None):
    """
    安全地求值表达式，仅支持基本运算、比较、逻辑运算和变量访问。
    context 字典提供变量值。
    """
    if context is None:
        context = {}
    tree = ast.parse(expr, mode='eval')
    return _eval_node(tree.body, context)

def _eval_node(node, context):
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Name):
        if node.id in context:
            return context[node.id]
        raise SafeEvalError(f"未定义的变量: {node.id}")
    elif isinstance(node, ast.BinOp):
        left = _eval_node(node.left, context)
        right = _eval_node(node.right, context)
        op = _OPERATORS.get(type(node.op))
        if op is None:
            raise SafeEvalError(f"不支持的操作符: {type(node.op).__name__}")
        return op(left, right)
    elif isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, context)
        op = _OPERATORS.get(type(node.op))
        if op is None:
            raise SafeEvalError(f"不支持的一元操作符: {type(node.op).__name__}")
        return op(operand)
    elif isinstance(node, ast.Compare):
        left = _eval_node(node.left, context)
        result = True
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator, context)
            op_func = _OPERATORS.get(type(op))
            if op_func is None:
                raise SafeEvalError(f"不支持的操作符: {type(op).__name__}")
            result = result and op_func(left, right)
            left = right
        return result
    elif isinstance(node, ast.BoolOp):
        values = [_eval_node(v, context) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        elif isinstance(node.op, ast.Or):
            return any(values)
        else:
            raise SafeEvalError(f"不支持的逻辑操作: {type(node.op).__name__}")
    else:
        raise SafeEvalError(f"不支持的表达式节点: {type(node).__name__}")