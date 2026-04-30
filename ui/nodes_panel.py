# -*- coding: utf-8 -*-
"""
node_library.py
作者: reformLi
创建日期: 2026/3/24
最后修改: 2026/3/24
版本: 1.0.0

功能描述: 节点库
"""
import logging

from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import (
    QWidget, QListWidget, QListWidgetItem, QLabel, QVBoxLayout,
    QHBoxLayout, QApplication, QAbstractItemView
)

from ui.styles import ThemeManager, NodeColors

class DraggableNodeItem(QWidget):
    """可拖拽的节点项"""

    def __init__(self, node_type, node_name, description, theme_manager=None, parent=None):
        super().__init__(parent)
        self.node_type = node_type
        self.node_name = node_name
        self.description = description
        self.theme_manager = theme_manager or ThemeManager()

        self._drag_start_pos = None  # 记录按下时的位置

        # 获取节点颜色和图标
        node_color = self.theme_manager.get_node_color(node_type)
        node_icon = self.theme_manager.get_node_icon(node_type)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        # 节点图标
        icon_label = QLabel(node_icon)
        icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 20px;
                background-color: {node_color};
                border-radius: 15px;
                padding: 6px;
                margin-right: 8px;
                min-width: 30px;
                min-height: 30px;
                text-align: center;
            }}
        """)

        # 节点信息
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(3)

        name_label = QLabel(node_name)
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme_manager.colors['text_primary']};
                font-weight: bold;
                font-size: 13px;
            }}
        """)

        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme_manager.colors['text_secondary']};
                font-size: 11px;
            }}
        """)

        info_layout.addWidget(name_label)
        info_layout.addWidget(desc_label)

        layout.addWidget(icon_label)
        layout.addWidget(info_widget, 1)

        # 设置整体样式
        self.setStyleSheet(f"""
            DraggableNodeItem {{
                background-color: {self.theme_manager.colors['secondary_bg']};
                border: 1px solid {self.theme_manager.colors['border']};
                border-radius: 10px;
                margin: 3px 0;
            }}
            DraggableNodeItem:hover {{
                background-color: {self.theme_manager.colors['tertiary_bg']};
                border: 1px solid {node_color};
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                margin: 2px 0;
            }}
            DraggableNodeItem:pressed {{
                background-color: {self.theme_manager.colors['button_pressed']};
                border: 1px solid {node_color};
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
            }}
        """)

class NodeLibraryWidget(QListWidget):
    """节点库部件 - 支持拖拽"""

    def __init__(self, core_manager, theme_manager=None, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.core_manager = core_manager
        self.theme_manager = theme_manager or ThemeManager()  # 使用主题管理器
        self.setDragEnabled(True)  # 允许拖动
        self.setAcceptDrops(False)  # 不接受放入，只拖出
        self.setSelectionMode(self.SingleSelection)
        self.drag_start_pos = None
        self.dragging_item = None          # 保存 QListWidgetItem
        self.dragging_widget = None  # 保存 DraggableNodeItem

        # 设置拖拽延迟，避免误操作
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setDragEnabled(True)

        self.setup_ui()

    def setup_ui(self):
        """设置用户界面"""
        self.setStyleSheet(self.theme_manager.get_stylesheet('node_library'))

        # 添加节点项
        self.add_node_items()

        self.setMinimumWidth(220)
        self.setMaximumWidth(320)
        self.setUniformItemSizes(True)  # 优化性能
        self.setSpacing(2)  # 项目间距

    def update_theme(self, theme_manager):
        """更新主题"""
        self.theme_manager = theme_manager
        self.setStyleSheet(self.theme_manager.get_stylesheet('node_library'))

        # 更新所有节点项的主题
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            if widget and isinstance(widget, DraggableNodeItem):
                widget.theme_manager = theme_manager
                # 重新设置widget样式
                node_color = theme_manager.get_node_color(widget.node_type)
                node_icon = theme_manager.get_node_icon(widget.node_type)

                # 找到图标标签并更新
                layout = widget.layout()
                if layout.count() > 0:
                    icon_label = layout.itemAt(0).widget()
                    if isinstance(icon_label, QLabel):
                        icon_label.setText(node_icon)
                        icon_label.setStyleSheet(f"""
                            QLabel {{
                                font-size: 20px;
                                background-color: {node_color};
                                border-radius: 15px;
                                padding: 6px;
                                margin-right: 8px;
                                min-width: 30px;
                                min-height: 30px;
                                text-align: center;
                            }}
                        """)

                # 重新应用整体样式
                widget.setStyleSheet(f"""
                    DraggableNodeItem {{
                        background-color: {theme_manager.colors['secondary_bg']};
                        border: 1px solid {theme_manager.colors['border']};
                        border-radius: 10px;
                        margin: 3px 0;
                    }}
                    DraggableNodeItem:hover {{
                        background-color: {theme_manager.colors['tertiary_bg']};
                        border: 1px solid {node_color};
                        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                        margin: 2px 0;
                    }}
                    DraggableNodeItem:pressed {{
                        background-color: {theme_manager.colors['button_pressed']};
                        border: 1px solid {node_color};
                        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
                    }}
                """)

    def add_node_items(self):
        """添加节点项到列表"""
        nodes_info = self.core_manager.get_available_nodes()
        # 可以添加显示名称映射（简单处理，从标识符取最后部分）
        for node in nodes_info:
            node_type = node.get('node_type')
            node_name = node.get('name')
            description = f"{node_name} 节点"  # 描述可自定义
            # 注意：我们存储的是标识符（例如 workflow.Start）
            widget = DraggableNodeItem(node_type, node_name, description, self.theme_manager, self)
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self.addItem(item)
            self.setItemWidget(item, widget)

    def mouseMoveEvent(self, event):
        if (event.buttons() == Qt.LeftButton and
                self.drag_start_pos is not None):
            # 计算移动距离是否超过系统拖拽阈值
            distance = (event.pos() - self.drag_start_pos).manhattanLength()
            if distance >= QApplication.startDragDistance():
                node_type = self.dragging_widget.node_type  # 获取属性
                node_name = self.dragging_widget.node_name
                self.logger.info(f"拖拽节点: {node_type}")

                # 创建拖拽操作
                drag = QDrag(self)
                mime_data = QMimeData()
                mime_data.setText(node_type)  # 传递节点类型
                drag.setMimeData(mime_data)

                # 设置拖拽光标样式
                drag.setDragCursor(self.style().standardPixmap(self.style().SP_DialogOkButton), Qt.CopyAction)

                # 执行拖拽（阻塞，直到拖拽结束）
                result = drag.exec_(Qt.CopyAction | Qt.MoveAction)
                self.logger.info(f"创建拖拽操作 result: {result}")

                # 拖拽结束后清除起始点
                self.drag_start_pos = None
                self.dragging_item = None
                self.dragging_widget = None
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
            self.dragging_item = self.itemAt(event.pos())   # 获取项对象
            if self.dragging_item:
                self.dragging_widget = self.itemWidget(self.dragging_item)
            else:
                self.drag_start_pos = None
                self.dragging_item = None
                self.dragging_widget = None
        else:
            # 右键或其它键：清空拖拽状态，正常处理
            self.drag_start_pos = None
            self.dragging_item = None
            self.dragging_widget = None
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # 右键释放时，重置拖拽状态
        if event.button() == Qt.RightButton:
            self.drag_start_pos = None
            self.dragging_item = None
            self.dragging_widget = None
        super().mouseReleaseEvent(event)
