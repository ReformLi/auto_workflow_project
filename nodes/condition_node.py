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
from utils.safe_eval import safe_eval
import logging

# 常用比较模板：(按钮文字, 填充的表达式)
_TEMPLATES = [
    ("大于", 'input > 5'),
    ("小于", 'input < 5'),
    ("等于", 'input == 5'),
    ("包含", 'input.startswith("")'),
]

class IfElseNode(WorkflowNode):
    __identifier__ = 'workflow'
    NODE_NAME = '条件判断'
    NODE_CATEGORY = '条件判断'

    def __init__(self):
        super().__init__()
        self.add_input('input')
        self.add_output('true')
        self.add_output('false')
        self.set_name('条件判断')
        self.add_multiline_input('expression', '条件表达式', 'True',
                                 tooltip='变量 input 为输入值；可引用 context["键"]\n求值为真走 true，为假走 false。',
                                 tab='表达式')
        # 属性页追加比较模板（在对话框中渲染按钮）
        for d in self._prop_defs:
            if d['name'] == 'expression':
                d['templates'] = _TEMPLATES
                break
        self.refresh_summary()

    def _summary_text(self) -> str:
        """节点体上显示截断的条件表达式摘要。"""
        expr = (self.get_property('expression') or '').strip() or 'True'
        expr = ' '.join(expr.split())            # 压缩空白
        return expr[:18] + ('…' if len(expr) > 18 else '')

    def set_property(self, name, value, push_undo=True):
        super().set_property(name, value, push_undo)
        if name == 'expression':
            self.refresh_summary()

    def execute(self, inputs):
        expr = self.get_property('expression') or 'True'
        # 上下文：input 为输入端口值；context 暴露上游全部输出数据
        context = {'context': inputs}
        if 'input' in inputs:
            context['input'] = inputs['input']
        try:
            result = safe_eval(expr, context)
        except Exception as e:
            logging.getLogger(__name__).error(f"条件表达式求值错误: {e}")
            result = False
        result = bool(result)
        return {'result': result}, ('true' if result else 'false')