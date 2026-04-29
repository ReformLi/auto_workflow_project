# -*- coding: utf-8 -*-
"""
loop_node.py
作者: reformLi
创建日期: 2026/4/22
最后修改: 2026/4/22
版本: 1.0.0

功能描述: 实现简单循环
"""
from nodes.base_node import WorkflowNode

class WhileLoopNode(WorkflowNode):
    __identifier__ = 'workflow'
    NODE_NAME = '循环判断'

    def __init__(self):
        super().__init__()
        self.add_input('in')
        # 结束循环
        self.add_output('end')
        # 循环
        self.add_output('cycle')
        self.set_name('循环')
        self.add_text_input('iterations', '剩余循环次数', '3')
        self.set_property('iterations', '3')

    def execute(self, inputs):
        # 获取当前剩余次数
        remaining_str = self.get_property('iterations')
        try:
            remaining = int(remaining_str) if remaining_str else 0
        except:
            remaining = 0

        if remaining <= 0:
            print("循环剩余次数已为0，跳过循环！")
            return {'end': True}, 'end'

        # 内循环执行
        # for i in range(remaining, 0, -1):
        #     print(f"循环第 {remaining - i + 1} 次，剩余 {i-1} 次")
        #     # 更新属性（减一）
        #     new_remaining = i - 1
        #     self.set_property('iterations', str(new_remaining))
        #     # 可选：触发属性面板刷新（NodeGraphQt 会自动处理信号）
        #     # 可以添加短暂延时以便观察
        #     time.sleep(0.1)  # 模拟循环体执行
        # return {'out': True}, 'out'

        # 外循环执行
        print(f"循环剩余 {remaining} 次数")
        # 更新属性（减一）
        new_remaining = remaining - 1
        self.set_property('iterations', str(new_remaining))
        return {'cycle': True}, 'cycle'

class DoLoopNode(WorkflowNode):
    __identifier__ = 'workflow'
    NODE_NAME = '循环'

    def __init__(self):
        super().__init__()
        self.add_input('in')
        self.add_input('cycle')
        self.add_output('out')
        self.set_name('循环承接')

    def execute(self, inputs):
        return {'out': True}, 'out'