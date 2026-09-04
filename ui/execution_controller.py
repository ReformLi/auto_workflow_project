# -*- coding: utf-8 -*-
"""
execution_controller.py
功能描述: 执行控制——启动/暂停/恢复/终止/验证 + 工具栏按钮状态机 + event_bus 状态订阅

注意：暂停/终止仅在节点间隙生效（当前节点 execute() 返回后才检查标志，
      如 Delay 节点睡眠中无法立即中断），与执行引擎的既有设计一致。
      本文件只改「按钮渲染与状态栏输出」，不改状态机语义与执行链路。
"""
from core.events import event_bus
from ui import icons


class ExecutionController:
    """执行控制器，window 为宿主主窗口（提供 logger/core_manager/status_view）"""

    # 状态 → (启动按钮文案, 启动按钮图标)
    _START_BUTTON = {
        'idle':    ('启动', 'fa5s.play'),
        'running': ('运行中', 'fa5s.play'),
        'paused':  ('已暂停', 'fa5s.pause'),
        'stopped': ('启动', 'fa5s.play'),
    }

    def __init__(self, window):
        self.window = window
        self.logger = window.logger
        self.core_manager = window.core_manager
        self._connect_events()

    def _connect_events(self):
        """订阅执行状态信号，驱动按钮状态机"""
        event_bus.execution_started.connect(lambda: self.update_execution_buttons('running'))
        event_bus.execution_finished.connect(self._on_finished)
        event_bus.execution_paused.connect(lambda: self.update_execution_buttons('paused'))
        event_bus.execution_resumed.connect(lambda: self.update_execution_buttons('running'))
        event_bus.execution_stopped.connect(lambda: self.update_execution_buttons('stopped'))

    def _on_finished(self, success):
        """执行结束：成功/失败分别呈现"""
        self.update_execution_buttons('idle', success=success)

    # ── 命令 ────────────────────────────────────────────
    def execute_workflow(self):
        """执行工作流（先验证，通过后启动）"""
        try:
            self.logger.info('开始执行工作流验证...')
            validation_result = self.core_manager.validate_workflow()
            if validation_result.get('success', False):
                self.logger.info('工作流验证通过，开始执行...')
                self.start_workflow()
            else:
                self.logger.error(f'工作流验证失败: {validation_result.get("message", "未知错误")}')
                self.logger.warning('提示: 请检查节点连接是否正确')
        except Exception as e:
            self.logger.error(f'执行工作流时发生错误: {str(e)}')

    def validate_workflow(self):
        """验证工作流"""
        try:
            self.logger.info('正在验证工作流...')
            validation_result = self.core_manager.validate_workflow()

            if validation_result.get('success', False):
                self.logger.info('工作流验证通过！结构完整，可以执行')
                self._status().set_message('工作流验证通过', 3000)
            else:
                error_msg = validation_result.get('message', '未知错误')
                self.logger.error(f'工作流验证失败: {error_msg}')
                self._status().set_message(f'验证失败：{error_msg}', 5000)
        except Exception as e:
            self.logger.error(f'验证工作流时发生错误: {str(e)}')
            self._status().set_message('验证过程中发生错误', 5000)

    def start_workflow(self):
        """启动工作流"""
        try:
            self.logger.info('开始执行工作流...')
            self.update_execution_buttons('running')
            self.core_manager.execute_workflow()
        except Exception as e:
            self.logger.error(f'启动工作流失败: {str(e)}')
            self.update_execution_buttons('idle')

    def pause_workflow(self):
        """暂停工作流"""
        try:
            self.logger.info('暂停工作流执行')
            self.core_manager.pause_workflow()
        except Exception as e:
            self.logger.error(f'暂停工作流失败: {str(e)}')

    def resume_workflow(self):
        """恢复工作流"""
        try:
            self.logger.info('恢复工作流执行')
            self.core_manager.resume_workflow()
        except Exception as e:
            self.logger.error(f'恢复工作流失败: {str(e)}')

    def stop_workflow(self):
        """终止工作流"""
        try:
            self.logger.warning('终止工作流执行')
            self.core_manager.stop_workflow()
        except Exception as e:
            self.logger.error(f'终止工作流失败: {str(e)}')

    # ── 状态机 ──────────────────────────────────────────
    def update_execution_buttons(self, state, success=None):
        """根据执行状态更新按钮可用态、图标与状态栏（语义与原实现一致）

        Args:
            state: 'idle' / 'running' / 'paused' / 'stopped'
            success: 仅 idle 且由执行结束触发时传入，True=成功 False=失败
        """
        window = self.window

        if state == 'idle':
            window.start_action.setEnabled(True)
            window.pause_action.setEnabled(False)
            window.resume_action.setEnabled(False)
            window.stop_action.setEnabled(False)
        elif state == 'running':
            window.start_action.setEnabled(False)
            window.pause_action.setEnabled(True)
            window.resume_action.setEnabled(False)
            window.stop_action.setEnabled(True)
        elif state == 'paused':
            window.start_action.setEnabled(False)
            window.pause_action.setEnabled(False)
            window.resume_action.setEnabled(True)
            window.stop_action.setEnabled(True)
        elif state == 'stopped':
            window.start_action.setEnabled(True)
            window.pause_action.setEnabled(False)
            window.resume_action.setEnabled(False)
            window.stop_action.setEnabled(False)

        # 启动按钮文案/图标随状态切换（图标色由 QSS #startAction 负责）
        text, icon_name = self._START_BUTTON.get(state, self._START_BUTTON['idle'])
        window.start_action.setText(text)
        window.start_action.setIcon(icons.icon(icon_name, scale=0.9))

        # 状态栏：结束态优先呈现成功/失败
        status = self._status()
        if state == 'idle' and success is not None:
            status.set_state('success' if success else 'error')
        else:
            status.set_state(state)

    def _status(self):
        """取主窗口的状态栏视图（P1 前为 None 时回落原生 showMessage）"""
        status_view = getattr(self.window, 'status_view', None)
        if status_view is not None:
            return status_view
        return _LegacyStatusShim(self.window.statusBar())


class _LegacyStatusShim:
    """兼容壳：主窗口尚未提供 status_view 时退回 showMessage 行为"""

    def __init__(self, bar):
        self._bar = bar

    def set_message(self, text, timeout_ms=0):
        self._bar.showMessage(text, timeout_ms)

    def set_state(self, state, message=None):
        self._bar.showMessage(message or state)
