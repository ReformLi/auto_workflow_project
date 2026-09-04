# -*- coding: utf-8 -*-
"""
loop_node.py
作者: reformLi
创建日期: 2026/4/22
最后修改: 2026/9/4
版本: 1.2.0

功能描述: 实现循环。
- 循环判断节点：决定继续循环（true）还是退出（false）。支持两种模式：
  计数器模式（默认，按循环次数）与条件值模式（依据 input 求表达式，类似条件判断）。
- 循环入口节点：过渡节点，first 进入时激活 body 进入循环体；循环体末尾触发 next
  时回流重新触发循环判断节点，形成回路。
"""
from nodes.base_node import WorkflowNode
from utils.safe_eval import safe_eval

# 比较模板（条件值模式复用）
_LOOP_TEMPLATES = [
    ("大于", 'input > 5'),
    ("小于", 'input < 5'),
    ("等于", 'input == 5'),
    ("包含", 'input.startswith("")'),
]

_MODES = ["计数器模式", "条件值模式"]


class WhileLoopNode(WorkflowNode):
    __identifier__ = 'workflow'
    NODE_NAME = '循环判断'
    NODE_CATEGORY = '循环'
    NODE_ICON = 'fa5s.sync-alt'

    def __init__(self):
        super().__init__()
        self.add_input('in')       # 首次触发/正常进入
        self.add_output('true')    # 继续循环（接循环入口.enter）
        self.add_output('false')   # 退出循环（接循环体之后的节点）
        self.set_name('循环判断')

        self._loop_remaining = None  # 运行时剩余次数，不做持久化

        self.add_combo_menu('mode', '循环模式', _MODES)
        self.add_text_input('count', '循环次数', '3',
                            tooltip='循环体需执行的次数（正整数）。')
        self.add_multiline_input('expression', '条件表达式', 'True',
                                 tooltip='变量 input 为进入值；可引用 context["键"]\n求值为真继续循环，为假退出。')
        # 条件值模式下显示比较模板
        for d in self._prop_defs:
            if d['name'] == 'expression':
                d['templates'] = _LOOP_TEMPLATES
                d['vis_when'] = ('mode', '条件值模式')
            elif d['name'] == 'count':
                d['vis_when'] = ('mode', '计数器模式')
        self.refresh_summary()
        self.set_property('mode', self.get_property('mode') or _MODES[0])

    def _summary_text(self) -> str:
        mode = self.get_property('mode') or _MODES[0]
        if mode == '条件值模式':
            expr = (self.get_property('expression') or '').strip() or 'True'
            expr = ' '.join(expr.split())
            return '条件:' + expr[:14] + ('…' if len(expr) > 14 else '')
        count = (self.get_property('count') or '').strip() or '3'
        return f"循环 {count} 次"

    def set_property(self, name, value, push_undo=True):
        super().set_property(name, value, push_undo)
        if name in ('mode', 'count', 'expression'):
            self.refresh_summary()

    def reset(self):
        super().reset()
        self._loop_remaining = None

    def execute(self, inputs):
        mode = self.get_property('mode') or _MODES[0]
        if mode == '条件值模式':
            expr = self.get_property('expression') or 'True'
            context = {'context': inputs, 'input': inputs.get('in')}
            try:
                result = bool(safe_eval(expr, context))
            except Exception:
                result = False
            return {'true': result, 'false': not result}, ('true' if result else 'false')

        # 计数器模式：命中次数清零则退出
        if self._loop_remaining is None:
            try:
                self._loop_remaining = int(self.get_property('count') or 0)
            except (TypeError, ValueError):
                self._loop_remaining = 0
        if self._loop_remaining > 0:
            self._loop_remaining -= 1
            return {'true': True}, 'true'
        return {'false': True}, 'false'


class LoopEntryNode(WorkflowNode):
    """循环入口（过渡节点）：第一次进入(enter)激活 body 进入循环体；
    循环体末尾触发 next 时回流重新触发循环判断节点。"""
    __identifier__ = 'workflow'
    NODE_NAME = '循环入口'
    NODE_CATEGORY = '循环'
    NODE_ICON = 'fa5s.recycle'
    is_loop_entry = True

    def __init__(self):
        super().__init__()
        self.add_input('enter')   # 首次进入（接循环判断 true 输出）
        self.add_input('next')    # 循环体末尾回流
        self.add_output('body')   # 接循环体第一个节点
        self.set_name('循环入口')
        # 在体内提示，便于识别特殊节点
        self._decision_node = None
        self.refresh_summary()

    def _summary_text(self) -> str:
        return '循环入口'

    def get_decision_node(self):
        """返回本循环对应的循环判断节点（通过 enter 端口上游解析）。"""
        if not self._decision_node:
            for p in self.input_ports():
                if p.name() == 'enter':
                    conns = p.connected_ports()
                    if conns:
                        self._decision_node = conns[0].node()
                    break
        return self._decision_node

    def execute(self, inputs):
        return {'body': True}, 'body'