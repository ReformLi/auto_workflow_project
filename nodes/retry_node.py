# -*- coding: utf-8 -*-
"""
retry_node.py
功能描述: 重试执行节点——把"失败后重试"这一高频模式内建为单个节点，替代
         手工搭建的 循环判断+循环入口 回路。
典型连接:
    重试执行.body → 操作A → 操作B
    操作A/B 的 fail 出口 → 重试执行.retry（失败回流）
    重试执行.用尽 → 重试次数用尽后的补救流程（可不连）
行为:
    - 首次触发（in）→ 进入 body，开始第 1 次尝试
    - 尝试链中任一节点执行失败并回流到 retry → 间隔等待后重新触发 body
    - 重试次数用尽 → 触发「用尽」出口（未连接则结束流程）
    - 尝试链全部成功 → 正常沿末尾节点继续向下，不经过本节点
"""
import time

from nodes.base_node import WorkflowNode


def _to_int(v, default):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _to_float(v, default):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


class RetryNode(WorkflowNode):
    __identifier__ = 'workflow'
    NODE_NAME = '重试执行'
    NODE_ICON = 'fa5s.redo'
    NODE_CATEGORY = '容错'

    def __init__(self):
        super().__init__()
        self.add_input('in')                          # 首次进入
        self.add_input('retry', multi_input=True)     # 失败回流（连接尝试链的 fail 出口）
        self.add_output('body')                       # 执行体入口
        self.add_output('用尽')                        # 重试次数用尽出口

        self.add_text_input('max_retries', '重试次数', '3',
                            tooltip='失败后额外重试的次数（不含首次尝试）。0 表示不重试。')
        self.add_text_input('interval', '重试间隔(秒)', '1',
                            tooltip='两次尝试之间的等待时间，支持小数。')

        self._retries_used = 0    # 运行时状态，不持久化
        self.refresh_summary()

    def _summary_text(self) -> str:
        n = _to_int(self.get_property('max_retries'), 3)
        sec = _to_float(self.get_property('interval'), 1.0)
        return f"失败重试 {n} 次 · 间隔 {sec:g}s"

    def reset(self):
        super().reset()
        self._retries_used = 0

    def execute(self, inputs):
        trigger = inputs.get('__trigger__')
        if trigger != 'retry':
            # 首次进入：清零计数并开始第 1 次尝试
            self._retries_used = 0
            return {'body': True}, 'body'

        max_retries = max(0, _to_int(self.get_property('max_retries'), 3))
        if self._retries_used >= max_retries:
            return {'用尽': True}, '用尽'
        self._retries_used += 1
        interval = max(0.0, _to_float(self.get_property('interval'), 1.0))
        if interval > 0:
            time.sleep(interval)
        return {'body': True}, 'body'
