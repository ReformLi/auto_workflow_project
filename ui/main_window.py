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
from ui.log_panel import TextEditHandler
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
        self.setup_menu_bar()

        # 设置工具栏
        self.setup_tool_bar()

        # 设置日志窗口
        self.setup_log_window()

        # 设置状态栏
        self.setup_status_bar()

    def setup_menu_bar(self):
        """设置菜单栏"""
        menu_bar = self.menuBar()

        # 文件菜单
        file_menu = menu_bar.addMenu('文件')

        new_action = QAction('新建', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_workflow)
        file_menu.addAction(new_action)

        open_action = QAction('打开', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_workflow)
        file_menu.addAction(open_action)

        save_action = QAction('保存', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_workflow)
        file_menu.addAction(save_action)

        save_as_action = QAction('另存为', self)
        save_as_action.setShortcut('Ctrl+Shift+S')
        save_as_action.triggered.connect(self.save_workflow_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menu_bar.addMenu('编辑')

        undo_action = QAction('撤销', self)
        undo_action.setShortcut('Ctrl+Z')
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction('重做', self)
        redo_action.setShortcut('Ctrl+Y')
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        # 删除（新增）
        delete_action = QAction('删除', self)
        delete_action.setShortcut('Delete')  # 快捷键 Delete
        delete_action.triggered.connect(self.delete_selected)
        edit_menu.addAction(delete_action)

        edit_menu.addSeparator()

        # 添加复制粘贴
        copy_action = QAction('复制', self)
        copy_action.setShortcut('Ctrl+C')
        copy_action.triggered.connect(self.copy_nodes)
        edit_menu.addAction(copy_action)

        paste_action = QAction('粘贴', self)
        paste_action.setShortcut('Ctrl+V')
        paste_action.triggered.connect(self.paste_nodes)
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        clear_action = QAction('清空', self)
        clear_action.triggered.connect(self.clear_workflow)
        edit_menu.addAction(clear_action)

        # 运行菜单
        run_menu = menu_bar.addMenu('运行')

        execute_action = QAction('执行工作流', self)
        execute_action.setShortcut('F5')
        execute_action.triggered.connect(self.execute_workflow)
        run_menu.addAction(execute_action)

        validate_action = QAction('验证工作流', self)
        validate_action.setShortcut('F6')
        validate_action.triggered.connect(self.validate_workflow)
        run_menu.addAction(validate_action)

        # 工具菜单
        tools_menu = menu_bar.addMenu('工具')

        settings_action = QAction('设置', self)
        settings_action.setShortcut('Ctrl+,')
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)

        tools_menu.addSeparator()

        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        tools_menu.addAction(about_action)

    def setup_tool_bar(self):
        """设置工具栏"""
        tool_bar = QToolBar('工具栏', self)
        tool_bar.setIconSize(QSize(20, 20))
        tool_bar.setMovable(False)
        tool_bar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(tool_bar)

        # 文件操作组
        # 新建
        new_action = QAction('📄\n新建', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_workflow)
        new_action.setStatusTip('新建工作流 (Ctrl+N)')
        tool_bar.addAction(new_action)

        # 打开
        open_action = QAction('📂\n打开', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_workflow)
        open_action.setStatusTip('打开工作流文件 (Ctrl+O)')
        tool_bar.addAction(open_action)

        # 保存
        save_action = QAction('💾\n保存', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_workflow)
        save_action.setStatusTip('保存工作流 (Ctrl+S)')
        tool_bar.addAction(save_action)

        tool_bar.addSeparator()

        # 编辑操作组
        # 清空
        clear_action = QAction('🗑️\n清空', self)
        clear_action.triggered.connect(self.clear_workflow)
        clear_action.setStatusTip('清空当前工作流')
        tool_bar.addAction(clear_action)

        tool_bar.addSeparator()

        # 执行控制组 - 这些按钮会根据工作流状态变化
        self.start_action = QAction('▶️\n启动', self)
        self.start_action.setShortcut('F5')
        self.start_action.triggered.connect(self.start_workflow)
        self.start_action.setStatusTip('启动工作流执行 (F5)')
        tool_bar.addAction(self.start_action)

        self.pause_action = QAction('⏸️\n暂停', self)
        self.pause_action.triggered.connect(self.pause_workflow)
        self.pause_action.setStatusTip('暂停工作流执行')
        self.pause_action.setEnabled(False)
        tool_bar.addAction(self.pause_action)

        self.resume_action = QAction('⏯️\n恢复', self)
        self.resume_action.triggered.connect(self.resume_workflow)
        self.resume_action.setStatusTip('恢复工作流执行')
        self.resume_action.setEnabled(False)
        tool_bar.addAction(self.resume_action)

        self.stop_action = QAction('⏹️\n终止', self)
        self.stop_action.triggered.connect(self.stop_workflow)
        self.stop_action.setStatusTip('终止工作流执行')
        self.stop_action.setEnabled(False)
        tool_bar.addAction(self.stop_action)

        # 验证按钮
        tool_bar.addSeparator()
        self.validate_action = QAction('✓\n验证', self)
        self.validate_action.setShortcut('F6')
        self.validate_action.triggered.connect(self.validate_workflow)
        self.validate_action.setStatusTip('验证工作流 (F6)')
        tool_bar.addAction(self.validate_action)

        # 搜索日志按钮
        tool_bar.addSeparator()
        self.search_log_action = QAction('🔍\n搜索日志', self)
        self.search_log_action.setShortcut('Ctrl+F')
        self.search_log_action.triggered.connect(self.show_search_toolbar)
        self.search_log_action.setStatusTip('搜索日志 (Ctrl+F)')
        tool_bar.addAction(self.search_log_action)

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

        # 创建搜索工具栏
        self.setup_log_search_toolbar(log_container)
        log_layout.addWidget(self.log_search_toolbar)

        # 创建日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont('Courier New', 10))
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)  # 禁用自动换行，保持日志格式
        # 样式将在apply_theme中设置
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
        self.log_search_toolbar.setVisible(True)
        self.log_search_box.setFocus()
        self.search_log_action.setEnabled(False)

    def hide_search_toolbar(self):
        """隐藏搜索工具栏"""
        self.log_search_toolbar.setVisible(False)
        self.log_search_box.clear()
        self.search_log_action.setEnabled(True)
        self.clear_search_highlights()

    def search_logs(self, search_text):
        """搜索日志内容"""
        if not search_text:
            self.clear_search_highlights()
            self.search_count_label.setText("0/0")
            return

        # 清除之前的高亮
        self.clear_search_highlights()

        # 搜索匹配项
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.Start)

        self.search_matches = []
        format = QTextCharFormat()
        format.setBackground(QColor('#ffa502'))  # 橙色高亮
        format.setForeground(QColor('#000000'))  # 黑色文本

        while True:
            cursor = self.log_text.document().find(search_text, cursor)
            if cursor.isNull():
                break
            # 保存匹配位置
            self.search_matches.append(cursor.position())
            # 高亮匹配项
            cursor.movePosition(cursor.NoMove, cursor.KeepAnchor, len(search_text))
            self.log_text.setTextCursor(cursor)
            cursor.mergeCharFormat(format)
            cursor.clearSelection()

        # 更新计数显示
        total_matches = len(self.search_matches)
        if total_matches > 0:
            self.current_match_index = 0
            self.highlight_current_match()
            self.search_count_label.setText(f"{self.current_match_index + 1}/{total_matches}")
        else:
            self.current_match_index = -1
            self.search_count_label.setText("0/0")

    def clear_search_highlights(self):
        """清除搜索高亮"""
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.Start)
        cursor.movePosition(cursor.End, cursor.KeepAnchor)
        format = QTextCharFormat()
        format.clearBackground()
        cursor.mergeCharFormat(format)
        self.search_matches = []
        self.current_match_index = -1

    def highlight_current_match(self):
        """高亮当前匹配项"""
        if not self.search_matches or self.current_match_index < 0:
            return

        # 移除之前的高亮
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.Start)
        cursor.movePosition(cursor.End, cursor.KeepAnchor)
        format = QTextCharFormat()
        format.clearBackground()
        cursor.mergeCharFormat(format)

        # 高亮当前匹配项
        cursor.setPosition(self.search_matches[self.current_match_index])
        cursor.movePosition(cursor.Right, cursor.KeepAnchor, len(self.log_search_box.text()))
        format.setBackground(QColor('#ffa502'))
        format.setForeground(QColor('#000000'))
        cursor.mergeCharFormat(format)

        # 滚动到匹配项
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()

    def search_next(self):
        """查找下一个匹配项"""
        if not self.search_matches:
            return

        self.current_match_index = (self.current_match_index + 1) % len(self.search_matches)
        total_matches = len(self.search_matches)
        self.search_count_label.setText(f"{self.current_match_index + 1}/{total_matches}")
        self.highlight_current_match()

    def search_previous(self):
        """查找上一个匹配项"""
        if not self.search_matches:
            return

        self.current_match_index = (self.current_match_index - 1) % len(self.search_matches)
        total_matches = len(self.search_matches)
        self.search_count_label.setText(f"{self.current_match_index + 1}/{total_matches}")
        self.highlight_current_match()

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
        if hasattr(self, 'log_search_toolbar'):
            self.log_search_toolbar.setStyleSheet(self.theme_manager.get_stylesheet('search_toolbar'))

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
            self.update_execution_buttons('paused')
            if hasattr(self, '_executor'):
                self._executor.pause()
            else:
                # 如果没有执行器，也更新按钮状态
                self.update_execution_buttons('paused')
        except Exception as e:
            self.logger.error(f'暂停工作流失败: {str(e)}')

    def resume_workflow(self):
        """恢复工作流"""
        try:
            self.logger.info('▶️ 恢复工作流执行')
            self.update_execution_buttons('running')
            if hasattr(self, '_executor'):
                self._executor.resume()
            else:
                # 模拟恢复操作
                self.update_execution_buttons('running')
        except Exception as e:
            self.logger.error(f'恢复工作流失败: {str(e)}')

    def stop_workflow(self):
        """终止工作流"""
        try:
            self.logger.warning('⏹️ 终止工作流执行')
            self.update_execution_buttons('stopped')
            if hasattr(self, '_executor'):
                self._executor.stop()
            else:
                # 模拟停止操作
                self.update_execution_buttons('stopped')
        except Exception as e:
            self.logger.error(f'终止工作流失败: {str(e)}')
            self.update_execution_buttons('idle')

    def setup_log_search_toolbar(self, parent):
        """设置日志搜索工具栏"""
        self.log_search_toolbar = QToolBar()
        self.log_search_toolbar.setStyleSheet(self.theme_manager.get_stylesheet('search_toolbar'))
        self.log_search_toolbar.setMovable(False)
        self.log_search_toolbar.setVisible(False)  # 默认隐藏

        # 搜索框
        self.log_search_box = QLineEdit()
        self.log_search_box.setPlaceholderText("搜索日志...")
        self.log_search_box.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.theme_manager.colors['primary_bg']};
                color: {self.theme_manager.colors['text_primary']};
                border: 1px solid {self.theme_manager.colors['border']};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 200px;
            }}
        """)
        self.log_search_box.textChanged.connect(self.search_logs)

        # 搜索结果计数标签
        self.search_count_label = QLabel("0/0")
        self.search_count_label.setStyleSheet(f"color: {self.theme_manager.colors['text_secondary']}; font-size: 11px;")
        self.search_count_label.setMinimumWidth(40)

        # 上一个按钮
        self.search_prev_btn = QToolButton()
        self.search_prev_btn.setText("↑")
        self.search_prev_btn.setToolTip("上一个匹配项")
        self.search_prev_btn.setStyleSheet(f"""
            QToolButton {{
                background-color: {self.theme_manager.colors['button_bg']};
                color: {self.theme_manager.colors['text_primary']};
                border: 1px solid {self.theme_manager.colors['border_light']};
                border-radius: 4px;
                padding: 4px;
                min-width: 30px;
            }}
            QToolButton:hover {{
                background-color: {self.theme_manager.colors['button_hover']};
            }}
        """)
        self.search_prev_btn.clicked.connect(self.search_previous)

        # 下一个按钮
        self.search_next_btn = QToolButton()
        self.search_next_btn.setText("↓")
        self.search_next_btn.setToolTip("下一个匹配项")
        self.search_next_btn.setStyleSheet(f"""
            QToolButton {{
                background-color: {self.theme_manager.colors['button_bg']};
                color: {self.theme_manager.colors['text_primary']};
                border: 1px solid {self.theme_manager.colors['border_light']};
                border-radius: 4px;
                padding: 4px;
                min-width: 30px;
            }}
            QToolButton:hover {{
                background-color: {self.theme_manager.colors['button_hover']};
            }}
        """)
        self.search_next_btn.clicked.connect(self.search_next)

        # 关闭搜索按钮
        self.search_close_btn = QToolButton()
        self.search_close_btn.setText("✕")
        self.search_close_btn.setToolTip("关闭搜索")
        self.search_close_btn.setStyleSheet(f"""
            QToolButton {{
                background-color: {self.theme_manager.colors['button_bg']};
                color: {self.theme_manager.colors['text_primary']};
                border: 1px solid {self.theme_manager.colors['border_light']};
                border-radius: 4px;
                padding: 4px;
                min-width: 30px;
            }}
            QToolButton:hover {{
                background-color: {self.theme_manager.colors['error']};
                border-color: {self.theme_manager.colors['critical']};
            }}
        """)
        self.search_close_btn.clicked.connect(self.hide_search_toolbar)

        # 添加到工具栏
        self.log_search_toolbar.addWidget(self.log_search_box)
        self.log_search_toolbar.addWidget(self.search_count_label)
        self.log_search_toolbar.addWidget(self.search_prev_btn)
        self.log_search_toolbar.addWidget(self.search_next_btn)
        self.log_search_toolbar.addWidget(self.search_close_btn)

        # 搜索相关变量
        self.search_matches = []
        self.current_match_index = -1

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