# -*- coding: utf-8 -*-
"""
config.py
作者: reformLi
创建日期: 2026/4/28
最后修改: 2026/4/28
版本: 1.0.0

功能描述: 应用程序设置
"""

# -*- coding: utf-8 -*-
"""
应用程序设置
"""

# 应用程序设置
APP_NAME = '自动工作流设计器'
APP_VERSION = '1.0.0'
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

# 节点图设置
NODE_GRAPH_BACKGROUND_COLOR = (43, 43, 43)
NODE_GRAPH_GRID_COLOR = (60, 60, 60)
NODE_GRAPH_GRID_SIZE = 20

# 日志设置
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 文件设置
DEFAULT_FILE_EXTENSION = '.json'
SUPPORTED_FILE_TYPES = [
    ('JSON文件', '*.json'),
    ('所有文件', '*.*')
]

# 节点设置
NODE_TYPES = {
    'Input': {
        'name': '输入节点',
        'color': (50, 100, 150),
        'description': '数据输入节点'
    },
    'Process': {
        'name': '处理节点',
        'color': (150, 100, 50),
        'description': '数据处理节点'
    },
    'Output': {
        'name': '输出节点',
        'color': (100, 150, 50),
        'description': '数据输出节点'
    },
    'Backdrop': {
        'name': '背景节点',
        'color': (128, 128, 128),
        'description': '背景容器节点'
    }
}

# 工具栏设置
TOOLBAR_ITEMS = [
    {'name': '新建', 'icon': 'document-new', 'shortcut': 'Ctrl+N', 'action': 'new'},
    {'name': '打开', 'icon': 'document-open', 'shortcut': 'Ctrl+O', 'action': 'open'},
    {'name': '保存', 'icon': 'document-save', 'shortcut': 'Ctrl+S', 'action': 'save'},
    {'name': '清空', 'icon': 'edit-clear', 'shortcut': None, 'action': 'clear'},
    {'name': '执行', 'icon': 'media-playback-start', 'shortcut': 'F5', 'action': 'execute'}
]

# 菜单设置
MENU_ITEMS = {
    '文件': [
        {'name': '新建', 'shortcut': 'Ctrl+N', 'action': 'new'},
        {'name': '打开', 'shortcut': 'Ctrl+O', 'action': 'open'},
        {'name': '保存', 'shortcut': 'Ctrl+S', 'action': 'save'},
        {'name': '另存为', 'shortcut': 'Ctrl+Shift+S', 'action': 'save_as'},
        {'separator': True},
        {'name': '退出', 'shortcut': 'Ctrl+Q', 'action': 'exit'}
    ],
    '编辑': [
        {'name': '撤销', 'shortcut': 'Ctrl+Z', 'action': 'undo'},
        {'name': '重做', 'shortcut': 'Ctrl+Y', 'action': 'redo'},
        {'separator': True},
        {'name': '清空', 'shortcut': None, 'action': 'clear'}
    ],
    '运行': [
        {'name': '执行工作流', 'shortcut': 'F5', 'action': 'execute'},
        {'name': '验证工作流', 'shortcut': 'F6', 'action': 'validate'}
    ]
}