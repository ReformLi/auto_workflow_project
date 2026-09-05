# -*- coding: utf-8 -*-
"""
actions.py
功能描述: 菜单栏与工具栏的纯结构构建（不含业务逻辑，命令统一绑定到主窗口）
         图标全部来自 ui/icons（qtawesome），执行按钮语义色由 ui/qss.py 的 #objectName 选择器负责。
         见 UI_DESIGN.md §5.1 / §5.2

注意：build_menu_bar 的「运行」菜单复用工具栏创建的 QAction（状态自动同步），
     因此必须先调用 build_tool_bar，再调用 build_menu_bar。
"""
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QAction, QToolBar

from ui import icons


# ── 图标名集中管理，避免拼写漂移 ─────────────────────────────
class Icon:
    NEW = 'fa5s.file'
    OPEN = 'fa5s.folder-open'
    SAVE = 'fa5s.save'
    CLEAR = 'fa5s.trash-alt'
    START = 'fa5s.play'
    PAUSE = 'fa5s.pause'
    RESUME = 'fa5s.forward'
    STOP = 'fa5s.stop'
    VALIDATE = 'fa5s.check-double'
    SEARCH = 'fa5s.search'
    UNDO = 'fa5s.undo'
    REDO = 'fa5s.redo'
    COPY = 'fa5s.copy'
    PASTE = 'fa5s.paste'
    DELETE = 'fa5s.minus-circle'
    EXIT = 'fa5s.sign-out-alt'
    SETTINGS = 'fa5s.cog'
    ABOUT = 'fa5s.info-circle'
    GRID = 'fa5s.th'
    ZOOM_IN = 'fa5s.search-plus'
    ZOOM_OUT = 'fa5s.search-minus'
    ZOOM_RESET = 'fa5s.compress'
    PANEL_LEFT = 'fa5s.columns'
    PANEL_BOTTOM = 'fa5s.window-maximize'
    RUN = 'fa5s.play-circle'


def _action(window, text, icon_name, shortcut=None, slot=None, status_tip=None,
            checkable=False, checked=False):
    """构造 QAction 的薄封装，统一图标风格"""
    action = QAction(text, window)
    action.setIcon(icons.toolbar_icon(icon_name))
    if shortcut:
        action.setShortcut(shortcut)
    if slot:
        action.triggered.connect(slot)
    if status_tip:
        action.setStatusTip(status_tip)
    if checkable:
        action.setCheckable(True)
        action.setChecked(checked)
    return action


def build_tool_bar(window):
    """构建工具栏（单行图标按钮），执行控制按钮挂到 window 属性并打 objectName 供 QSS 着色"""
    tool_bar = QToolBar('工具栏', window)
    tool_bar.setObjectName('mainToolBar')
    tool_bar.setIconSize(QSize(18, 18))
    tool_bar.setMovable(False)
    tool_bar.setFloatable(False)
    tool_bar.setToolButtonStyle(Qt.ToolButtonIconOnly)
    window.addToolBar(tool_bar)
    window.tool_bar = tool_bar

    # ── 文件组（新建/打开/保存动作挂到 window，供菜单栏复用，避免重复快捷键） ──
    window.new_action = _action(window, '新建', Icon.NEW, 'Ctrl+N',
                                window.file_actions.new_workflow, '新建工作流 (Ctrl+N)')
    window.open_action = _action(window, '打开', Icon.OPEN, 'Ctrl+O',
                                 window.file_actions.open_workflow, '打开工作流文件 (Ctrl+O)')
    window.save_action = _action(window, '保存', Icon.SAVE, 'Ctrl+S',
                                 window.file_actions.save_workflow, '保存工作流 (Ctrl+S)')
    tool_bar.addAction(window.new_action)
    tool_bar.addAction(window.open_action)
    tool_bar.addAction(window.save_action)
    tool_bar.addSeparator()

    # ── 编辑组 ───────────────────────────────────────
    clear_action = _action(window, '清空', Icon.CLEAR, None,
                           window.file_actions.clear_workflow, '清空当前工作流')
    tool_bar.addAction(clear_action)
    tool_bar.addSeparator()

    # ── 执行控制组（按钮可用态由 ExecutionController 状态机驱动） ──
    window.start_action = _action(window, '启动', Icon.START, 'F5',
                                  window.execution.start_workflow, '启动工作流执行 (F5)')
    window.pause_action = _action(window, '暂停', Icon.PAUSE, None,
                                  window.execution.pause_workflow, '暂停工作流执行')
    window.resume_action = _action(window, '恢复', Icon.RESUME, None,
                                   window.execution.resume_workflow, '恢复工作流执行')
    window.stop_action = _action(window, '终止', Icon.STOP, None,
                                 window.execution.stop_workflow, '终止工作流执行')
    for action in (window.start_action, window.pause_action,
                   window.resume_action, window.stop_action):
        action.setEnabled(action is window.start_action)
        tool_bar.addAction(action)
    tool_bar.addSeparator()

    # ── 校验 / 搜索 ──────────────────────────────────
    window.validate_action = _action(window, '验证', Icon.VALIDATE, 'F6',
                                     window.execution.validate_workflow, '验证工作流 (F6)')
    tool_bar.addAction(window.validate_action)
    tool_bar.addSeparator()

    window.search_log_action = _action(window, '搜索日志', Icon.SEARCH, 'Ctrl+F',
                                       window.show_search_toolbar, '搜索日志 (Ctrl+F)')
    tool_bar.addAction(window.search_log_action)

    # 给执行区按钮打 objectName（QSS #id 选择器 → 绿/黄/红语义色）
    _name_tool_button(tool_bar, window.start_action, 'startAction')
    _name_tool_button(tool_bar, window.pause_action, 'pauseAction')
    _name_tool_button(tool_bar, window.resume_action, 'resumeAction')
    _name_tool_button(tool_bar, window.stop_action, 'stopAction')
    _name_tool_button(tool_bar, clear_action, 'clearAction')


def build_menu_bar(window):
    """构建菜单栏（文件/编辑/运行/视图/工具）"""
    menu_bar = window.menuBar()

    # ── 文件 ─────────────────────────────────────────
    # 新建/打开/保存复用工具栏创建的 action（避免相同快捷键歧义，状态自动同步）
    file_menu = menu_bar.addMenu('文件')
    file_menu.addAction(window.new_action)
    file_menu.addAction(window.open_action)
    file_menu.addAction(window.save_action)
    file_menu.addAction(_action(window, '另存为', Icon.SAVE, 'Ctrl+Shift+S',
                                window.file_actions.save_workflow_as, '另存为 (Ctrl+Shift+S)'))
    file_menu.addSeparator()
    file_menu.addAction(_action(window, '退出', Icon.EXIT, 'Ctrl+Q',
                                window.close, '退出程序 (Ctrl+Q)'))

    # ── 编辑 ─────────────────────────────────────────
    edit_menu = menu_bar.addMenu('编辑')
    edit_menu.addAction(_action(window, '撤销', Icon.UNDO, 'Ctrl+Z', window.undo))
    edit_menu.addAction(_action(window, '重做', Icon.REDO, 'Ctrl+Y', window.redo))
    edit_menu.addSeparator()
    edit_menu.addAction(_action(window, '复制', Icon.COPY, 'Ctrl+C', window.copy_nodes))
    edit_menu.addAction(_action(window, '粘贴', Icon.PASTE, 'Ctrl+V', window.paste_nodes))
    edit_menu.addAction(_action(window, '删除', Icon.DELETE, 'Delete', window.delete_selected))
    edit_menu.addSeparator()
    edit_menu.addAction(_action(window, '清空画布', Icon.CLEAR, None,
                                window.file_actions.clear_workflow))

    # ── 运行（复用工具栏 QAction，可用态与文案自动同步） ──
    run_menu = menu_bar.addMenu('运行')
    # 只去掉重复快捷键（F5 已由下方 start_action 占用；F6 直接复用工具栏 validate_action）
    run_menu.addAction(_action(window, '执行工作流', Icon.RUN, None,
                               window.execution.execute_workflow, '验证通过后立即执行'))
    run_menu.addAction(window.validate_action)
    run_menu.addSeparator()
    run_menu.addAction(window.start_action)
    run_menu.addAction(window.pause_action)
    run_menu.addAction(window.resume_action)
    run_menu.addAction(window.stop_action)

    # ── 视图 ─────────────────────────────────────────
    view_menu = menu_bar.addMenu('视图')
    window.grid_action = _action(window, '网格线', Icon.GRID, None, window.toggle_grid,
                                 '画布网格线显隐', checkable=True,
                                 checked=window.theme_state.grid_display)
    view_menu.addAction(window.grid_action)
    view_menu.addSeparator()
    view_menu.addAction(_action(window, '放大', Icon.ZOOM_IN, 'Ctrl++', window.zoom_in))
    view_menu.addAction(_action(window, '缩小', Icon.ZOOM_OUT, 'Ctrl+-', window.zoom_out))
    view_menu.addAction(_action(window, '重置缩放', Icon.ZOOM_RESET, 'Ctrl+0', window.reset_zoom))
    view_menu.addSeparator()
    window.node_library_action = _action(window, '节点库面板', Icon.PANEL_LEFT, None,
                                         window.toggle_node_library, '显示/隐藏节点库',
                                         checkable=True, checked=True)
    view_menu.addAction(window.node_library_action)
    window.log_panel_action = _action(window, '日志面板', Icon.PANEL_BOTTOM, 'Ctrl+L',
                                      window.toggle_log_panel, '显示/隐藏日志窗口',
                                      checkable=True, checked=True)
    view_menu.addAction(window.log_panel_action)

    # ── 工具 ─────────────────────────────────────────
    tools_menu = menu_bar.addMenu('工具')
    tools_menu.addAction(_action(window, '设置', Icon.SETTINGS, 'Ctrl+,', window.show_settings))
    tools_menu.addSeparator()
    tools_menu.addAction(_action(window, '关于', Icon.ABOUT, None, window.show_about))


def _name_tool_button(tool_bar, action, object_name):
    """给 action 对应的 QToolButton 打 objectName 并重新 polish（QSS #id 选择器需要）"""
    button = tool_bar.widgetForAction(action)
    if button is None:
        return
    button.setObjectName(object_name)
    style = button.style()
    style.unpolish(button)
    style.polish(button)
