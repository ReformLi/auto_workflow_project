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
    QWidget, QListWidget,
    QListWidgetItem, QLabel, QVBoxLayout, QHBoxLayout, QApplication
)

class DraggableNodeItem(QWidget):
    """可拖拽的节点项"""

    def __init__(self, node_type, node_name, description, parent=None):
        super().__init__(parent)
        self.node_type = node_type
        self.node_name = node_name

        self._drag_start_pos = None  # 记录按下时的位置

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        # 节点图标（用文本代替）
        icon_label = QLabel("⚡")
        icon_label.setStyleSheet("font-size: 16px; color: #4CAF50;")

        # 节点信息
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        name_label = QLabel(node_name)
        name_label.setStyleSheet("color: #ffffff; font-weight: bold;")

        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #cccccc; font-size: 11px;")

        info_layout.addWidget(name_label)
        info_layout.addWidget(desc_label)

        layout.addWidget(icon_label)
        layout.addWidget(info_widget, 1)

        self.setStyleSheet("""
            DraggableNodeItem {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 4px;
            }
            DraggableNodeItem:hover {
                background-color: #4a4a4a;
                border: 1px solid #666666;
            }
        """)

class NodeLibraryWidget(QListWidget):
    """节点库部件 - 支持拖拽"""

    def __init__(self, core_manager,parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.core_manager = core_manager
        self.setDragEnabled(True)  # 允许拖动
        self.setAcceptDrops(False)  # 不接受放入，只拖出
        self.setSelectionMode(self.SingleSelection)
        self.drag_start_pos = None
        self.dragging_item = None          # 保存 QListWidgetItem
        self.dragging_widget = None  # 保存 DraggableNodeItem
        self.setup_ui()

    def setup_ui(self):
        """设置用户界面"""
        # layout = QVBoxLayout(self)
        # layout.setContentsMargins(5, 5, 5, 5)
        # layout.setSpacing(5)
        #
        # # 标题
        # title_label = QLabel("节点库")
        # title_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 14px;")
        # title_label.setAlignment(Qt.AlignCenter)
        # layout.addWidget(title_label)

        # 节点列表
        # self.node_list = QListWidget()
        # # self.node_list.setDragEnabled(False)  # We handle drag at the item level
        self.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                border: none;
                outline: none;
            }
            QListWidget::item {
                margin: 2px 0;
            }
        """)

        # 添加节点项
        self.add_node_items()

        # self.addWidget(self.node_list)

        # 使用说明
        # help_text = QLabel("拖拽节点到画布上创建")
        # help_text.setStyleSheet("color: #888888; font-size: 11px;")
        # help_text.setAlignment(Qt.AlignCenter)
        # layout.addWidget(help_text)
        #
        # self.setMinimumWidth(200)

    def add_node_items(self):
        """添加节点项到列表"""
        nodes_info = self.core_manager.get_available_nodes()
        # 可以添加显示名称映射（简单处理，从标识符取最后部分）
        for node in nodes_info:
            node_type = node.get('node_type')
            node_name = node.get('name')
            description = f"{node_name} 节点"  # 描述可自定义
            # 注意：我们存储的是标识符（例如 workflow.Start）
            widget = DraggableNodeItem(node_type, node_name, description, self)
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
                self.logger.info(f"拖拽节点: {node_type}")
                # 创建拖拽操作
                drag = QDrag(self)
                mime_data = QMimeData()
                mime_data.setText(node_type)  # 传递节点类型
                drag.setMimeData(mime_data)
                # 可选：设置拖拽时的图像（如果截图有效）
                # pixmap = self.grab()
                # if not pixmap.isNull():
                #     drag.setPixmap(pixmap)
                #     drag.setHotSpot(self.drag_start_pos)
                # 执行拖拽（阻塞，直到拖拽结束）
                result = drag.exec_(Qt.CopyAction | Qt.MoveAction)
                self.logger.info(f"创建拖拽操作 result: {result}")
                # 拖拽结束后清除起始点
                self.drag_start_pos = None
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
            # 左键或其它键：清空拖拽状态，正常处理
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
