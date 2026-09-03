# -*- coding: utf-8 -*-
"""重构验证脚本：执行链路 + 按钮状态机（headless 离屏运行）"""
import os
import logging
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

logging.getLogger().setLevel(logging.INFO)

app = QApplication(sys.argv)
from ui.main_window import WorkflowMainWindow  # noqa: E402

w = WorkflowMainWindow()
g = w.core_manager.graph_manager.node_graph

# 搭 开始 → 等待(1s) → 结束 链
n1 = g.create_node('workflow.StartNode')
n2 = g.create_node('workflow.DelayNode')
n3 = g.create_node('workflow.EndNode')
n2.set_property('duration_sec', '1')
n1.output(0).connect_to(n2.input(0))
n2.output(0).connect_to(n3.input(0))

states = []
w.execution.update_execution_buttons = (lambda s: (states.append(s),
                                                    w.__class__.__mro__ and None) or None) if False else w.execution.update_execution_buttons

# 记录状态栏消息以跟踪按钮状态机
messages = []
orig = w.statusBar().showMessage
def trace(msg, *a):
    messages.append(msg)
    return orig(msg, *a)
w.statusBar().showMessage = trace

def check(name, cond):
    print(('PASS' if cond else 'FAIL'), name)
    if not cond:
        sys.exit(1)

check('验证通过', w.core_manager.validate_workflow()['success'])

# 执行工作流
w.execution.execute_workflow()

def step1():
    # 执行中：应处于 running 状态
    running = not w.start_action.isEnabled() and w.pause_action.isEnabled()
    check('执行中按钮状态 running', running)
    # 暂停
    w.execution.pause_workflow()
    QTimer.singleShot(300, step2)

def step2():
    paused = w.resume_action.isEnabled() and not w.pause_action.isEnabled()
    check('暂停后按钮状态 paused', paused)
    # 恢复
    w.execution.resume_workflow()
    QTimer.singleShot(300, step3)

def step3():
    running = not w.start_action.isEnabled() and w.pause_action.isEnabled()
    check('恢复后按钮状态 running', running)
    # 等待执行完毕
    QTimer.singleShot(2500, step4)

def step4():
    idle = w.start_action.isEnabled() and not w.pause_action.isEnabled()
    check('完成后按钮状态 idle', idle)
    print('状态消息序列:', [m for m in messages if '工作流' in m or '就绪' in m])
    app.quit()

# 等待工作流启动
QTimer.singleShot(300, step1)
app.exec_()

# 再次执行验证执行器可重复运行（连接泄漏修复后状态更新不叠加）
w.execution.execute_workflow()

def step5():
    check('第二次执行后 idle', w.start_action.isEnabled())
    print('ALL PASS')
    app.quit()

QTimer.singleShot(3000, step5)
app.exec_()
