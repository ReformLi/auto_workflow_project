# -*- coding: utf-8 -*-
"""
node_graph_panel.py
功能描述: 节点图画布面板——集成 NodeGraphQt 的 widget，放置到主窗口中央
         负责画布层视觉：深色底 + 点阵网格 + 连线按来源节点分类色着色 + 两级右键菜单
         （见 UI_DESIGN.md §5.4）
"""
import logging

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QMenu

from NodeGraphQt.constants import PipeLayoutEnum, ViewerEnum
from core.events import event_bus
from ui import icons, tokens
from ui.theme import ThemeState


class NodeGraphPanel(QWidget):
    """节点图画布面板（画布配色、网格、连线着色、右键建节点）"""

    def __init__(self, core_manager=None, theme_state=None, main_window=None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.core_manager = core_manager
        self.graph_manager = self.core_manager.graph_manager

        self.view = self.core_manager.get_view()

        self.theme_state = theme_state or ThemeState()
        # 本面板不在主窗口控件树内（只有 NGQ graph widget 进了分割器），
        # self.window() 会返回自身这个游离顶层控件，因此显式持有主窗口引用。
        self._main_window = main_window

        # 画布视觉（背景 / 网格 / 连线走向）
        self.apply_canvas_theme()

        # 右键菜单
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.on_view_context_menu)

        # 拖拽创建节点
        self.view.dragEnterEvent = self.view_dragEnterEvent
        self.view.dropEvent = self.view_dropEvent
        self.view.setAcceptDrops(True)

        # 连线着色：图结构变化后去抖重刷
        self._pipe_timer = QtCore.QTimer(self)
        self._pipe_timer.setSingleShot(True)
        self._pipe_timer.setInterval(60)
        self._pipe_timer.timeout.connect(self.refresh_pipe_colors)
        event_bus.graph_changed.connect(self._pipe_timer.start)

        # 属性面板：双击 / 右键→属性 唤醒；单击选中仅在面板可见时切换内容；
        # 点击空白处隐藏（面板在主窗口右侧）
        self.graph_manager.node_graph.node_double_clicked.connect(
            self._on_node_double_clicked)
        self.graph_manager.node_graph.node_selected.connect(
            self._on_node_selected)
        self.graph_manager.node_graph.node_selection_changed.connect(
            self._on_node_selection_changed)

        # 在视图层拦截左键双击：NGQ 的 NodeItem.mouseDoubleClickEvent 遇到双击落在
        # 标题文字上时会开启就地改名编辑器（弹出 QLineEdit 抢走焦点 → 选中集被清空 →
        # 属性面板闪现即回空态）。这里自己判定命中节点并唤起属性面板，事件不再下传。
        self.view.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        """拦截画布双击：命中节点则唤起属性面板，避开 NGQ 的标题改名编辑器"""
        if obj is self.view.viewport() and \
                event.type() == QtCore.QEvent.MouseButtonDblClick and \
                event.button() == Qt.LeftButton:
            node = self._node_at(self.view.mapToScene(event.pos()))
            if node is not None:
                try:
                    has_props = bool(node.get_property_defs())
                except Exception:
                    has_props = False
                if has_props:
                    self._open_properties(node)
                return True            # 有无属性都吃掉事件，杜绝改名编辑器闪现
        return super().eventFilter(obj, event)

    def get_widget(self):
        return self.core_manager.get_widget()

    # ── 画布主题 ────────────────────────────────────────
    def apply_canvas_theme(self):
        """应用画布配色与连线走向（NodeGraphQt 画布不吃 QSS，必须走这套 API）"""
        try:
            graph = self.graph_manager.node_graph
            graph.set_background_color(*tokens.rgb(tokens.DARK['bg_canvas']))
            graph.set_grid_color(*tokens.rgb(tokens.DARK['grid_dot']))
            graph.set_pipe_style(PipeLayoutEnum.CURVED.value)
            self.update_grid(self.theme_state.grid_display)
        except Exception as e:
            self.logger.error(f'应用画布主题失败: {str(e)}')

    def update_theme(self, theme_state):
        """更新主题（主窗口 apply_theme 调用）"""
        self.theme_state = theme_state
        self.apply_canvas_theme()
        self.refresh_pipe_colors()

    def update_grid(self, grid_display):
        """
        更新节点图网格线。

        注意：不使用 ViewerEnum.GRID_DISPLAY_DOTS —— NodeGraphQt 0.6.44 的
        NodeScene._draw_dots() 里 `pen.setWidth(grid_size / 10)` 把 float 传给 int 参数，
        在绘制虚函数中会让进程直接 abort（无 Python 异常、无 stderr）。
        这里改用线状网格，配合低对比网格色 tokens.grid_dot 达到同样克制的观感。
        """
        try:
            mode = (ViewerEnum.GRID_DISPLAY_LINES.value if grid_display
                    else ViewerEnum.GRID_DISPLAY_NONE.value)
            self.graph_manager.node_graph.set_grid_mode(mode)
            self.logger.debug(f'节点图网格线已更新: {grid_display}')
        except Exception as e:
            self.logger.error(f'更新节点图网格失败: {str(e)}')

    # ── 连线着色 ────────────────────────────────────────
    def refresh_pipe_colors(self):
        """
        按「输出端所属节点」的分类色给连线着色。
        NodeGraphQt 未提供 NodeGraph 级连线配色 API，这里遍历场景中的 PipeItem，
        使用其公开的 output_port / color / style 属性完成着色；
        任何异常都只记调试日志，绝不影响连线功能。
        """
        try:
            scene = self.view.scene()
            if scene is None:
                return
            for item in scene.items():
                if type(item).__name__ != 'PipeItem':
                    continue
                color = self._pipe_color_for(item)
                item.color = color
                item.set_pipe_styling(color=color, width=2, style=item.style)
        except Exception as e:
            self.logger.debug(f'连线着色跳过: {e}')

    def _pipe_color_for(self, pipe_item):
        """取连线颜色 = 输出节点的分类色（NodeItem.color 为 (r,g,b,a) 元组属性）"""
        try:
            node_item = pipe_item.output_port.node if pipe_item.output_port else None
            color = getattr(node_item, 'color', None) if node_item else None
            if color and len(color) >= 3:
                alpha = int(round((color[3] if len(color) > 3 else 255) * 0.85))
                return int(color[0]), int(color[1]), int(color[2]), alpha
        except Exception:
            pass
        fallback = QtGui.QColor(tokens.DARK['text_2nd'])
        return fallback.red(), fallback.green(), fallback.blue(), 200

    # ── 右键菜单（节点 → 属性；空白 → 分类建节点） ─────────
    def on_view_context_menu(self, pos):
        """处理视图右键菜单：命中节点显示节点菜单（属性），否则按分类分组的二级菜单"""
        scene_pos = self.view.mapToScene(pos)
        node = self._node_at(scene_pos)
        if node is not None:
            self._show_node_menu(node, pos)
            return

        menu = QMenu(self.view)
        for label, entry in self._group_by_category(self.core_manager.get_available_nodes()):
            submenu = menu.addMenu(icons.icon(entry['icon'], color=entry['color']), label)
            for node in entry['nodes']:
                action = submenu.addAction(icons.icon(node['icon'], color=node['color']), node['name'])
                action.setData(node['node_type'])

        action = menu.exec_(self.view.mapToGlobal(pos))
        if not action:
            return
        node_type = action.data()
        if not node_type:
            return
        try:
            pos_tuple = (scene_pos.x(), scene_pos.y())
            node = self.graph_manager.node_graph.create_node(node_type, pos=pos_tuple)
            if node:
                self.logger.info(f"右键创建节点: {node_type} 位置 {scene_pos}")
                event_bus.node_dropped.emit(node_type, scene_pos)
        except Exception as e:
            self.logger.error(f"右键创建节点失败: {str(e)}")

    def _node_at(self, scene_pos):
        """
        返回场景坐标处的节点对象（未命中返回 None）。

        注意不能用 NGQ 的 _items_near 默认 20x20 矩形——它的矩形以点击点为
        右下角向左上展开（偏左上），双击节点标题（左上区域）时会漏检，
        双击事件漏给 NGQ 后就地改名编辑器弹出又随焦点消失（"闪现弹框"）。
        这里改为以点击点为中心的 6px 小矩形做命中，边缘留 3px 容差。
        """
        try:
            rect = QtCore.QRectF(scene_pos.x() - 3, scene_pos.y() - 3, 6, 6)
            items = self.view.scene().items(rect)
        except Exception:
            return None
        if not items:
            return None
        for node in self.graph_manager.node_graph.all_nodes():
            if node.view in items:
                return node
        return None

    def _show_node_menu(self, node, view_pos):
        """显示节点右键菜单（属性 / 重命名；无属性的节点只显示重命名）"""
        menu = QMenu(self.view)
        prop_action = None
        try:
            has_props = bool(node.get_property_defs())
        except Exception:
            has_props = False
        if has_props:
            prop_action = menu.addAction(
                icons.icon('fa5s.edit', color='#4c8dff'), '属性')
        rename_action = menu.addAction(
            icons.icon('fa5s.i-cursor', color='#8b949e'), '重命名')
        action = menu.exec_(self.view.mapToGlobal(view_pos))
        if action is prop_action:
            self._open_properties(node)
        elif action is rename_action:
            self._rename_node(node)

    def _rename_node(self, node):
        """重命名节点（双击已让位给属性面板，改名入口收拢到右键菜单）"""
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self.view, '重命名节点', '节点名称:', text=node.name())
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        try:
            node.set_name(name)
            self.logger.info(f'节点重命名: {name}')
        except Exception as e:
            self.logger.error(f'重命名失败: {e}')

    def _on_node_double_clicked(self, node):
        """双击节点 → 面板显示其属性（无属性的节点不触发）"""
        if node.get_property_defs():
            self._open_properties(node)

    def _host_window(self):
        """真正的主窗口（本面板不在控件树内，不能用 self.window()）"""
        if self._main_window is None:
            self.logger.warning('NodeGraphPanel 未注入主窗口引用，属性面板命令无法送达')
            return self.window()
        return self._main_window

    def _on_node_selected(self, node):
        """
        单击选中节点 → 面板可见时切换到该节点配置（不抢焦点）。
        面板隐藏时不主动唤醒——按约定只有双击 / 右键→属性才唤起面板。
        """
        fn = getattr(self._host_window(), 'show_node_properties_if_visible', None)
        if callable(fn):
            fn(node)
        else:
            self.logger.warning('主窗口缺少 show_node_properties_if_visible，属性面板未更新')

    def _on_node_selection_changed(self, deselected, selected):
        """
        选中集变化 → 同步属性面板。

        注意：NodeGraphQt 0.6.44 该信号的两个参数顺序与命名相反
        （viewer 发出的是 (当前选中id, 之前选中id)，graph 层按
        (deselected, selected) 转发），信任入参会在刚选中节点时误判为
        空选中、把面板瞬间清掉（表现为"属性闪现一下又回到空态"）。
        因此一律以 selected_nodes() 实测为准。
        """
        try:
            current = list(self.graph_manager.node_graph.selected_nodes())
        except Exception:
            current = []

        host = self._host_window()
        if current:
            fn = getattr(host, 'show_node_properties_if_visible', None)
            if callable(fn):
                fn(current[0])
            return

        focus = QtWidgets.QApplication.focusWidget()
        if isinstance(focus, QtWidgets.QLineEdit) and focus.isVisible() and \
                focus.parentWidget() is not None and \
                self.view.isAncestorOf(focus.parentWidget()):
            return                      # NGQ 标题改名中，不是真的取消选中
        fn = getattr(host, 'hide_node_properties', None)
        if callable(fn):
            fn()                        # 点击空白处 → 面板整体隐藏

    def _open_properties(self, node):
        """显式打开属性（双击/右键）：面板显示并确保可见"""
        try:
            self.logger.info(f"打开节点属性: {node.name()}")
        except Exception:
            pass
        fn = getattr(self._host_window(), 'show_node_properties', None)
        if callable(fn):
            fn(node, raise_panel=True)
        else:
            self.logger.warning('主窗口缺少 show_node_properties，属性面板未能显示')

    @staticmethod
    def _group_by_category(nodes_info):
        """把可用节点按分组聚合为 [(分组名, {'icon','color','nodes'})]，顺序跟随 tokens.GROUP_ORDER"""
        buckets = {}
        for node in nodes_info:
            style = tokens.category_style(node.get('category') or '')
            group = style['group']
            entry = buckets.setdefault(group, {
                'icon': tokens.GROUP_ICONS.get(group, 'fa5s.layer-group'),
                'color': tokens.DARK['text_2nd'],
                'nodes': [],
            })
            entry['nodes'].append({
                'node_type': node['node_type'],
                'name': node['name'],
                'icon': node.get('icon') or style['icon'],
                'color': style['color'],
            })

        ordered = [(group, buckets[group]) for group in tokens.GROUP_ORDER if group in buckets]
        for group, entry in buckets.items():          # 未登记分组兜底追加
            if group not in [name for name, _ in ordered]:
                ordered.append((group, entry))
        return ordered

    # ── 拖拽创建 ────────────────────────────────────────
    def view_dragEnterEvent(self, event):
        """检查拖拽数据是否包含文本，接受拖拽"""
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

        node_type = text
        scene_pos = self.view.mapToScene(event.pos())
        pos_tuple = (scene_pos.x(), scene_pos.y())
        try:
            self.graph_manager.node_graph.create_node(node_type, pos=pos_tuple)
            self.logger.info(f"从拖拽创建节点: {node_type} 位置 {scene_pos}")
            event_bus.node_dropped.emit(node_type, scene_pos)
            event.setDropAction(Qt.CopyAction)
        except Exception as e:
            self.logger.error(f"创建节点失败: {str(e)}")
        event.acceptProposedAction()
