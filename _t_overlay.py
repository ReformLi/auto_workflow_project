# -*- coding: utf-8 -*-
"""属性悬浮层冒烟测试（离屏）：
1. 悬浮层不参与分割器（水平分割器 2 格）
2. 显示/隐藏属性面板前后，画布与日志的分割器尺寸完全不变
3. 悬浮层几何贴合画布右缘
4. 表单/编辑器都在滚动容器内
"""
import os, sys
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)

from ui.main_window import WorkflowMainWindow, PROPERTIES_WIDTH

win = WorkflowMainWindow()
win.show()
app.processEvents()

hs, vs = win.horizontal_splitter, win.vertical_splitter
assert hs.count() == 2, f'水平分割器应为 2 格，实际 {hs.count()}'
print('1. 悬浮层不参与分割器 OK（水平分割器 2 格）')

before_h = list(hs.sizes())
before_v = list(vs.sizes())
# 布局彻底稳定（状态栏等初始化收尾可能有 1-2px 漂移）
for _ in range(20):
    app.processEvents()
    if list(hs.sizes()) == before_h and list(vs.sizes()) == before_v:
        break
    before_h, before_v = list(hs.sizes()), list(vs.sizes())
gwidget = win.core_manager.get_widget()

# 显示属性面板
node = win.core_manager.graph_manager.node_graph.create_node(
    'workflow.DelayNode', name='d')
win.show_node_properties(node, raise_panel=False)
app.processEvents()
assert win.properties_panel_host.isVisible(), '面板应可见'
after_show_h = list(hs.sizes())
after_show_v = list(vs.sizes())
assert before_h == after_show_h, f'显示面板后水平分割器变动: {before_h} -> {after_show_h}'
assert before_v == after_show_v, f'显示面板后垂直分割器变动: {before_v} -> {after_show_v}'
print('2a. 显示面板：分割器尺寸零变动 OK')

# 几何贴合画布右缘
gp = gwidget.mapTo(win, gwidget.rect().topLeft())
g = win.properties_panel_host.geometry()
assert abs((gp.x() + gwidget.width() - PROPERTIES_WIDTH - 2) - g.x()) <= 1, \
    f'面板未贴画布右缘: {g.x()} vs {gp.x() + gwidget.width() - PROPERTIES_WIDTH - 2}'
assert abs(g.width() - PROPERTIES_WIDTH) <= 1
assert abs((gp.y() + gwidget.height()) - (g.y() + g.height())) <= 2
print('3. 悬浮层几何贴合画布右缘 OK')

# 隐藏面板
win.hide_node_properties()
app.processEvents()
assert not win.properties_panel_host.isVisible()
assert list(hs.sizes()) == before_h and list(vs.sizes()) == before_v, '隐藏后面板分割器尺寸应复原'
print('2b. 隐藏面板：分割器尺寸零变动 OK')

# 滚动容器：表单/编辑器都在 QScrollArea 内
win.show_node_properties(node)
scrolls = win.properties_panel_host.findChildren(__import__('PyQt5.QtWidgets', fromlist=['QScrollArea']).QScrollArea)
assert scrolls, '属性内容应在 QScrollArea 内'
panel = win.core_manager.graph_manager.node_graph.create_node('workflow.FindImageNode', name='img')
win.show_node_properties(panel)
app.processEvents()
from PyQt5.QtWidgets import QScrollArea
scrolls = win.properties_panel_host.findChildren(QScrollArea)
assert scrolls, '编辑器节点内容应在 QScrollArea 内'
print('4. 表单/编辑器统一上下滚动容器 OK')

# ---- 5. 切换节点瞬间无多余顶层弹框（deleteLater 未执行时检测） ----
from PyQt5.QtCore import Qt as QtConst
kb2 = win.core_manager.graph_manager.node_graph.create_node('workflow.HotkeyNode', name='kb2')
win.show_node_properties(panel)      # 图片节点（含编辑器）
win.show_node_properties(node)       # 切到通用表单节点
win.show_node_properties(kb2)        # 再切一次
# 不 processEvents：deleteLater 尚未执行，若旧控件闪现顶层窗口会在此暴露
stray = [w for w in QApplication.topLevelWidgets()
         if w.isVisible() and w is not win]
assert not stray, f'切换节点时出现多余可见顶层窗口: {stray}'
app.processEvents()
stray = [w for w in QApplication.topLevelWidgets()
         if w.isVisible() and w is not win]
assert not stray, f'事件处理后仍有多余可见顶层窗口: {stray}'
print('5. 切换节点无瞬间弹框（可见顶层窗口扫描） OK')

print('\nALL PASS')
