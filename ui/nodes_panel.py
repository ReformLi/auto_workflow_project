# -*- coding: utf-8 -*-
"""
nodes_panel.py
功能描述: 节点库面板
         - 顶部搜索框（按名称/分类即时过滤）
         - 按分类分组、可折叠的节点条目
         - 条目 = 分类色条 + 分类色图标块 + 名称/描述
         - 按住条目拖到画布即创建节点（mime 文本仍为 node_type，与画布侧约定一致）
         见 UI_DESIGN.md §5.3
"""
import logging

from PyQt5.QtCore import Qt, QMimeData, QSize, pyqtSignal
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget
)

from ui import icons, tokens
from ui.theme import ThemeState


class DraggableNodeItem(QWidget):
    """可拖拽的节点条目"""

    drag_started = pyqtSignal(str)   # node_type

    def __init__(self, node_type, node_name, description, color, icon_name, parent=None):
        super().__init__(parent)
        self.node_type = node_type
        self.node_name = node_name
        self.description = description
        self.color = color
        self.icon_name = icon_name
        self._drag_start_pos = None

        self.setObjectName('nodeItem')
        self.setFixedHeight(tokens.NODE_ITEM_HEIGHT)
        self.setSizePolicy(self.sizePolicy().Preferred, self.sizePolicy().Fixed)
        self.setCursor(Qt.OpenHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.setSpacing(8)

        # 左侧分类色条（每条颜色不同，只能按控件级样式给出）
        bar = QFrame()
        bar.setFixedWidth(3)
        bar.setStyleSheet(f'background-color: {color}; border: none; border-radius: 1px;')
        layout.addWidget(bar)

        # 分类色图标块
        icon_label = QLabel()
        icon_label.setFixedSize(28, 28)
        icon_label.setPixmap(icons.tile_pixmap(icon_name, color, size=28, radius=6))
        layout.addWidget(icon_label)

        # 名称 + 描述
        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(1)

        name_label = QLabel(node_name)
        name_label.setObjectName('nodeName')
        desc_label = QLabel(description)
        desc_label.setObjectName('nodeDesc')

        info_layout.addWidget(name_label)
        info_layout.addWidget(desc_label)
        layout.addWidget(info, 1)

    # ── 拖拽 ────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        else:
            self._drag_start_pos = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_start_pos is not None:
            moved = (event.pos() - self._drag_start_pos).manhattanLength()
            if moved >= QApplication.startDragDistance():
                self._start_drag()
                self._drag_start_pos = None
                event.accept()
                return
        super().mouseMoveEvent(event)

    def _start_drag(self):
        """发起拖拽：mime 文本携带 node_type，与画布 dropEvent 的约定一致"""
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.node_type)
        drag.setMimeData(mime_data)
        drag.setPixmap(icons.tile_pixmap(self.icon_name, self.color, size=32))
        drag.exec_(Qt.CopyAction)
        self.drag_started.emit(self.node_type)


class NodeSection(QWidget):
    """一个分类分组：标题栏（可折叠） + 条目列表"""

    def __init__(self, title, color, icon_name, parent=None):
        super().__init__(parent)
        self.collapsed = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.header = QPushButton(self)
        self.header.setObjectName('sectionToggle')
        self.header.setCheckable(False)
        self.header.setCursor(Qt.PointingHandCursor)
        self._build_header_layout()
        layout.addWidget(self.header)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(4)
        layout.addWidget(self.body)

        self.header.clicked.connect(self.toggle)
        self._title_text = title
        self._color, self._icon_name = color, icon_name
        self._update_header(0)

    def _build_header_layout(self):
        """标题行：折叠箭头 + 分组名 + 计数（构造时即安装到 header，勿再 setLayout）"""
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(4, 4, 14, 4)
        header_layout.setSpacing(6)

        self._chevron = QLabel()
        self._chevron.setFixedWidth(12)
        self._title = QLabel()
        self._title.setObjectName('sectionTitle')
        self._count = QLabel()
        self._count.setObjectName('sectionTitle')

        header_layout.addWidget(self._chevron)
        header_layout.addWidget(self._title)
        header_layout.addStretch(1)
        header_layout.addWidget(self._count)

    def _update_header(self, count):
        """刷新标题行（箭头方向随折叠状态变化）"""
        self._count.setText(str(count))
        self._title.setText(self._title_text)
        icon_name = 'fa5s.chevron-right' if self.collapsed else 'fa5s.chevron-down'
        self._chevron.setPixmap(
            icons.icon(icon_name, color=self._color, scale=0.7).pixmap(QSize(12, 12)))

    def add_item(self, widget, color, icon_name):
        self.body_layout.addWidget(widget)
        self._color, self._icon_name = color, icon_name
        self._update_header(self.body_layout.count())

    def toggle(self):
        self.collapsed = not self.collapsed
        self.body.setVisible(not self.collapsed)
        self._update_header(self.body_layout.count())


class NodeLibraryWidget(QWidget):
    """节点库面板（搜索 + 分组 + 可拖拽条目）"""

    node_drag_started = pyqtSignal(str)

    def __init__(self, core_manager, theme_state=None, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.core_manager = core_manager
        self.theme_state = theme_state or ThemeState()

        self._sections = []      # [(NodeSection, [ (DraggableNodeItem, 搜索关键词) ])]
        self.setObjectName('nodeLibrary')
        self._build()
        self.reload_nodes()

    # ── 构建 ────────────────────────────────────────────
    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.search_box = QLineEdit()
        self.search_box.setObjectName('nodeSearchBox')
        self.search_box.setPlaceholderText('搜索节点…')
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self._apply_filter)

        search_icon = self.search_box.addAction(
            icons.icon('fa5s.search', color=tokens.DARK['text_dim']), QLineEdit.LeadingPosition)
        search_icon.setToolTip('按节点名称或分类过滤')
        layout.addWidget(self.search_box)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName('nodeScrollArea')
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName('nodeScrollContent')
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setContentsMargins(0, 0, 4, 0)
        self.content_layout.setSpacing(10)
        self.content_layout.addStretch(1)

        self.scroll_area.setWidget(container)
        layout.addWidget(self.scroll_area, 1)

        self.setMinimumWidth(tokens.NODE_LIBRARY_WIDTH)
        self.setSizePolicy(self.sizePolicy().Expanding, self.sizePolicy().Expanding)

    def reload_nodes(self):
        """按分类重建条目（数据来自 core_manager.get_available_nodes）"""
        for section, _ in self._sections:
            section.hide()          # 先隐藏：可见控件 setParent(None) 会闪现顶层窗口
            section.setParent(None)
            section.deleteLater()
        self._sections = []

        for label, entry in self._grouped_nodes():
            section = NodeSection(label, entry['color'], entry['icon'])
            items = []
            for node in entry['nodes']:
                item = DraggableNodeItem(
                    node_type=node['node_type'],
                    node_name=node['name'],
                    description=node['description'],
                    color=node['color'],
                    icon_name=node['icon'],
                    parent=self,
                )
                item.drag_started.connect(
                    lambda node_type: self.logger.info(f"拖拽节点: {node_type}"))
                section.add_item(item, entry['color'], entry['icon'])
                items.append((item, f"{node['name']} {node['category_label']} {label}".lower()))
            self._sections.append((section, items))
            # 插入到 stretch 之前，保持分组顺序
            self.content_layout.insertWidget(self.content_layout.count() - 1, section)

        self._apply_filter(self.search_box.text())

    def _grouped_nodes(self):
        """按分组（流程/控制流/自动化操作）聚合节点；条目保留各自分类色与图标"""
        buckets = {}
        for node in self.core_manager.get_available_nodes():
            style = tokens.category_style(node.get('category') or '')
            group = style['group']
            entry = buckets.setdefault(group, {
                'icon': tokens.GROUP_ICONS.get(group, 'fa5s.layer-group'),
                'color': tokens.DARK['text_2nd'],
                'category': style,
                'nodes': [],
            })
            entry['nodes'].append({
                'node_type': node['node_type'],
                'name': node['name'],
                'description': node.get('description') or f"{node['name']}节点",
                'icon': node.get('icon') or style['icon'],
                'color': style['color'],
                'category_label': style['label'],
            })

        ordered = [(group, buckets[group]) for group in tokens.GROUP_ORDER if group in buckets]
        for group, entry in buckets.items():          # 未登记分组兜底追加
            if group not in [name for name, _ in ordered]:
                ordered.append((group, entry))
        return ordered

    # ── 搜索过滤 ────────────────────────────────────────
    def _apply_filter(self, text):
        """按名称/分类过滤条目，空分组自动隐藏"""
        query = (text or '').strip().lower()
        for section, items in self._sections:
            visible = 0
            for item, keywords in items:
                match = not query or query in keywords
                item.setVisible(match)
                if match:
                    visible += 1
            section.setVisible(visible > 0)
            section._count.setText(str(visible))

    # ── 主题 ────────────────────────────────────────────
    def update_theme(self, theme_state):
        """同步界面状态（当前仅深色主题，保留接口）"""
        self.theme_state = theme_state
