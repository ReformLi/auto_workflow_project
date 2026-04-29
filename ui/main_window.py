# -*- coding: utf-8 -*-
"""
主窗口类
"""

import logging

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QAction, QFileDialog,
    QTextEdit, QDockWidget, QToolBar, QSplitter, QVBoxLayout, QMessageBox
)

from app.config import WINDOW_HEIGHT, WINDOW_WIDTH
from core.events import event_bus
from core.manager import CoreManager
from ui.log_panel import TextEditHandler
from ui.node_graph_panel import NodeGraphPanel
from ui.nodes_panel import NodeLibraryWidget


class WorkflowMainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

        self.setWindowTitle('自动工作流设计器')
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # 设置样式
        self.setStyleSheet(self.get_stylesheet())
        self.core_manager = CoreManager()
        # 初始化 UI
        self.setup_ui()
        self.setup_logging()
        event_bus.execution_started.connect(lambda: self.logger.info("工作流开始执行"))
        event_bus.execution_finished.connect(lambda: self.logger.info("工作流执行结束"))
        event_bus.node_started.connect(lambda name: self.logger.info(f"执行节点: {name}"))
        event_bus.node_finished.connect(lambda name, dict: self.logger.info(f"节点完成: {name},返回信息：{dict}"))
        event_bus.error_occurred.connect(lambda err: self.logger.error(err))

        self.logger.info('主窗口初始化完成')

    def get_stylesheet(self):
        """获取样式表"""
        return """
            QMainWindow {
                background-color: #2b2b2b;
            }
            QMenuBar {
                background-color: #333333;
                color: #ffffff;
                border-bottom: 1px solid #444444;
            }
            QMenuBar::item {
                background-color: #333333;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #444444;
            }
            QMenu {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #444444;
            }
            QMenu::item:selected {
                background-color: #444444;
            }
            QToolBar {
                background-color: #333333;
                border: none;
                border-bottom: 1px solid #444444;
            }
            QToolButton {
                color: #ffffff;
            }
            QToolButton:hover {
                background-color: #444444;
            }
            QDockWidget {
                color: #ffffff;
                background-color: #2b2b2b;
                border: none;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #444444;
            }
        """

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

    def setup_tool_bar(self):
        """设置工具栏"""
        tool_bar = QToolBar('工具栏', self)
        tool_bar.setIconSize(QSize(24, 24))
        tool_bar.setMovable(False)
        self.addToolBar(tool_bar)

        # 新建
        new_action = QAction('新建', self)
        new_action.triggered.connect(self.new_workflow)
        tool_bar.addAction(new_action)

        # 打开
        open_action = QAction('打开', self)
        open_action.triggered.connect(self.open_workflow)
        tool_bar.addAction(open_action)

        # 保存
        save_action = QAction('保存', self)
        save_action.triggered.connect(self.save_workflow)
        tool_bar.addAction(save_action)

        tool_bar.addSeparator()

        # 清空
        clear_action = QAction('清空', self)
        clear_action.triggered.connect(self.clear_workflow)
        tool_bar.addAction(clear_action)

        tool_bar.addSeparator()

        # # 执行
        # execute_action = QAction('执行', self)
        # execute_action.triggered.connect(self.execute_workflow)
        # tool_bar.addAction(execute_action)

        # tool_bar.addSeparator()
        # 执行控制
        self.start_action = QAction('启动', self)
        self.start_action.triggered.connect(self.start_workflow)
        tool_bar.addAction(self.start_action)
        self.pause_action = QAction('暂停', self)
        self.pause_action.triggered.connect(self.pause_workflow)
        tool_bar.addAction(self.pause_action)
        self.resume_action = QAction('恢复', self)
        self.resume_action.triggered.connect(self.resume_workflow)
        tool_bar.addAction(self.resume_action)
        self.stop_action = QAction('终止', self)
        self.stop_action.triggered.connect(self.stop_workflow)
        tool_bar.addAction(self.stop_action)

    def setup_node_library(self, parent):
        """设置节点库"""
        dock = QDockWidget('节点库', self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea)

        # 创建节点库管理器
        self.node_library = NodeLibraryWidget(self.core_manager)
        dock.setWidget(self.node_library)
        parent.addWidget(dock)

    def setup_node_graph(self, parent):
        """设置节点图编辑器"""
        self.node_graph_panel = NodeGraphPanel(self.core_manager)
        graph_widget = self.core_manager.graph_manager.get_widget()
        parent.addWidget(graph_widget)

        # 可选：连接信号用于日志
        event_bus.node_dropped.connect(self.on_node_dropped)

    def on_node_dropped(self, node_type, scene_pos):
        """节点拖拽创建后的额外处理（例如日志）"""
        self.logger.info(f"节点已创建: {node_type} 位置 {scene_pos}")

    def setup_log_window(self):
        """设置日志窗口"""
        log_dock = QDockWidget('日志窗口', self)
        log_dock.setAllowedAreas(Qt.BottomDockWidgetArea)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont('Courier New', 10))

        log_dock.setWidget(self.log_text)
        self.addDockWidget(Qt.BottomDockWidgetArea, log_dock)
        log_dock.setMaximumHeight(200)

    def setup_logging(self):
        """设置日志记录"""
        # 创建日志处理器
        handler = TextEditHandler(self.log_text)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)

        # 获取根日志记录器并添加处理器
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

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
        self.logger.info('开始执行工作流...')
        # 这里实现工作流执行逻辑

    def validate_workflow(self):
        """验证工作流"""
        self.logger.info('验证工作流...')
        # 这里实现工作流验证逻辑

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
        # if hasattr(self, '_executor') and self._executor._thread and self._executor._thread.isRunning():
        #     self.logger.warning("工作流已在运行中")
        #     return
        self.core_manager.execute_workflow()

    def pause_workflow(self):
        if hasattr(self, '_executor'):
            self._executor.pause()

    def resume_workflow(self):
        if hasattr(self, '_executor'):
            self._executor.resume()

    def stop_workflow(self):
        if hasattr(self, '_executor'):
            self._executor.stop()