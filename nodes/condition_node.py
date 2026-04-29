# -*- coding: utf-8 -*-
"""
condition_node.py
作者: reformLi
创建日期: 2026/4/22
最后修改: 2026/4/22
版本: 1.0.0

功能描述: 根据输入条件决定输出到 True 分支还是 False 分支
"""
from nodes.base_node import WorkflowNode
from utils.safe_eval import safe_eval, SafeEvalError

class IfElseNode(WorkflowNode):
    __identifier__ = 'workflow'
    NODE_NAME = '条件判断'

    def __init__(self):
        super().__init__()
        self.add_input('condition')
        self.add_output('true')
        self.add_output('false')
        self.set_name('条件判断')
        self.add_text_input('expression', '条件表达式', 'True')
        self.set_property('expression', 'True')

    # def execute(self, inputs):
    #     # 简单解析表达式（实际可用 eval，但注意安全）
    #     expr = self.get_property('expression') or 'True'
    #     try:
    #         condition = eval(expr)
    #     except:
    #         condition = True
    #     if condition:
    #         return {'result': True}, 'true'
    #     else:
    #         return {'result': False}, 'false'

    def execute(self, inputs):
        expr = self.get_property('expression') or 'True'
        # 构建上下文：将输入端口 'condition' 的值作为变量 'cond'
        context = {}
        if 'condition' in inputs:
            context['cond'] = inputs['condition']
        # 也可以将所有输入作为变量，但为避免冲突，只放 cond
        try:
            result = safe_eval(expr, context)
        except SafeEvalError as e:
            print(f"表达式求值错误: {e}")
            result = False
        if result:
            return {'result': True}, 'true'
        else:
            return {'result': False}, 'false'