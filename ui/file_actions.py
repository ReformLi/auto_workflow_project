# -*- coding: utf-8 -*-
"""
file_actions.py
功能描述: 文件操作命令（新建/打开/保存/另存为/清空），持有当前文件路径状态
"""
from PyQt5.QtWidgets import QFileDialog, QMessageBox


class FileActions:
    """文件操作命令集合，window 为宿主主窗口（提供 logger/core_manager）"""

    def __init__(self, window):
        self.window = window
        self.logger = window.logger
        self.core_manager = window.core_manager
        self.current_file = None

    def _notify_status(self, dirty=False):
        """通知主窗口同步状态栏文件指示（主窗口未就绪时静默忽略）"""
        notify = getattr(self.window, 'notify_file_change', None)
        if callable(notify):
            try:
                notify(dirty=dirty)
            except Exception:
                pass

    def new_workflow(self):
        """新建工作流"""
        self.logger.info('开始新建工作流...')
        reply = QMessageBox.question(
            self.window, '新建工作流',
            '是否保存当前工作流？',
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )
        if reply == QMessageBox.Cancel:
            return
        if reply == QMessageBox.Yes:
            if not self.save_workflow():  # 如果保存失败则取消新建
                return

        # 清空节点图
        self.core_manager.new_workflow()
        # 清除当前文件记录
        self.current_file = None
        status_view = getattr(self.window, 'status_view', None)
        reset_elapsed = getattr(status_view, 'reset_elapsed', None)
        if callable(reset_elapsed):
            reset_elapsed()
        self._notify_status()
        self.logger.info('新建工作流')

    def open_workflow(self):
        """打开工作流"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.window, '打开工作流文件', '', 'JSON文件 (*.json);;所有文件 (*.*)'
        )
        if file_path:
            try:
                if self.core_manager.load_workflow(file_path):
                    self.current_file = file_path
                    self._notify_status()
                    self.logger.info(f'打开工作流文件: {file_path}')
                else:
                    self.logger.error(f'打开文件失败:无法加载')
            except Exception as e:
                self.logger.error(f'打开文件失败: {str(e)}')

    def save_workflow(self):
        """保存工作流"""
        if not self.current_file:
            return self.save_workflow_as()
        try:
            if self.core_manager.save_workflow(self.current_file):
                self.logger.info(f'保存工作流到: {self.current_file}')
                self._notify_status()
                return True
        except Exception as e:
            self.logger.error(f'保存文件失败: {str(e)}')
        return False

    def save_workflow_as(self):
        """另存为工作流"""
        file_path, _ = QFileDialog.getSaveFileName(
            self.window, '保存工作流文件', '', 'JSON文件 (*.json);;所有文件 (*.*)'
        )
        if file_path:
            self.current_file = file_path
            return self.save_workflow()
        return False

    def clear_workflow(self):
        """清空工作流"""
        self.logger.info('开始清空工作流...')
        reply = QMessageBox.question(
            self.window, '清空工作流',
            '确认清空当前工作流？',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.core_manager.clear_all()
            self.logger.info('清空工作流')
