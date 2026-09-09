# -*- coding: utf-8 -*-
"""
subflow_node.py
功能描述: 子工作流节点——把另一个 .awflow / .json 工作流文件作为一个节点嵌入执行，
         实现"搭一次、处处用"的流程复用。
行为:
- 执行时加载子工作流文件，从其「开始」节点同步执行到结束（独立运行，不共享画布）。
- 子工作流内部节点抛异常且未接 fail 分支 → 本节点视为执行失败（走本节点 fail 出口，
  未连接则终止主工作流）。
- 子工作流内部支持条件/循环/重试等全部控制流；嵌套调用最多 8 层（防自调用死循环）。
- 执行期间响应工具栏的 终止/暂停。
属性页使用自定义编辑器（SubflowNodeEditor，见 ui/node_subflow_widget.py）：
路径输入 + 浏览按钮 + 文件状态检查。
"""
import os

from nodes._control_common import StopFlag, load_graph_dict, run_subgraph_from_dict
from nodes.base_node import WorkflowNode


class SubflowNode(WorkflowNode):
    __identifier__ = 'workflow'
    NODE_NAME = '子工作流'
    NODE_ICON = 'fa5s.project-diagram'
    NODE_CATEGORY = '子流程'
    SUBFLOW_NODE = True  # 使用自定义属性编辑器（SubflowNodeEditor）接管属性页

    def __init__(self):
        super().__init__()
        self.add_input('in')
        self.add_output('out')
        self.add_fail_output()   # 子流程内部失败时的出口

        self._register_storage('workflow_path', '')
        self.refresh_summary()

    def _register_storage(self, name, value):
        """注册为可序列化的模型属性，由 SubflowNodeEditor 接管展示。"""
        self.create_property(name, value=value)

    def _summary_text(self) -> str:
        path = (self.get_property('workflow_path') or '').strip()
        if not path:
            return '未选择子工作流'
        name = os.path.basename(path)
        return f"{name} ✓" if os.path.isfile(path) else f"{name} ✗ 文件不存在"

    def execute(self, inputs):
        path = (self.get_property('workflow_path') or '').strip()
        graph_dict = load_graph_dict(path)   # 路径为空 / 文件缺失 → RuntimeError
        with StopFlag() as stop:
            outputs = run_subgraph_from_dict(graph_dict, stop)
        return dict(outputs or {}), 'out'
