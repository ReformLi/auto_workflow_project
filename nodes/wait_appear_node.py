# -*- coding: utf-8 -*-
"""
wait_appear_node.py
功能描述: 等待出现节点——轮询直到目标出现或超时，替代"固定等待 + 碰运气"。
- 等待图片（WaitImageNode）：继承查找图片节点，复用模板配置与属性编辑器
  （ImageNodeEditor），按阈值反复匹配直到命中；命中后照常输出 坐标/中心坐标/匹配度。
- 等待窗口（WaitWindowNode）：按标题/类名/进程名反复查找窗口；出现后输出
  窗口对象/窗口句柄，可直接供激活窗口/鼠标点击等下游节点使用。
公共行为: 出现 → 走「出现」出口；超时 → 走「超时」出口（可接补救流程）。
执行期间响应工具栏的 终止/暂停。
"""
import time

from nodes._control_common import StopFlag, WorkflowInterrupted
from nodes.base_node import WorkflowNode
from nodes.image_nodes import FindImageNode
from nodes.window_nodes import _WindowSearchMixin, wm


def _to_float(v, default):
    try:
        return max(0.0, float(v))
    except (TypeError, ValueError):
        return default


class _WaitAppearMixin:
    """超时/轮询间隔属性 + 轮询骨架（非 WorkflowNode，不被自动注册）。"""

    def _add_wait_appear_properties(self):
        self.add_text_input('timeout', '超时(秒)', '10',
                            tooltip='最长相 wait 时间，超时走「超时」出口')
        self.add_text_input('interval', '轮询间隔(秒)', '0.5',
                            tooltip='两次尝试之间的间隔，支持小数')

    def _wait_params(self):
        timeout = _to_float(self.get_property('timeout'), 10.0)
        interval = _to_float(self.get_property('interval'), 0.5)
        return timeout, max(0.05, interval)

    def _poll(self, try_once, inputs):
        """轮询骨架：try_once(inputs) 命中时返回输出 dict，未命中抛 RuntimeError。"""
        timeout, interval = self._wait_params()
        with StopFlag() as stop:
            deadline = time.monotonic() + timeout
            while True:
                stop.check()
                try:
                    return try_once(inputs)
                except WorkflowInterrupted:
                    raise
                except RuntimeError:
                    pass                      # 未命中 → 继续轮询
                if time.monotonic() >= deadline:
                    return None               # 超时
                stop.wait(interval)


class WaitImageNode(_WaitAppearMixin, FindImageNode):
    """等待图片：反复执行模板匹配/颜色定位直到命中或超时。"""
    __identifier__ = 'workflow'
    NODE_NAME = '等待图片'
    NODE_ICON = 'fa5s.hourglass-half'
    NODE_CATEGORY = '等待'

    def __init__(self):
        super().__init__()
        self.add_output('出现')
        self.add_output('超时')
        self._add_wait_appear_properties()
        self.refresh_summary()

    def _summary_text(self) -> str:
        timeout, _ = self._wait_params()
        mode = self.get_property('mode') or '模板匹配'
        return f"等待{mode} ≤{timeout:g}s"

    def set_property(self, name, value, push_undo=True):
        super().set_property(name, value, push_undo)
        if name in ('timeout', 'interval'):
            self.refresh_summary()

    def execute(self, inputs):
        # 配置错误（无模板/无采集点）应立即报错，而不是空轮询到超时
        if (self.get_property('mode') or '模板匹配') == '模板匹配':
            if self.get_template() is None:
                raise RuntimeError('未设置模板图片：请粘贴 / 选择图片，或提供内嵌模板')
        else:
            if len(self.get_colored_points()) < 1:
                raise RuntimeError('颜色定位需要至少 1 个采集点，请在属性中执行「开始采集」')

        result = self._poll(super().execute, inputs)
        if result is None:
            return {'超时': True}, '超时'
        outputs, _ = result
        outputs['出现'] = True
        return outputs, '出现'


class WaitWindowNode(_WaitAppearMixin, _WindowSearchMixin, WorkflowNode):
    """等待窗口：反复查找窗口直到出现或超时。"""
    __identifier__ = 'workflow'
    NODE_NAME = '等待窗口'
    NODE_ICON = 'fa5s.window-maximize'
    NODE_CATEGORY = '等待'

    def __init__(self):
        super().__init__()
        self.add_input('in')
        self.add_output('出现')
        self.add_output('超时')
        self.add_output('窗口对象')
        self.add_output('窗口句柄')
        self._add_search_properties(title_label='窗口标题')
        self._add_wait_appear_properties()
        self.refresh_summary()

    def _summary_text(self) -> str:
        title, mode, cls, proc = self._read_search_conditions()
        desc = title or cls or proc or '未设置条件'
        timeout, _ = self._wait_params()
        return f"等待窗口「{desc[:12]}」 ≤{timeout:g}s"

    def execute(self, inputs):
        title, match_mode, class_name, process_name = self._read_search_conditions()
        if not any([title, class_name, process_name]):
            raise RuntimeError('请至少填写窗口标题 / 类名 / 进程名之一（可用捕获按钮采集）')

        def try_once(_inputs):
            window = wm.find_window(title=title or None, match_mode=match_mode,
                                    class_name=class_name or None,
                                    process_name=process_name or None)
            if not window:
                raise RuntimeError('窗口未出现')
            return {'出现': True, '窗口对象': window,
                    '窗口句柄': int(window.NativeWindowHandle)}

        result = self._poll(try_once, inputs)
        if result is None:
            return {'超时': True}, '超时'
        return result, '出现'
