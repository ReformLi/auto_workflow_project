# -*- coding: utf-8 -*-
"""
execution_controller.py
功能描述: 执行控制——启动/暂停/恢复/终止/验证 + 工具栏按钮状态机 + event_bus 状态订阅

注意：暂停/终止仅在节点间隙生效（当前节点 execute() 返回后才检查标志，
如 Delay 节点睡眠中无法立即中断），与执行引擎的既有设计一致。
"""
from core.events import event_bus


class ExecutionController:
    """执行控制器，window 为宿主主窗口（提供 logger/core_manager）"""

    def __init__(self, window):
        self.window = window
        self.logger = window.logger
        self.core_manager = window.core_manager
        self._connect_events()

    def _connect_events(self):
        """订阅执行状态信号，驱动按钮状态机"""
        event_bus.execution_started.connect(lambda: self.update_execution_buttons('running'))
        event_bus.execution_finished.connect(lambda: self.update_execution_buttons('idle'))
        event_bus.execution_paused.connect(lambda: self.update_execution_buttons('paused'))
        event_bus.execution_resumed.connect(lambda: self.update_execution_buttons('running'))
        event_bus.execution_stopped.connect(lambda: self.update_execution_buttons('stopped'))

    def execute_workflow(self):
        """执行工作流（先验证，通过后启动）"""
        try:
            self.logger.info('🔍 开始执行工作流验证...')
            # 先验证工作流
            validation_result = self.core_manager.validate_workflow()
            if validation_result.get('success', False):
                self.logger.info('✅ 工作流验证通过，开始执行...')
                self.start_workflow()
            else:
                self.logger.error(f'❌ 工作流验证失败: {validation_result.get("message", "未知错误")}')
                self.logger.warning('💡 提示: 请检查节点连接是否正确')
        except Exception as e:
            self.logger.error(f'执行工作流时发生错误: {str(e)}')

    def validate_workflow(self):
        """验证工作流"""
        try:
            self.logger.info('🔍 正在验证工作流...')
            validation_result = self.core_manager.validate_workflow()

            if validation_result.get('success', False):
                self.logger.info('✅ 工作流验证通过！')
                self.logger.info('💡 提示: 工作流结构完整，可以执行')
                self.window.statusBar().showMessage('工作流验证通过', 3000)
            else:
                error_msg = validation_result.get('message', '未知错误')
                self.logger.error(f'❌ 工作流验证失败: {error_msg}')
                self.window.statusBar().showMessage('工作流验证失败', 3000)

        except Exception as e:
            self.logger.error(f'验证工作流时发生错误: {str(e)}')
            self.window.statusBar().showMessage('验证过程中发生错误', 3000)

    def start_workflow(self):
        """启动工作流"""
        try:
            self.logger.info('🚀 开始执行工作流...')
            self.update_execution_buttons('running')
            self.core_manager.execute_workflow()
        except Exception as e:
            self.logger.error(f'启动工作流失败: {str(e)}')
            self.update_execution_buttons('idle')

    def pause_workflow(self):
        """暂停工作流"""
        try:
            self.logger.info('⏸️ 暂停工作流执行')
            self.core_manager.pause_workflow()
        except Exception as e:
            self.logger.error(f'暂停工作流失败: {str(e)}')

    def resume_workflow(self):
        """恢复工作流"""
        try:
            self.logger.info('▶️ 恢复工作流执行')
            self.core_manager.resume_workflow()
        except Exception as e:
            self.logger.error(f'恢复工作流失败: {str(e)}')

    def stop_workflow(self):
        """终止工作流"""
        try:
            self.logger.warning('⏹️ 终止工作流执行')
            self.core_manager.stop_workflow()
        except Exception as e:
            self.logger.error(f'终止工作流失败: {str(e)}')

    def update_execution_buttons(self, state):
        """根据工作流执行状态更新按钮状态

        Args:
            state: 'idle', 'running', 'paused', 'stopped'
        """
        window = self.window
        status_messages = {
            'idle': '就绪 - 拖拽节点创建工作流',
            'running': '工作流正在执行中...',
            'paused': '工作流已暂停',
            'stopped': '工作流已停止'
        }

        if state == 'idle':
            window.start_action.setEnabled(True)
            window.pause_action.setEnabled(False)
            window.resume_action.setEnabled(False)
            window.stop_action.setEnabled(False)
            window.start_action.setText('▶️\n启动')
            window.start_action.setStatusTip('启动工作流执行 (F5)')
        elif state == 'running':
            window.start_action.setEnabled(False)
            window.pause_action.setEnabled(True)
            window.resume_action.setEnabled(False)
            window.stop_action.setEnabled(True)
            window.start_action.setText('⏸️\n运行中')
            window.start_action.setStatusTip('工作流正在运行中...')
        elif state == 'paused':
            window.start_action.setEnabled(False)
            window.pause_action.setEnabled(False)
            window.resume_action.setEnabled(True)
            window.stop_action.setEnabled(True)
            window.start_action.setText('⏸️\n已暂停')
            window.start_action.setStatusTip('工作流已暂停')
        elif state == 'stopped':
            window.start_action.setEnabled(True)
            window.pause_action.setEnabled(False)
            window.resume_action.setEnabled(False)
            window.stop_action.setEnabled(False)
            window.start_action.setText('▶️\n启动')
            window.start_action.setStatusTip('启动工作流执行 (F5)')

        # 更新状态栏消息
        message = status_messages.get(state, '未知状态')
        window.statusBar().showMessage(message, 0)  # 0表示永久显示，直到下次更新
