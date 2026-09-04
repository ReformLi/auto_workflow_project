# -*- coding: utf-8 -*-
"""
tokens.py
功能描述: 设计令牌（Design Tokens）——全局唯一的色值/字体/间距来源
         所有 QSS、qtawesome 图标着色、NodeGraphQt 画布配色都必须从这里取值，
         禁止在其它文件中出现硬编码色值。
参见: UI_DESIGN.md §3
"""

# ─────────────────────────────────────────────────────────────
# 深色主题色板（唯一事实来源）
# ─────────────────────────────────────────────────────────────
DARK = {
    # 背景层级（由深到浅，画布最深、弹层最高）
    'bg_canvas': '#16181d',      # 节点图画布
    'bg_window': '#1e2127',      # 主窗口 / 对话框底
    'bg_panel': '#23262e',       # 菜单栏 / 工具栏 / 面板 / 状态栏
    'bg_elevated': '#2a2e37',    # 输入框 / 悬浮菜单 / 卡片
    'bg_hover': '#31353f',       # hover 态
    'bg_active': '#3a3f4b',      # pressed / 选中底色

    # 边框
    'border': '#333844',
    'border_strong': '#454b58',

    # 文字
    'text': '#e8eaed',           # 主文字
    'text_2nd': '#a8b0bb',       # 次要文字 / 图标默认色
    'text_dim': '#6b7280',       # 占位 / 禁用 / 时间戳

    # 强调色
    'accent': '#4c8dff',
    'accent_hover': '#6ba2ff',
    'accent_press': '#3a6fd0',
    'selection': 'rgba(76, 141, 255, 0.25)',

    # 语义色
    'success': '#3fb950',
    'warning': '#d29922',
    'error': '#f85149',
    'critical': '#f85149',
    'info': '#58a6ff',

    # 画布网格
    'grid_dot': '#262a31',

    # 日志搜索高亮（深浅底都可读）
    'search_highlight': '#d29922',
    'search_text': '#16181d',
}

# ─────────────────────────────────────────────────────────────
# 字体
# ─────────────────────────────────────────────────────────────
FONT_FAMILY_UI = 'Microsoft YaHei UI'
FONT_SIZE_UI = 9
FONT_FAMILY_MONO = 'Consolas'
FONT_SIZE_MONO = 9

# ─────────────────────────────────────────────────────────────
# 间距与尺寸（基数 4px）
# ─────────────────────────────────────────────────────────────
SPACING = 4
RADIUS_SM = 4
RADIUS_MD = 6
TOOLBAR_HEIGHT = 36
STATUSBAR_HEIGHT = 26
DOCK_TITLE_HEIGHT = 28
NODE_LIBRARY_WIDTH = 240
NODE_ITEM_HEIGHT = 52

# ─────────────────────────────────────────────────────────────
# 节点分类（颜色即语义）：用于节点头色条、节点库色条与图标 tint
# 顺序即节点库中的分组顺序
# 具体节点归属哪个分类、用哪个图标，由 nodes/*.py 的
# NODE_CATEGORY / NODE_ICON 类属性声明（与节点定义同处，避免两处事实来源）
# ─────────────────────────────────────────────────────────────
NODE_CATEGORIES = {
    '开始':     {'label': '开始',     'group': '流程',      'color': '#3fb950', 'icon': 'fa5s.play-circle'},
    '结束':     {'label': '结束',     'group': '流程',      'color': '#f85149', 'icon': 'fa5s.stop-circle'},
    '条件判断': {'label': '条件判断', 'group': '控制流',    'color': '#d29922', 'icon': 'fa5s.code-branch'},
    '循环':     {'label': '循环',     'group': '控制流',    'color': '#a371f7', 'icon': 'fa5s.sync'},
    '等待':     {'label': '等待',     'group': '控制流',    'color': '#8b949e', 'icon': 'fa5s.clock'},
    '输入操作': {'label': '输入操作', 'group': '自动化操作', 'color': '#58a6ff', 'icon': 'fa5s.mouse-pointer'},
    '窗口操作': {'label': '窗口操作', 'group': '自动化操作', 'color': '#39c5cf', 'icon': 'fa5s.window-restore'},
    '图像识别': {'label': '图像识别', 'group': '自动化操作', 'color': '#db61a2', 'icon': 'fa5s.image'},
}

# 节点库分组顺序
GROUP_ORDER = ['流程', '控制流', '自动化操作']

# 分组标题图标（分组内含多个分类，标题用中性色 + 分组图标）
GROUP_ICONS = {
    '流程': 'fa5s.play-circle',
    '控制流': 'fa5s.sitemap',
    '自动化操作': 'fa5s.robot',
}

# 未知分类的兜底样式
NODE_STYLE_DEFAULT = {'label': '其它', 'group': '其它', 'color': '#8b949e', 'icon': 'fa5s.cube'}


def category_style(category: str) -> dict:
    """分类完整样式声明（未知分类回落兜底）"""
    return NODE_CATEGORIES.get(category, NODE_STYLE_DEFAULT)


def category_color(category: str) -> str:
    """分类主色（未知分类回落兜底色）"""
    return category_style(category)['color']


def category_icon(category: str) -> str:
    """分类默认图标（节点未声明 NODE_ICON 时使用）"""
    return category_style(category)['icon']


def category_label(category: str) -> str:
    """分类显示名"""
    return category_style(category)['label']


def category_group(category: str) -> str:
    """分类所属分组（节点库用）"""
    return category_style(category)['group']


def grouped_categories():
    """按 GROUP_ORDER 返回 [(分组名, [(分类键, 样式), ...]), ...]，未列出的分组追加到末尾"""
    buckets = {}
    for key, style in NODE_CATEGORIES.items():
        buckets.setdefault(style['group'], []).append((key, style))

    ordered = [(group, buckets.pop(group)) for group in GROUP_ORDER if group in buckets]
    ordered.extend(buckets.items())
    return ordered


def rgba(hex_color: str, alpha: float) -> str:
    """'#rrggbb' + alpha → 'rgba(r, g, b, a)'，供 QSS 半透明底使用"""
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f'rgba({r}, {g}, {b}, {alpha})'


def rgb(hex_color: str) -> tuple:
    """'#rrggbb' → (r, g, b)，供 NodeGraphQt set_*_color 使用"""
    hex_color = hex_color.lstrip('#')
    return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
