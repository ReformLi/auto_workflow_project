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

# 允许调用的方法白名单（字符串 / 列表 / 字典等安全读操作）
_SAFE_METHODS = {
    # 字符串
    'startswith', 'endswith', 'find', 'index', 'count', 'format', 'upper',
    'lower', 'strip', 'lstrip', 'rstrip', 'split', 'rsplit', 'join',
    'replace', 'isdigit', 'isalpha', 'isalnum', 'isspace', 'contains',
    # 序列 / 映射
    'get', 'keys', 'values', 'items', 'copy', 'tolist',
}

# 允许调用的内置函数白名单
_SAFE_FUNCS = {
    'len': len, 'abs': abs, 'min': min, 'max': max, 'sum': sum,
    'all': all, 'any': any, 'str': str, 'int': int, 'float': float,
    'bool': bool, 'round': round, 'sorted': sorted, 'range': range,
    'isinstance': isinstance,
}

def safe_eval(expr: str, context: dict = None):
    """
    安全地求值表达式，支持：
    - 基本运算、比较、逻辑运算；
    - 变量访问、属性访问（如 input.startswith）、下标（如 context['key']）；
    - 白名单方法 / 内置函数调用。
    context 字典提供变量值。
    """
    if context is None:
        context = {}
    tree = ast.parse(expr, mode='eval')
    return _eval_node(tree.body, context)

def _eval_call(node, context):
    func = node.func
    args = [_eval_node(a, context) for a in node.args]
    kwargs = {}
    for kw in node.keywords:
        if kw.arg is None:
            continue
        kwargs[kw.arg] = _eval_node(kw.value, context)
    if isinstance(func, ast.Attribute):
        obj = _eval_node(func.value, context)
        name = func.attr
        if name not in _SAFE_METHODS:
            raise SafeEvalError(f"不允许调用方法: {name}")
        return getattr(obj, name)(*args, **kwargs)
    if isinstance(func, ast.Name):
        name = func.id
        if name not in _SAFE_FUNCS:
            raise SafeEvalError(f"不允许调用函数: {name}")
        return _SAFE_FUNCS[name](*args, **kwargs)
    raise SafeEvalError("不支持的调用")

def _eval_node(node, context):
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.List):
        return [_eval_node(e, context) for e in node.elts]
    elif isinstance(node, ast.Tuple):
        return tuple(_eval_node(e, context) for e in node.elts)
    elif isinstance(node, ast.Set):
        return {_eval_node(e, context) for e in node.elts}
    elif isinstance(node, ast.Dict):
        keys = [_eval_node(k, context) for k in node.keys]
        values = [_eval_node(v, context) for v in node.values]
        return dict(zip(keys, values))
    elif isinstance(node, ast.Name):
        if node.id in context:
            return context[node.id]
        raise SafeEvalError(f"未定义的变量: {node.id}")
    elif isinstance(node, ast.Attribute):
        obj = _eval_node(node.value, context)
        if node.attr.startswith('_'):
            raise SafeEvalError(f"不允许访问私有属性: {node.attr}")
        return getattr(obj, node.attr)
    elif isinstance(node, ast.Subscript):
        obj = _eval_node(node.value, context)
        sl = node.slice
        if isinstance(sl, ast.Index):      # Python3.8 兼容
            sl = sl.value
        if isinstance(sl, ast.Slice):
            lower = _eval_node(sl.lower, context) if sl.lower else None
            upper = _eval_node(sl.upper, context) if sl.upper else None
            step = _eval_node(sl.step, context) if sl.step else None
            return obj[slice(lower, upper, step)]
        return obj[_eval_node(sl, context)]
    elif isinstance(node, ast.Call):
        return _eval_call(node, context)
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