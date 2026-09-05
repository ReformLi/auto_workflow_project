# -*- coding: utf-8 -*-
"""
base_node.py
作者: reformLi
创建日期: 2026/3/25
最后修改: 2026/3/25
版本: 1.0.0

功能描述: 基础节点类 -工作流节点基类
"""
import weakref
from abc import ABC, abstractmethod

from NodeGraphQt import BaseNode
from NodeGraphQt.constants import NodePropWidgetEnum
from PyQt5 import QtWidgets, QtGui

from ui import icons, tokens


class WorkflowNode(BaseNode, ABC):
    """
    工作流节点基类，扩展执行功能 + 线程安全的状态显示
    """
    __identifier__ = 'workflow'  # 默认标识，子类可覆盖
    NODE_NAME = 'WorkflowNode'

    # 视觉语义（子类声明）：分类键为中文，取值见 ui/tokens.NODE_CATEGORIES
    NODE_CATEGORY = None      # None → 回落 tokens 兜底样式
    NODE_ICON = None          # None 时使用分类默认图标

    # 全局弱引用字典：{node_id: node_instance}
    _instances = weakref.WeakValueDictionary()

    def __init__(self):
        super(WorkflowNode, self).__init__()
        # 原有初始化
        self._executed = False
        self._output_data = None
        self.set_disabled(False)

        # 分类色 + 分类图标（放在 __init__ 中，反序列化加载旧工作流同样生效）
        self._apply_visual_style()

        # ========== 新增：状态显示相关 ==========
        # 生成唯一标识（使用Python对象id，也可用uuid）
        self._node_id = str(id(self))
        WorkflowNode._instances[self._node_id] = self

        # 创建用于显示状态的小型文本组件（作为节点的子项，自动跟随移动）
        font = QtGui.QFont()
        font.setPointSize(6)
        self.status_text = QtWidgets.QGraphicsTextItem(self.view) # type: ignore  #在代码行添加type: ignore注释，仅屏蔽当前行的警告：
        self.status_text.setFont(font)
        self.status_text.document().setDefaultStyleSheet(
            "div { margin:0; padding:0; } br { line-height: 0.6; }"
        )
        self.status_text.setDefaultTextColor(QtGui.QColor(tokens.DARK['text']))
        self.status_text.setVisible(False)

        # 属性定义（供节点属性页渲染；不入节点体，节点图只显示节点本身）
        self._prop_defs = []

        # 节点摘要文本（如条件表达式摘要），放在节点体下方，可选
        sum_font = QtGui.QFont()
        sum_font.setPointSize(7)
        self.summary_text = QtWidgets.QGraphicsTextItem(self.view)  # type: ignore
        self.summary_text.setFont(sum_font)
        self.summary_text.document().setDefaultStyleSheet("div { margin:0; padding:0; }")
        self.summary_text.setDefaultTextColor(QtGui.QColor(tokens.DARK['text_dim']))
        self.summary_text.setVisible(False)

    def set_summary(self, text):
        """在节点体下方显示摘要文本（空串则隐藏）。"""
        if not self.view:
            return
        self.summary_text.setPlainText(text)
        self.summary_text.setVisible(bool(text))
        if not text:
            return
        node_rect = self.view.boundingRect()
        text_rect = self.summary_text.boundingRect()
        x = 6
        y = node_rect.height() - text_rect.height() - 6
        self.summary_text.setPos(x, y)
        self.summary_text.update()

    def refresh_summary(self):
        """子类可覆盖 _summary_text() 返回摘要；属性变化时调用以刷新。"""
        self.set_summary(self._summary_text())

    def _summary_text(self) -> str:
        """节点摘要字符串，默认空。"""
        return ''

    def _apply_visual_style(self):
        """按 NODE_CATEGORY / NODE_ICON 应用节点头部色与图标"""
        try:
            color = tokens.category_color(self.NODE_CATEGORY)
            self.set_color(*tokens.rgb(color))

            icon_name = self.NODE_ICON or tokens.category_icon(self.NODE_CATEGORY)
            icon_path = icons.node_icon_path(icon_name, tokens.DARK['bg_canvas'])
            if icon_path:
                self.set_icon(icon_path)
        except Exception:
            # 视觉样式失败不能影响节点可用性
            pass

    def get_node_id(self) -> str:
        """返回节点的唯一标识（供工作流线程使用）"""
        return self._node_id

    def update_status(self, html: str, is_error: bool = False):
        """
        在主线程中安全更新节点状态UI。
        该方法应由 WorkflowExecutor 在主线程中调用。
        """
        if not self.view:  # 节点可能已被销毁
            return
        self.status_text.setHtml(html)
        self.status_text.setVisible(bool(html))
        color = QtGui.QColor(tokens.DARK['error'] if is_error else tokens.DARK['success'])
        self.status_text.setDefaultTextColor(color)

        # 重新计算位置（节点内部右上角，留4像素边距）
        node_rect = self.view.boundingRect()
        text_rect = self.status_text.boundingRect()
        x = node_rect.width() - text_rect.width() - 2
        y = -32
        self.status_text.setPos(x, y)
        self.update()

    @classmethod
    def get_node_by_id(cls, node_id: str):
        """通过节点ID安全获取节点实例（若节点已销毁则返回None）"""
        return cls._instances.get(node_id, None)

    # ========== 原有抽象方法 ==========
    def _run(self, context):
        """子类实现具体执行逻辑"""
        raise NotImplementedError

    def reset(self):
        """重置节点状态（用于多次执行）"""
        self._executed = False
        self._output_data = None

    @abstractmethod
    def execute(self, inputs: dict) -> (dict, str):
        """
        执行节点逻辑，返回输出数据和下一个要执行的端口名（默认为 None）
        返回格式: (outputs, next_port_name)
        """
        pass

    @classmethod
    def is_start_node(cls) -> bool:
        return False

    @classmethod
    def is_end_node(cls) -> bool:
        return False

    # ========== 属性定义（节点属性页用，不入节点体） ==========
    def add_text_input(self, name, label='', text='', placeholder_text='',
                       tooltip=None, tab=None):
        """注册一个文本属性到节点模型（不内嵌到节点体，仅在属性页展示）。"""
        self.create_property(
            name, value=text,
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            widget_tooltip=tooltip, tab=tab)
        self._prop_defs.append({
            'name': name, 'label': label or name, 'kind': 'text',
            'value': text, 'items': None, 'capture': False,
        })

    def add_multiline_input(self, name, label='', text='', tooltip=None, tab=None):
        """注册一个多行文本属性（表达式等），在属性页以多行编辑框展示。"""
        self.create_property(
            name, value=text,
            widget_type=NodePropWidgetEnum.QTEXT_EDIT.value,
            widget_tooltip=tooltip, tab=tab)
        self._prop_defs.append({
            'name': name, 'label': label or name, 'kind': 'text',
            'multiline': True, 'value': text,
            'items': None, 'capture': False,
        })

    def add_combo_menu(self, name, label='', items=None, tooltip=None, tab=None):
        """注册一个下拉选择属性到节点模型（不内嵌到节点体，仅在属性页展示）。"""
        items = items or []
        self.create_property(
            name, value=items[0] if items else None, items=items,
            widget_type=NodePropWidgetEnum.QCOMBO_BOX.value,
            widget_tooltip=tooltip, tab=tab)
        self._prop_defs.append({
            'name': name, 'label': label or name, 'kind': 'combo',
            'value': items[0] if items else None, 'items': items,
            'capture': False,
        })

    def add_bool_option(self, name, label='', default=False, tooltip=None, tab=None):
        """注册一个布尔（复选）属性：'1' 为开启，'0' 为关闭。"""
        val = '1' if default else '0'
        self.create_property(
            name, value=val,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            widget_tooltip=tooltip, tab=tab)
        self._prop_defs.append({
            'name': name, 'label': label or name, 'kind': 'check',
            'value': val, 'items': None, 'capture': False,
        })

    def mark_property_capture(self, name):
        """把指定属性标记为支持'捕获'（在属性页对应输入框旁渲染捕获按钮）。"""
        for d in self._prop_defs:
            if d['name'] == name:
                d['capture'] = True
                return

    def get_property_defs(self):
        """返回节点的声明式属性定义列表，供节点属性页渲染。"""
        # 同步模型中的最新值（属性可在外部被赋值）
        for d in self._prop_defs:
            val = self.get_property(d['name'])
            if val is not None:
                d['value'] = val
        defs = list(self._prop_defs)
        # 特殊节点（查找图片 / OCR 识别 等）使用自定义属性编辑器，
        # 属性不进入 _prop_defs，但必须保证有属性页（否则双击/右键不弹窗）。
        if not defs and (getattr(self, 'IMAGE_NODE', False)
                         or getattr(self, 'OCR_NODE', False)
                         or getattr(self, 'MOUSE_NODE', False)):
            defs.append({'name': '_custom', 'label': '属性', 'kind': 'text',
                         'value': '', 'items': None, 'capture': False})
        return defs

    # ---------------- 前置 / 后置等待（通用属性方法） ----------------
    def _add_wait_properties(self, include_pre=True, include_post=True):
        """注册前置(pre_wait) / 后置(post_wait) 等待属性（单位：秒，默认 0）。"""
        if include_pre:
            self.add_text_input('pre_wait', '前置等待(秒)', '0',
                                placeholder_text='执行前等待，0 表示不等待')
        if include_post:
            self.add_text_input('post_wait', '后置等待(秒)', '0',
                                placeholder_text='执行后等待，0 表示不等待')

    @staticmethod
    def _wait_seconds(wait_value):
        try:
            return max(0.0, float(wait_value or '0'))
        except (TypeError, ValueError):
            return 0.0

    def _apply_wait(self, inputs=None, wait_prop='pre_wait'):
        """按指定等待属性阻塞等待；wait_prop 为 'pre_wait' 或 'post_wait'。"""
        secs = self._wait_seconds(self.get_property(wait_prop)
                                  if hasattr(self, 'get_property') else None)
        if secs > 0:
            import time
            time.sleep(secs)