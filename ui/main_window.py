# -*- coding: utf-8 -*-
"""
主窗口类
"""

import logging

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QTextCharFormat, QColor
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QAction, QFileDialog,
    QTextEdit, QDockWidget, QToolBar, QSplitter,
    QVBoxLayout, QMessageBox, QHBoxLayout, QPushButton,
    QLineEdit, QLabel, QToolButton, QDialog
)

from app.config import WINDOW_HEIGHT, WINDOW_WIDTH
from core.events import event_bus
from core.manager import CoreManager
from ui.actions import build_menu_bar, build_tool_bar
from ui.log_panel import TextEditHandler
from ui.log_search_bar import LogSearchBar
from ui.node_graph_panel import NodeGraphPanel
from ui.nodes_panel import NodeLibraryWidget
from ui.styles import ThemeManager
from ui.settings_dialog import SettingsDialog
from ui.about_dialog import AboutDialog


class WorkflowMainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

        self.setWindowTitle('自动工作流设计器')
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # 初始化主题管理器
        self.theme_manager = ThemeManager()

        # 设置样式
        self.setStyleSheet(self.theme_manager.get_stylesheet('main_window'))
        self.core_manager = CoreManager()
        # 初始化 UI
        self.setup_ui()
        self.setup_logging()
        event_bus.execution_started.connect(lambda: self.logger.info("工作流开始执行"))
        event_bus.execution_finished.connect(lambda: self.logger.info("工作流执行结束"))
        event_bus.node_started.connect(lambda name: self.logger.info(f"执行节点: {name}"))
        event_bus.node_finished.connect(lambda name, dict: self.logger.info(f"节点完成: {name},返回信息：{dict}"))
        event_bus.error_occurred.connect(lambda err: self.logger.error(err))

        # 连接执行状态更新
        event_bus.execution_started.connect(lambda: self.update_execution_buttons('running'))
        event_bus.execution_finished.connect(lambda: self.update_execution_buttons('idle'))
        event_bus.execution_paused.connect(lambda: self.update_execution_buttons('paused'))
        event_bus.execution_resumed.connect(lambda: self.update_execution_buttons('running'))
        event_bus.execution_stopped.connect(lambda: self.update_execution_buttons('stopped'))

        self.logger.info('主窗口初始化完成')


    def setup_ui(self):
        """设置用户界面"""
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧节点库（1/6宽度）
        self.setup_node_library(splitter)

        # 右侧节点图编辑器（5/6宽度）
        self.setup_node_graph(splitter)

        # 设置分割器比例
        splitter.setSizes([200, 1000])

        # 设置菜单栏
        build_menu_bar(self)

        # 设置工具栏
        build_tool_bar(self)

        # 设置日志窗口
        self.setup_log_window()

        # 设置状态栏
        self.setup_status_bar()

    def setup_node_library(self, parent):
        """设置节点库"""
        dock = QDockWidget('节点库', self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea)

        # 设置dock widget样式以确保标题可见
        dock.setStyleSheet(self.theme_manager.get_stylesheet('dock_widget'))

        # 创建节点库管理器
        self.node_library = NodeLibraryWidget(self.core_manager, self.theme_manager)
        dock.setWidget(self.node_library)
        parent.addWidget(dock)

    def setup_node_graph(self, parent):
        """设置节点图编辑器"""
        self.node_graph_panel = NodeGraphPanel(self.core_manager,self.theme_manager)
        graph_widget = self.node_graph_panel.get_widget()

        parent.addWidget(graph_widget)

        # 可选：连接信号用于日志
        event_bus.node_dropped.connect(self.on_node_dropped)

    def on_node_dropped(self, node_type, scene_pos):
        """节点拖拽创建后的额外处理（例如日志）"""
        self.logger.info(f"节点已创建: {node_type} 位置 {scene_pos}")
        self.update_node_count()

    def update_node_count(self):
        """更新状态栏中的节点计数"""
        try:
            node_count = self.core_manager.get_node_count()
            current_message = self.statusBar().currentMessage()
            if '就绪' in current_message or '节点' in current_message:
                self.statusBar().showMessage(f'就绪 - 当前有 {node_count} 个节点', 0)
        except Exception as e:
            self.logger.debug(f"更新节点计数失败: {str(e)}")

    def setup_log_window(self):
        """设置日志窗口"""
        log_dock = QDockWidget('日志窗口', self)
        log_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        log_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        # 设置dock widget样式以确保标题可见
        log_dock.setStyleSheet(self.theme_manager.get_stylesheet('dock_widget'))

        # 创建日志面板容器
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(0)

        # 创建日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont('Courier New', 10))
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)  # 禁用自动换行，保持日志格式
        # 样式将在apply_theme中设置

        # 创建搜索工具栏（位于日志文本框上方）
        self.log_search_bar = LogSearchBar(self.log_text, self.theme_manager)
        self.log_search_bar.closed.connect(self._on_log_search_closed)
        log_layout.addWidget(self.log_search_bar)

        log_layout.addWidget(self.log_text)

        log_dock.setWidget(log_container)
        self.addDockWidget(Qt.BottomDockWidgetArea, log_dock)
        log_dock.setMaximumHeight(400)
        log_dock.setMinimumHeight(100)
        # 设置默认高度为窗口的 1/3
        log_dock.resize(log_dock.width(), 200)

        # 应用初始主题到日志文本框
        self.log_text.setStyleSheet(self.theme_manager.get_stylesheet('log_text_edit'))

    def setup_logging(self):
        """设置日志记录"""
        # 创建日志处理器
        handler = TextEditHandler(self.log_text, self.theme_manager)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)

        # 获取根日志记录器并添加处理器
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        # 添加初始日志消息
        self.logger.info("=" * 50)
        self.logger.info("工作流设计器已启动")
        self.logger.info("=" * 50)
        self.logger.debug("调试模式已启用")
        self.logger.info("提示: 从左侧节点库拖拽节点到画布上创建工作流")
        self.logger.info("提示: 使用 F5 执行工作流，F6 验证工作流")

    def new_workflow(self):
        """新建工作流"""
        # 检查当前是否有未保存的更改
        # 可选：询问用户是否保存
        self.logger.info('开始新建工作流...')
        reply = QMessageBox.question(
            self, '新建工作流',
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
        if hasattr(self, 'current_file'):
            delattr(self, 'current_file')
        self.logger.info('新建工作流')

    def open_workflow(self):
        """打开工作流"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, '打开工作流文件', '', 'JSON文件 (*.json);;所有文件 (*.*)'
        )
        if file_path:
            try:
                if self.core_manager.load_workflow(file_path):
                    self.current_file = file_path
                    self.logger.info(f'打开工作流文件: {file_path}')
                else:
                    self.logger.error(f'打开文件失败:无法加载')
            except Exception as e:
                self.logger.error(f'打开文件失败: {str(e)}')

    def save_workflow(self):
        """保存工作流"""
        if not hasattr(self, 'current_file') or not self.current_file:
            return self.save_workflow_as()
        try:
            if self.core_manager.save_workflow(self.current_file):
                self.logger.info(f'保存工作流到: {self.current_file}')
                return True
        except Exception as e:
            self.logger.error(f'保存文件失败: {str(e)}')
        return False

    def save_workflow_as(self):
        """另存为工作流"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, '保存工作流文件', '', 'JSON文件 (*.json);;所有文件 (*.*)'
        )
        if file_path:
            self.current_file = file_path
            return self.save_workflow()
        return False

    def clear_workflow(self):
        """清空工作流"""
        self.logger.info('开始清空工作流...')
        reply = QMessageBox.question(
            self, '清空工作流',
            '确认清空当前工作流？',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.core_manager.clear_all()
            self.logger.info('清空工作流')

    def execute_workflow(self):
        """执行工作流"""
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
                self.logger.info('💡 工作流结构完整，可以执行')
                # 可以在状态栏显示成功消息
                self.statusBar().showMessage('工作流验证通过', 3000)
            else:
                error_msg = validation_result.get('message', '未知错误')
                self.logger.error(f'❌ 工作流验证失败: {error_msg}')
                # 可以在状态栏显示错误消息
                self.statusBar().showMessage('工作流验证失败', 3000)

        except Exception as e:
            self.logger.error(f'验证工作流时发生错误: {str(e)}')
            self.statusBar().showMessage('验证过程中发生错误', 3000)

    def show_search_toolbar(self):
        """显示搜索工具栏"""
        self.log_search_bar.open_search()
        self.search_log_action.setEnabled(False)

    def _on_log_search_closed(self):
        """搜索栏关闭后恢复搜索按钮"""
        self.search_log_action.setEnabled(True)

    def show_settings(self):
        """显示设置对话框"""
        try:
            dialog = SettingsDialog(self.theme_manager, self)
            if dialog.exec_() == QDialog.Accepted:
                self.logger.info('设置已更新')
        except Exception as e:
            self.logger.error(f'打开设置对话框失败: {str(e)}')

    def show_about(self):
        """显示关于对话框"""
        try:
            dialog = AboutDialog(self.theme_manager, self)
            dialog.exec_()
        except Exception as e:
            self.logger.error(f'打开关于对话框失败: {str(e)}')

    def apply_theme(self):
        """应用主题更改"""
        # 重新设置主窗口样式
        self.setStyleSheet(self.theme_manager.get_stylesheet('main_window'))

        # 更新日志文本框样式
        self.log_text.setStyleSheet(self.theme_manager.get_stylesheet('log_text_edit'))

        # 更新搜索工具栏样式
        if hasattr(self, 'log_search_bar'):
            self.log_search_bar.apply_theme(self.theme_manager)

        # 更新节点库主题
        if hasattr(self, 'node_library'):
            self.node_library.update_theme(self.theme_manager)

        # 更新节点图主题
        if hasattr(self, 'node_graph_panel'):
            self.node_graph_panel.update_theme(self.theme_manager)

        # 重新设置日志处理器格式以匹配新主题
        self.update_log_handler_theme()

        self.logger.info(f'主题已切换为: {self.theme_manager.current_theme}')

    def update_grid(self,grid_display:bool):
        # 更新节点图网格线
        if hasattr(self, 'node_graph_panel'):
            self.node_graph_panel.update_grid(grid_display)

    def update_log_handler_theme(self):
        """更新日志处理器主题"""
        # 找到我们的TextEditHandler并更新其主题
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, TextEditHandler):
                handler.theme_manager = self.theme_manager
                handler.setup_formats()
                handler.on_theme_changed()

    def undo(self):
        """撤销操作"""
        self.core_manager.undo()
        self.logger.info('撤销操作')

    def redo(self):
        """重做操作"""
        self.core_manager.redo()
        self.logger.info('重做操作')

    def closeEvent(self, event):
        """窗口关闭事件"""
        reply = QtWidgets.QMessageBox.question(
            self, '确认退出', '确定要退出应用程序吗？',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            """窗口关闭事件：清理资源"""
            self.logger.info("正在关闭主窗口，清理资源...")
            # 显式清理节点图管理器
            self.core_manager.cleanup()
            event.accept()
        else:
            event.ignore()

    def copy_nodes(self):
        """复制选中的节点"""
        self.logger.info('复制选中的节点...')
        self.core_manager.copy_selected_nodes()

    def paste_nodes(self):
        """粘贴节点"""
        self.logger.info('粘贴节点...')
        self.core_manager.paste_nodes()

    def delete_selected(self):
        """删除选中的节点和连接"""
        self.logger.info('删除选中的节点和连接...')
        self.core_manager.delete_selected()

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

    def setup_status_bar(self):
        """设置状态栏"""
        status_bar = self.statusBar()
        status_bar.showMessage('就绪 - 拖拽节点创建工作流')

    def update_execution_buttons(self, state):
        """根据工作流执行状态更新按钮状态

        Args:
            state: 'idle', 'running', 'paused', 'stopped'
        """
        status_messages = {
            'idle': '就绪 - 拖拽节点创建工作流',
            'running': '工作流正在执行中...',
            'paused': '工作流已暂停',
            'stopped': '工作流已停止'
        }

        if state == 'idle':
            self.start_action.setEnabled(True)
            self.pause_action.setEnabled(False)
            self.resume_action.setEnabled(False)
            self.stop_action.setEnabled(False)
            self.start_action.setText('▶️\n启动')
            self.start_action.setStatusTip('启动工作流执行 (F5)')
        elif state == 'running':
            self.start_action.setEnabled(False)
            self.pause_action.setEnabled(True)
            self.resume_action.setEnabled(False)
            self.stop_action.setEnabled(True)
            self.start_action.setText('⏸️\n运行中')
            self.start_action.setStatusTip('工作流正在运行中...')
        elif state == 'paused':
            self.start_action.setEnabled(False)
            self.pause_action.setEnabled(False)
            self.resume_action.setEnabled(True)
            self.stop_action.setEnabled(True)
            self.start_action.setText('⏸️\n已暂停')
            self.start_action.setStatusTip('工作流已暂停')
        elif state == 'stopped':
            self.start_action.setEnabled(True)
            self.pause_action.setEnabled(False)
            self.resume_action.setEnabled(False)
            self.stop_action.setEnabled(False)
            self.start_action.setText('▶️\n启动')
            self.start_action.setStatusTip('启动工作流执行 (F5)')

        # 更新状态栏消息
        message = status_messages.get(state, '未知状态')
        self.statusBar().showMessage(message, 0)  # 0表示永久显示，直到下次更新
