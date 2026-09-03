# -*- coding: utf-8 -*-
"""
actions.py
功能描述: 菜单栏与工具栏的纯结构构建（不含业务逻辑，命令统一绑定到主窗口）
"""
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QAction, QToolBar


def build_menu_bar(window):
    """构建菜单栏（文件/编辑/运行/工具），命令绑定到 window 的槽方法"""
    menu_bar = window.menuBar()

    # 文件菜单
    file_menu = menu_bar.addMenu('文件')

    new_action = QAction('新建', window)
    new_action.setShortcut('Ctrl+N')
    new_action.triggered.connect(window.file_actions.new_workflow)
    file_menu.addAction(new_action)

    open_action = QAction('打开', window)
    open_action.setShortcut('Ctrl+O')
    open_action.triggered.connect(window.file_actions.open_workflow)
    file_menu.addAction(open_action)

    save_action = QAction('保存', window)
    save_action.setShortcut('Ctrl+S')
    save_action.triggered.connect(window.file_actions.save_workflow)
    file_menu.addAction(save_action)

    save_as_action = QAction('另存为', window)
    save_as_action.setShortcut('Ctrl+Shift+S')
    save_as_action.triggered.connect(window.file_actions.save_workflow_as)
    file_menu.addAction(save_as_action)

    file_menu.addSeparator()

    exit_action = QAction('退出', window)
    exit_action.setShortcut('Ctrl+Q')
    exit_action.triggered.connect(window.close)
    file_menu.addAction(exit_action)

    # 编辑菜单
    edit_menu = menu_bar.addMenu('编辑')

    undo_action = QAction('撤销', window)
    undo_action.setShortcut('Ctrl+Z')
    undo_action.triggered.connect(window.undo)
    edit_menu.addAction(undo_action)

    redo_action = QAction('重做', window)
    redo_action.setShortcut('Ctrl+Y')
    redo_action.triggered.connect(window.redo)
    edit_menu.addAction(redo_action)

    edit_menu.addSeparator()

    delete_action = QAction('删除', window)
    delete_action.setShortcut('Delete')  # 快捷键 Delete
    delete_action.triggered.connect(window.delete_selected)
    edit_menu.addAction(delete_action)

    edit_menu.addSeparator()

    copy_action = QAction('复制', window)
    copy_action.setShortcut('Ctrl+C')
    copy_action.triggered.connect(window.copy_nodes)
    edit_menu.addAction(copy_action)

    paste_action = QAction('粘贴', window)
    paste_action.setShortcut('Ctrl+V')
    paste_action.triggered.connect(window.paste_nodes)
    edit_menu.addAction(paste_action)

    edit_menu.addSeparator()

    clear_action = QAction('清空', window)
    clear_action.triggered.connect(window.file_actions.clear_workflow)
    edit_menu.addAction(clear_action)

    # 运行菜单
    run_menu = menu_bar.addMenu('运行')

    execute_action = QAction('执行工作流', window)
    execute_action.setShortcut('F5')
    execute_action.triggered.connect(window.execution.execute_workflow)
    run_menu.addAction(execute_action)

    validate_action = QAction('验证工作流', window)
    validate_action.setShortcut('F6')
    validate_action.triggered.connect(window.execution.validate_workflow)
    run_menu.addAction(validate_action)

    # 工具菜单
    tools_menu = menu_bar.addMenu('工具')

    settings_action = QAction('设置', window)
    settings_action.setShortcut('Ctrl+,')
    settings_action.triggered.connect(window.show_settings)
    tools_menu.addAction(settings_action)

    tools_menu.addSeparator()

    about_action = QAction('关于', window)
    about_action.triggered.connect(window.show_about)
    tools_menu.addAction(about_action)


def build_tool_bar(window):
    """构建工具栏，执行控制按钮作为 window 属性挂载（start/pause/resume/stop/validate/search_log）"""
    tool_bar = QToolBar('工具栏', window)
    tool_bar.setIconSize(QSize(20, 20))
    tool_bar.setMovable(False)
    tool_bar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
    window.addToolBar(tool_bar)

    # 文件操作组
    new_action = QAction('📄\n新建', window)
    new_action.setShortcut('Ctrl+N')
    new_action.triggered.connect(window.file_actions.new_workflow)
    new_action.setStatusTip('新建工作流 (Ctrl+N)')
    tool_bar.addAction(new_action)

    open_action = QAction('📂\n打开', window)
    open_action.setShortcut('Ctrl+O')
    open_action.triggered.connect(window.file_actions.open_workflow)
    open_action.setStatusTip('打开工作流文件 (Ctrl+O)')
    tool_bar.addAction(open_action)

    save_action = QAction('💾\n保存', window)
    save_action.setShortcut('Ctrl+S')
    save_action.triggered.connect(window.file_actions.save_workflow)
    save_action.setStatusTip('保存工作流 (Ctrl+S)')
    tool_bar.addAction(save_action)

    tool_bar.addSeparator()

    # 编辑操作组
    clear_action = QAction('🗑️\n清空', window)
    clear_action.triggered.connect(window.file_actions.clear_workflow)
    clear_action.setStatusTip('清空当前工作流')
    tool_bar.addAction(clear_action)

    tool_bar.addSeparator()

    # 执行控制组 - 这些按钮会根据工作流状态变化
    window.start_action = QAction('▶️\n启动', window)
    window.start_action.setShortcut('F5')
    window.start_action.triggered.connect(window.execution.start_workflow)
    window.start_action.setStatusTip('启动工作流执行 (F5)')
    tool_bar.addAction(window.start_action)

    window.pause_action = QAction('⏸️\n暂停', window)
    window.pause_action.triggered.connect(window.execution.pause_workflow)
    window.pause_action.setStatusTip('暂停工作流执行')
    window.pause_action.setEnabled(False)
    tool_bar.addAction(window.pause_action)

    window.resume_action = QAction('⏯️\n恢复', window)
    window.resume_action.triggered.connect(window.execution.resume_workflow)
    window.resume_action.setStatusTip('恢复工作流执行')
    window.resume_action.setEnabled(False)
    tool_bar.addAction(window.resume_action)

    window.stop_action = QAction('⏹️\n终止', window)
    window.stop_action.triggered.connect(window.execution.stop_workflow)
    window.stop_action.setStatusTip('终止工作流执行')
    window.stop_action.setEnabled(False)
    tool_bar.addAction(window.stop_action)

    # 验证按钮
    tool_bar.addSeparator()
    window.validate_action = QAction('✓\n验证', window)
    window.validate_action.setShortcut('F6')
    window.validate_action.triggered.connect(window.execution.validate_workflow)
    window.validate_action.setStatusTip('验证工作流 (F6)')
    tool_bar.addAction(window.validate_action)

    # 搜索日志按钮
    tool_bar.addSeparator()
    window.search_log_action = QAction('🔍\n搜索日志', window)
    window.search_log_action.setShortcut('Ctrl+F')
    window.search_log_action.triggered.connect(window.show_search_toolbar)
    window.search_log_action.setStatusTip('搜索日志 (Ctrl+F)')
    tool_bar.addAction(window.search_log_action)


