# -*- coding: utf-8 -*-
"""
node_graph_panel.py
作者: reformLi
创建日期: 2026/4/25
最后修改: 2026/4/25
版本: 1.0.0

功能描述: 节点图画布面板——集成 NodeGraphQt 的 widget，放置到主窗口中央
"""
# ui/node_graph_panel.py
import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QMenu
from PyQt5 import QtGui

from core.events import event_bus
from ui.styles import ThemeManager
from NodeGraphQt.constants import ViewerEnum


class NodeGraphPanel(QWidget):
    def __init__(self, core_manager=None,theme_manager=None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.core_manager = core_manager
        self.graph_manager = self.core_manager.graph_manager

        self.view = self.core_manager.get_view()

        self.theme_manager = theme_manager or ThemeManager()  # 使用主题管理器
        self.update_theme(self.theme_manager)
        # 鼠标右键
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.on_view_context_menu)
        # 拖拽创建节点
        self.view.dragEnterEvent = self.view_dragEnterEvent  # 动态绑定方法
        self.view.dropEvent = self.view_dropEvent
        # 获取图形视图并设置拖拽
        self.view.setAcceptDrops(True)  # 允许 view 接收拖拽

    def get_widget(self):
        return self.core_manager.get_widget()

    def update_theme(self, theme_manager):
        """更新节点图主题"""
        try:
            # NodeGraphQt 的主题设置
            scene = self.view.scene()
            if theme_manager.current_theme == 'dark':
                # 深色主题
                scene.setBackgroundBrush(QtGui.QColor('#1e1e1e'))
            else:
                # 浅色主题
                scene.setBackgroundBrush(QtGui.QColor('#f5f5f5'))
            self.logger.info(f'节点图主题已更新为: {theme_manager.current_theme}')
        except Exception as e:
            self.logger.error(f'更新节点图主题失败: {str(e)}')

    def update_grid(self, grid_display):
        """更新节点图网格线"""
        try:
            # 显示网格线
            if grid_display:
                # # GRID_DISPLAY_LINES (2)：线状网格（最明显）
                self.graph_manager.node_graph.set_grid_mode(ViewerEnum.GRID_DISPLAY_LINES.value)
            else:
                # GRID_DISPLAY_NONE (0)：无网格
                self.graph_manager.node_graph.set_grid_mode(ViewerEnum.GRID_DISPLAY_NONE.value)
            self.logger.info(f'节点图网格线已更新: {grid_display}')
        except Exception as e:
            self.logger.error(f'更新节点图主题失败: {str(e)}')

    def on_view_context_menu(self, pos):
        """处理视图右键菜单"""
        # pos 是视图坐标（相对于视图）
        scene_pos = self.view.mapToScene(pos)
        menu = QMenu(self.view)
        nodes_info = self.core_manager.get_available_nodes()
        node_id = None
        for node in nodes_info:
            node_id = node.get("node_type")
            action = menu.addAction(node.get("name"))
            action.setData(node_id)
        action = menu.exec_(self.view.mapToGlobal(pos))
        if action:
            node_id = action.data()
            if node_id:
                try:
                    pos_tuple = (scene_pos.x(), scene_pos.y())  # 转换成元组，得到 (x, y)
                    node = self.graph_manager.node_graph.create_node(node_id,pos=pos_tuple)
                    if node:
                        self.logger.info(f"右键创建节点: {node_id} 位置 {scene_pos}")
                        event_bus.node_dropped.emit(node_id, scene_pos)
                except Exception as e:
                    self.logger.error(f"右键创建节点失败: {str(e)}")

    def view_dragEnterEvent(self, event):
        """检查拖拽数据是否包含文本，接受拖拽"""
        self.logger.error(event.mimeData().hasText())
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def view_dropEvent(self, event):
        """拖拽释放：在鼠标释放位置创建一个图形节点"""
        text = event.mimeData().text()
        if not text:
            event.ignore()
            return

        # 将视图坐标转换为场景坐标
        view_pos = event.pos()
        # scene_pos = self.mapToScene(view_pos)

        # 创建节点并添加到场景
        node_type = text
        scene_pos = self.view.mapToScene(view_pos)
        pos_tuple = (scene_pos.x(), scene_pos.y())    # 转换成元组，得到 (x, y)
        try:
            self.graph_manager.node_graph.create_node(node_type,pos=pos_tuple)
            self.logger.info(f"从拖拽创建节点: {node_type} 位置 {scene_pos}")
            # 将节点拖拽到该位置
            # node.set_pos(scene_pos.x(), scene_pos.y())
            event_bus.node_dropped.emit(node_type, scene_pos)
            event.setDropAction(Qt.CopyAction)
            event.acceptProposedAction()
        except Exception as e:
            self.logger.error(f"创建节点失败: {str(e)}")
        event.acceptProposedAction()
