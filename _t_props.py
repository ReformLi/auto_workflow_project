# -*- coding: utf-8 -*-
"""属性面板修复冒烟测试（离屏）：
1. 通用表单节点（键盘）渲染全部属性
2. 编辑器节点（查找图片）不再出现游离的 _custom 表单行
3. _node_at 命中检测：节点中心命中、空白处不命中
4. 选中/清空联动（show_node_properties_if_visible / hide_node_properties）
"""
import os, sys
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QRectF

app = QApplication(sys.argv)

from core.manager import NodeGraphManager
from ui.node_properties_panel import NodePropertiesPanel
from ui.node_graph_panel import NodeGraphPanel

mgr = __import__('core.manager', fromlist=['CoreManager']).CoreManager()
g = mgr.graph_manager.node_graph

kb = g.create_node('workflow.HotkeyNode', name='kb')
img = g.create_node('workflow.FindImageNode', name='img')
st = g.create_node('workflow.StartNode', name='start')
assert kb and img and st, '节点创建失败'
kb.set_pos(0, 0); img.set_pos(400, 400); st.set_pos(800, 0)

# ---- 1. 通用表单节点：全部属性渲染 ----
panel = NodePropertiesPanel()
panel.show_node(kb)
names = set(panel._widgets.keys())
expect = {'keys', 'quick_key', 'exec_mode', 'repeat', 'interval'}
assert expect <= names, f'键盘节点属性缺失: {expect - names}'
print('1. 键盘节点表单属性齐全 OK:', sorted(names))

# ---- 2. 编辑器节点：无 _custom 游离控件 ----
panel.show_node(img)
assert '_custom' not in panel._widgets, '_custom 占位行不应渲染'
assert panel._editor is not None, '查找图片节点应有专用编辑器'
print('2. 查找图片节点走专用编辑器，无游离表单行 OK')

# ---- 2b. 等待图片：编辑器 + 自有属性（超时/轮询间隔）共存 ----
wi = g.create_node('workflow.WaitImageNode', name='wi')
wi.set_pos(400, 800)
panel.show_node(wi)
assert panel._editor is not None, '等待图片应有专用编辑器'
assert {'timeout', 'interval'} <= set(panel._widgets), \
    f'等待图片自有属性缺失: {set(panel._widgets)}'
print('2b. 等待图片节点编辑器与表单共存 OK')

# ---- 3. _node_at 命中检测 ----
ngp = NodeGraphPanel(core_manager=mgr, main_window=None)
view = mgr.get_view()
center = img.view.sceneBoundingRect().center()
hit = ngp._node_at(center)
assert hit is img, f'节点中心应命中 img，实际: {hit}'
far = center + __import__('PyQt5.QtCore', fromlist=['QPointF']).QPointF(500, 500)
assert ngp._node_at(far) is None, '空白处不应命中'
# 标题左上角区域（旧实现偏左上矩形漏检的场景）
tr = img.view.sceneBoundingRect().topLeft() + \
    __import__('PyQt5.QtCore', fromlist=['QPointF']).QPointF(8, 6)
hit2 = ngp._node_at(tr)
assert hit2 is img, f'节点左上角应命中 img，实际: {hit2}'
print('3. _node_at 命中检测 OK（中心/左上角命中，空白不命中）')

# ---- 4. 模拟主窗口命令 ----
class FakeMW:
    def __init__(self):
        self.visible = False
        self.shown = []
    def show_node_properties(self, node, raise_panel=False):
        self.visible = True; self.shown.append(node)
    def show_node_properties_if_visible(self, node):
        if self.visible: self.shown.append(node)
    def hide_node_properties(self):
        self.visible = False

mw = FakeMW()
ngp._main_window = mw
# 单击选中：面板隐藏 → 不显示
ngp._on_node_selected(kb)
assert not mw.visible and not mw.shown, '面板隐藏时单击选中不应唤醒'
# 双击（有属性）→ 唤醒
ngp._open_properties(kb)
assert mw.visible
# 单击其他节点：面板可见 → 切换内容
n_before = len(mw.shown)
ngp._on_node_selected(img)
assert len(mw.shown) == n_before + 1 and mw.shown[-1] is img
# 空白点击（选中清空）→ 隐藏
for n in g.all_nodes():
    n.set_selected(False)
ngp._on_node_selection_changed([], [])
assert not mw.visible
print('4. 显隐联动 OK（隐藏不唤醒/双击唤醒/可见切换/空白隐藏）')

print('\nALL PASS')
