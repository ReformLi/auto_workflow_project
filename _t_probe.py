# -*- coding: utf-8 -*-
"""双击路径探针：真实模拟画布双击，检查改名编辑器（场景内 QTextEdit 交互）是否触发"""
import os, sys
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QPointF, QTimer
from PyQt5.QtTest import QTest

app = QApplication(sys.argv)

from ui.main_window import WorkflowMainWindow
win = WorkflowMainWindow()
win.show()
app.processEvents()

g = win.core_manager.graph_manager.node_graph
node = g.create_node('workflow.DelayNode', name='d')
node.set_pos(200, 200)
app.processEvents()

view = win.core_manager.get_view()
# 节点标题中心（旧 bug 高发位置）与节点中心，各测一次
targets = {
    '节点中心': node.view.sceneBoundingRect().center(),
    '标题左上': node.view.sceneBoundingRect().topLeft() + QPointF(30, 8),
}

for label, scene_pt in targets.items():
    vpt = view.mapFromScene(scene_pt)
    # 完整双击序列：press → release → dblclick
    QTest.mousePress(view.viewport(), Qt.LeftButton, Qt.NoModifier, vpt)
    QTest.mouseRelease(view.viewport(), Qt.LeftButton, Qt.NoModifier, vpt)
    QTest.mouseDClick(view.viewport(), Qt.LeftButton, Qt.NoModifier, vpt)
    app.processEvents()

    # 检查1：场景内是否有获得焦点/可编辑的文本项（NGQ 改名编辑器特征）
    focus_item = view.scene().focusItem()
    editing = focus_item is not None and \
        (focus_item.textInteractionFlags() & Qt.TextEditable)
    # 检查2：多余可见顶层窗口
    stray = [w for w in QApplication.topLevelWidgets()
             if w.isVisible() and w is not win]
    # 检查3：面板是否打开
    panel_open = win.properties_panel_host.isVisible()
    print(f'[{label}] 改名编辑器触发={editing}  多余顶层={len(stray)}  面板打开={panel_open}')
    if editing:
        print('   !!! 命中改名编辑器:', type(focus_item).__name__,
              'flags=', focus_item.textInteractionFlags())
    # 还原：清焦点
    if editing:
        view.scene().clearFocus()
    app.processEvents()

print('done')
