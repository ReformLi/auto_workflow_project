# -*- coding: utf-8 -*-
"""
主窗口类
布局结构（见 UI_DESIGN.md §4）：
    中央部件
    └── 垂直分割器
        ├── 水平分割器（左：节点库面板 | 右：节点图画布）
        └── 日志面板
样式统一由 app/main.py 的全局 QSS 提供，本文件不再 setStyleSheet。
"""

import logging

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget,
    QTextEdit, QSplitter,
    QVBoxLayout, QDialog
)

from app.config import WINDOW_HEIGHT, WINDOW_WIDTH
from core.events import event_bus
from core.manager import CoreManager
from ui import tokens
from ui.actions import build_menu_bar, build_tool_bar
from ui.execution_controller import ExecutionController
from ui.file_actions import FileActions
from ui.log_filter_bar import LogFilterBar
from ui.log_panel import TextEditHandler
from ui.log_search_bar import LogSearchBar
from ui.node_graph_panel import NodeGraphPanel
from ui.nodes_panel import NodeLibraryWidget
from ui.settings_dialog import SettingsDialog
from ui.about_dialog import AboutDialog
from ui.status_bar import StatusBarView
from ui.theme import ThemeState
from ui.title_bar import DockTitleBar


class WorkflowMainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

        self.setWindowTitle('自动工作流设计器')
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # 界面状态（主题/网格/日志参数，见 ui/theme.py）
        self.theme_state = ThemeState()
        self._log_handler = None

        self.core_manager = CoreManager()

        # 控制器（先于 UI 创建，菜单/工具栏构建时需要绑定其方法）
        self.file_actions = FileActions(self)
        self.execution = ExecutionController(self)

        # 画布视图引用（供缩放监听）
        self._graph_view = None
        # 缩放基准：高 DPI 下视图初始变换不为 1.0，首次布局完成后捕获
        self._zoom_baseline = 1.0
        self._zoom_baseline_captured = False

        # 初始化 UI（顺序：面板 → 工具栏 → 菜单 → 状态栏）
        self.setup_ui()
        self.setup_logging()
        self._connect_event_bus()

        self.logger.info('主窗口初始化完成')

    # ── 组装 ────────────────────────────────────────────
    def setup_ui(self):
        """设置用户界面"""
        central_widget = QWidget()
        central_widget.setObjectName('centralArea')
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 垂直分割器：上半（节点库 | 画布） + 下半（日志）
        self.vertical_splitter = QSplitter(Qt.Vertical)
        self.vertical_splitter.setObjectName('mainVerticalSplitter')
        main_layout.addWidget(self.vertical_splitter)

        self.horizontal_splitter = QSplitter(Qt.Horizontal)
        self.horizontal_splitter.setObjectName('mainHorizontalSplitter')
        self.vertical_splitter.addWidget(self.horizontal_splitter)

        # 左侧节点库面板
        self.setup_node_library()

        # 中央节点图编辑器
        self.setup_node_graph()

        # 节点库固定宽度、画布占余下空间
        self.horizontal_splitter.setStretchFactor(0, 0)
        self.horizontal_splitter.setStretchFactor(1, 1)
        self.horizontal_splitter.setSizes([tokens.NODE_LIBRARY_WIDTH, WINDOW_WIDTH - tokens.NODE_LIBRARY_WIDTH])

        # 底部日志面板
        self.setup_log_window()

        # 日志默认约占 1/4 高度
        self.vertical_splitter.setStretchFactor(0, 1)
        self.vertical_splitter.setStretchFactor(1, 0)
        self.vertical_splitter.setSizes([WINDOW_HEIGHT - 220, 220])

        # 工具栏必须先于菜单构建（运行菜单复用工具栏 QAction）
        build_tool_bar(self)
        build_menu_bar(self)

        # 状态栏
        self.setup_status_bar()

        # 画布缩放指示监听
        self._install_zoom_watcher()

        # 初始网格线与统计
        self.update_grid(self.theme_state.grid_display)
        self.refresh_graph_stats()
        self.refresh_zoom()

    def setup_node_library(self):
        """左侧节点库面板（自定义标题栏，可折叠）"""
        panel = QWidget()
        panel.setObjectName('nodeLibraryPanel')
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.node_library_title = DockTitleBar(
            '节点库', icon_name='fa5s.shapes', accent_color=tokens.DARK['accent'], parent=panel)
        layout.addWidget(self.node_library_title)

        self.node_library = NodeLibraryWidget(self.core_manager, self.theme_state)
        layout.addWidget(self.node_library, 1)
        self.node_library_title.bind_content(self.node_library)

        self.node_library_panel = panel
        self.horizontal_splitter.addWidget(panel)

    def setup_node_graph(self):
        """设置节点图编辑器"""
        self.node_graph_panel = NodeGraphPanel(self.core_manager, self.theme_state)
        self.horizontal_splitter.addWidget(self.node_graph_panel.get_widget())

        # 节点创建后的额外处理（日志；计数由 graph_changed 驱动）
        event_bus.node_dropped.connect(self.on_node_dropped)

    def setup_log_window(self):
        """底部日志面板（内联标题栏 + 搜索栏 + 日志文本框）"""
        panel = QWidget()
        panel.setObjectName('logPanel')
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.log_title = DockTitleBar(
            '日志', icon_name='fa5s.terminal', accent_color=tokens.DARK['info'], parent=panel)
        layout.addWidget(self.log_title)

        # 日志正文 + 搜索栏（一起作为可折叠内容）
        body = QWidget()
        body.setObjectName('logPanelBody')
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.log_text = QTextEdit()
        self.log_text.setObjectName('logTextEdit')
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)  # 保持日志格式，禁用自动换行
        self.log_text.setFont(QFont(tokens.FONT_FAMILY_MONO, tokens.FONT_SIZE_MONO))

        self.log_search_bar = LogSearchBar(self.log_text)
        self.log_search_bar.closed.connect(self._on_log_search_closed)

        self.log_filter_bar = LogFilterBar()
        self.log_filter_bar.level_changed.connect(self.on_log_level_changed)
        self.log_filter_bar.clear_requested.connect(self.on_log_clear)
        self.log_filter_bar.export_requested.connect(self.on_log_export)

        body_layout.addWidget(self.log_filter_bar)
        body_layout.addWidget(self.log_search_bar)
        body_layout.addWidget(self.log_text, 1)

        layout.addWidget(body, 1)
        self.log_title.bind_content(body)

        self.log_panel = panel
        self.vertical_splitter.addWidget(panel)

    def setup_status_bar(self):
        """状态栏：左侧状态点 + 消息，右侧定宽分栏指标"""
        bar = self.statusBar()
        bar.setObjectName('mainStatusBar')
        bar.setSizeGripEnabled(False)
        self.status_view = StatusBarView(bar)
        self.status_view.set_state('idle')
        self.status_view.set_file(self.file_actions.current_file)

    def _connect_event_bus(self):
        """订阅核心事件，驱动日志与状态栏"""
        event_bus.execution_started.connect(lambda: self.logger.info("工作流开始执行"))
        event_bus.node_started.connect(lambda name: self.logger.info(f"执行节点: {name}"))
        event_bus.node_finished.connect(
            lambda name, result: self.logger.info(f"节点完成: {name}, 返回信息：{result}"))
        event_bus.error_occurred.connect(lambda err: self.logger.error(err))
        # 图结构变化 → 状态栏计数刷新
        event_bus.graph_changed.connect(self.refresh_graph_stats)

    def _install_zoom_watcher(self):
        """滚轮缩放后刷新状态栏缩放指示（只读取，不拦截事件）"""
        view = self.core_manager.get_view()
        if view is None:
            return
        self._graph_view = view
        view.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        """监听画布滚轮/按键/双击，延后一帧读取缩放值"""
        view = self._graph_view
        if view is not None and obj in (view, view.viewport()):
            if event.type() in (QEvent.Wheel, QEvent.KeyPress, QEvent.MouseButtonDblClick):
                QTimer.singleShot(0, self.refresh_zoom)
        return super().eventFilter(obj, event)

    # ── 状态栏刷新 ──────────────────────────────────────
    def refresh_graph_stats(self):
        """刷新节点/连线计数显示"""
        try:
            stats = self.core_manager.get_graph_stats()
            self.status_view.set_counts(stats['nodes'], stats['connections'])
        except Exception as e:
            self.logger.debug(f"刷新图统计失败: {e}")

    def showEvent(self, event):
        """首次显示后捕获视图基准缩放（高 DPI 下 QGraphicsView 基础变换 ≠ 1.0）"""
        super().showEvent(event)
        if not self._zoom_baseline_captured:
            self._zoom_baseline_captured = True
            QTimer.singleShot(0, self._capture_zoom_baseline)

    def _capture_zoom_baseline(self):
        """记录当前视图变换为 100% 基准，并刷新读数"""
        view = self._graph_view
        if view is not None:
            scale = view.transform().m11()
            if scale > 0:
                self._zoom_baseline = scale
        self.refresh_zoom()

    def refresh_zoom(self):
        """刷新缩放百分比（相对首次布局完成的基准值；NodeGraphQt 的 get_zoom 未考虑高 DPI）"""
        try:
            view = self._graph_view
            if view is None:
                return
            scale = view.transform().m11() / (self._zoom_baseline or 1.0)
            percent = int(round(scale * 100))
            if abs(scale - 1.0) < 0.02:      # 基准附近的浮点噪声吸附为整 100%
                percent = 100
            self.status_view.set_zoom(percent / 100.0)
        except Exception as e:
            self.logger.debug(f"刷新缩放失败: {e}")

    def notify_file_change(self, dirty=False):
        """文件操作完成后由 FileActions 调用，同步状态栏文件名与脏标记"""
        try:
            self.status_view.set_file(self.file_actions.current_file, dirty=dirty)
        except Exception as e:
            self.logger.debug(f"更新文件状态失败: {e}")

    def on_node_dropped(self, node_type, scene_pos):
        """节点拖拽创建后的额外处理"""
        self.logger.info(f"节点已创建: {node_type} 位置 {scene_pos}")

    # ── 视图菜单动作 ────────────────────────────────────
    def toggle_grid(self, checked):
        """网格线开关（视图菜单）"""
        self.theme_state.grid_display = bool(checked)
        self.update_grid(bool(checked))

    def update_grid(self, grid_display: bool):
        """更新节点图网格线"""
        if hasattr(self, 'node_graph_panel'):
            self.node_graph_panel.update_grid(grid_display)

    def zoom_in(self):
        """放大画布"""
        self._apply_zoom('in')

    def zoom_out(self):
        """缩小画布"""
        self._apply_zoom('out')

    def reset_zoom(self):
        """重置缩放"""
        try:
            self.core_manager.graph_manager.node_graph.reset_zoom()
            self.refresh_zoom()
        except Exception as e:
            self.logger.debug(f"重置缩放失败: {e}")

    def _apply_zoom(self, direction):
        """按档位缩放（NodeGraphQt 无 zoom_in/out，用 set_zoom(当前档位 ± 0.1)）"""
        try:
            graph = self.core_manager.graph_manager.node_graph
            step = 0.1 if direction == 'in' else -0.1
            graph.set_zoom(graph.get_zoom() + step)
            self.refresh_zoom()
        except Exception as e:
            self.logger.debug(f"缩放失败: {e}")

    def toggle_node_library(self, checked):
        """节点库面板显隐"""
        self.node_library_panel.setVisible(bool(checked))
        if self.node_library_panel.isVisible():
            self.horizontal_splitter.setSizes(
                [tokens.NODE_LIBRARY_WIDTH, WINDOW_WIDTH - tokens.NODE_LIBRARY_WIDTH])

    def toggle_log_panel(self, checked):
        """日志面板显隐"""
        self.log_panel.setVisible(bool(checked))
        if self.log_panel.isVisible():
            self.vertical_splitter.setSizes([WINDOW_HEIGHT - 220, 220])

    # ── 日志 ────────────────────────────────────────────
    def setup_logging(self):
        """设置日志记录（时间戳与级别徽章由 TextEditHandler 渲染，formatter 只给正文）"""
        handler = TextEditHandler(self.log_text, max_lines=self.theme_state.max_log_lines)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self._log_handler = handler

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        self.logger.info("=" * 60)
        self.logger.info("工作流设计器已启动")
        self.logger.info("=" * 60)
        self.logger.info("提示: 从左侧节点库拖拽节点到画布上创建工作流")
        self.logger.info("提示: 使用 F5 执行工作流，F6 验证工作流")

    # ── 日志面板命令 ────────────────────────────────────
    def on_log_level_changed(self, level):
        """级别过滤胶囊切换（logging.NOTSET 表示全部）"""
        if self._log_handler is None:
            return
        self.theme_state.log_display_filter = level
        self._log_handler.set_level_filter(level)
        label = '全部' if level == logging.NOTSET else logging.getLevelName(level)
        self.status_view.set_message(f'日志级别过滤：{label}', 2500)

    def on_log_clear(self):
        """清空日志（需确认，避免误点丢失现场）"""
        reply = QtWidgets.QMessageBox.question(
            self, '清空日志', '确定清空当前日志显示吗？',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes and self._log_handler is not None:
            self._log_handler.clear_logs()
            self.logger.info('日志已清空')

    def on_log_export(self):
        """把当前日志（含被过滤掉的）导出到文件"""
        if self._log_handler is None:
            return
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, '导出日志', 'workflow_log.txt', '文本文件 (*.txt);;所有文件 (*.*)')
        if not file_path:
            return
        try:
            lines = [f'[{time_str}] {logging.getLevelName(levelno):<8}| {msg}'
                     for time_str, levelno, msg in self._log_handler.log_records]
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            self.logger.info(f'日志已导出: {file_path}（{len(lines)} 行）')
        except Exception as e:
            self.logger.error(f'导出日志失败: {e}')

    def show_search_toolbar(self):
        """显示日志搜索栏"""
        self.log_search_bar.open_search()
        self.search_log_action.setEnabled(False)

    def _on_log_search_closed(self):
        """搜索栏关闭后恢复搜索按钮"""
        self.search_log_action.setEnabled(True)

    # ── 对话框 ──────────────────────────────────────────
    def show_settings(self):
        """显示设置对话框"""
        try:
            dialog = SettingsDialog(self.theme_state, self)
            if dialog.exec_() == QDialog.Accepted:
                self.logger.info('设置已更新')
        except Exception as e:
            self.logger.error(f'打开设置对话框失败: {str(e)}')

    def show_about(self):
        """显示关于对话框"""
        try:
            dialog = AboutDialog(self.theme_state, self)
            dialog.exec_()
        except Exception as e:
            self.logger.error(f'打开关于对话框失败: {str(e)}')

    def apply_theme(self):
        """应用主题/外观更改（画布不吃 QSS，需显式重刷）"""
        if hasattr(self, 'node_graph_panel'):
            self.node_graph_panel.update_theme(self.theme_state)
        self.logger.info(f'外观已应用: {self.theme_state.current_theme}')

    def apply_log_settings(self, capture_level=None, max_lines=None):
        """设置对话框接线：捕获级别写根记录器，最大行数写日志处理器"""
        if capture_level is not None:
            logging.getLogger().setLevel(capture_level)
            self.theme_state.log_capture_level = capture_level
        if max_lines is not None and self._log_handler is not None:
            self.theme_state.max_log_lines = max_lines
            self._log_handler.set_max_lines(max_lines)

    # ── 编辑命令（薄委托） ──────────────────────────────
    def undo(self):
        """撤销操作"""
        self.core_manager.undo()
        self.logger.info('撤销操作')

    def redo(self):
        """重做操作"""
        self.core_manager.redo()
        self.logger.info('重做操作')

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

    def closeEvent(self, event):
        """窗口关闭事件：确认后清理资源"""
        reply = QtWidgets.QMessageBox.question(
            self, '确认退出', '确定要退出应用程序吗？',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.logger.info("正在关闭主窗口，清理资源...")
            self.core_manager.cleanup()
            event.accept()
        else:
            event.ignore()
