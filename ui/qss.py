# -*- coding: utf-8 -*-
"""
qss.py
功能描述: 全局唯一样式表入口 —— build_qss() 返回一整份 QSS 字符串，
         由 app/main.py 一次性 QApplication.setStyleSheet() 应用。
         组件不再各自 setStyleSheet（见 UI_DESIGN.md §6）。
"""

from PyQt5.QtCore import QCoreApplication

from ui import tokens


def build_qss(colors: dict = None) -> str:
    """构建全局样式表；colors 默认取 tokens.DARK"""
    C = colors or tokens.DARK

    BG_CANVAS = C['bg_canvas']
    BG_WINDOW = C['bg_window']
    BG_PANEL = C['bg_panel']
    BG_ELEV = C['bg_elevated']
    BG_HOVER = C['bg_hover']
    BG_ACTIVE = C['bg_active']
    BORDER = C['border']
    BORDER_S = C['border_strong']
    TEXT = C['text']
    TEXT2 = C['text_2nd']
    TEXTD = C['text_dim']
    ACCENT = C['accent']
    ACCENT_H = C['accent_hover']
    ACCENT_P = C['accent_press']
    SELECT = C['selection']
    SUCCESS = C['success']
    WARNING = C['warning']
    ERROR = C['error']
    INFO = C['info']
    FONT = tokens.FONT_FAMILY_UI
    MONO = tokens.FONT_FAMILY_MONO

    return f"""
/* ══════════════ 基础 ══════════════ */
QWidget {{
    font-family: "{FONT}", "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: {tokens.FONT_SIZE_UI}pt;
    color: {TEXT};
    background-color: transparent;
}}
QMainWindow, QDialog {{
    background-color: {BG_WINDOW};
}}
QLabel {{
    color: {TEXT};
    background-color: transparent;
}}
QLabel[role="secondary"] {{
    color: {TEXT2};
}}
QLabel[role="dim"] {{
    color: {TEXTD};
}}

/* ══════════════ 菜单栏 ══════════════ */
QMenuBar {{
    background-color: {BG_PANEL};
    color: {TEXT2};
    border-bottom: 1px solid {BORDER};
    padding: 2px 6px;
    spacing: 2px;
    height: 26px;
}}
QMenuBar::item {{
    background-color: transparent;
    padding: 4px 10px;
    border-radius: {tokens.RADIUS_SM}px;
    color: {TEXT2};
}}
QMenuBar::item:selected {{
    background-color: {BG_HOVER};
    color: {TEXT};
}}
QMenuBar::item:pressed {{
    background-color: {BG_ACTIVE};
    color: {TEXT};
}}

/* ══════════════ 弹出菜单 ══════════════ */
QMenu {{
    background-color: {BG_ELEV};
    border: 1px solid {BORDER_S};
    border-radius: {tokens.RADIUS_MD}px;
    padding: 4px;
}}
QMenu::item {{
    background-color: transparent;
    color: {TEXT};
    padding: 6px 28px 6px 10px;
    border-radius: {tokens.RADIUS_SM}px;
}}
QMenu::item:selected {{
    background-color: {BG_HOVER};
}}
QMenu::item:disabled {{
    color: {TEXTD};
}}
QMenu::separator {{
    height: 1px;
    background-color: {BORDER};
    margin: 4px 8px;
}}
QMenu::icon {{
    padding-left: 4px;
}}
QMenu::right-arrow {{
    width: 0; height: 0;
    border-left: 4px solid {TEXT2};
    border-top: 4px transparent;
    border-bottom: 4px transparent;
    margin-right: 8px;
}}

/* ══════════════ 工具栏 ══════════════ */
QToolBar {{
    background-color: {BG_PANEL};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 4px 8px;
    spacing: 4px;
}}
QToolBar::separator {{
    background-color: {BORDER};
    width: 1px;
    margin: 5px 6px;
}}
QToolBar::handle {{
    background-color: transparent;
    width: 4px;
}}
QToolButton {{
    background-color: transparent;
    color: {TEXT2};
    border: 1px solid transparent;
    border-radius: {tokens.RADIUS_SM}px;
    padding: 5px 9px;
    min-height: {tokens.TOOLBAR_HEIGHT - 12}px;
}}
QToolButton:hover {{
    background-color: {BG_HOVER};
    border-color: {BORDER};
    color: {TEXT};
}}
QToolButton:pressed, QToolButton:checked {{
    background-color: {BG_ACTIVE};
    border-color: {BORDER_S};
    color: {TEXT};
}}
QToolButton:disabled {{
    color: {TEXTD};
    background-color: transparent;
    border-color: transparent;
}}
QToolButton::menu-indicator {{
    image: none;
    width: 0;
}}
/* 执行区主按钮：启动=绿、暂停=黄、终止=红（按 objectName 着色） */
QToolButton#startAction {{
    background-color: {tokens.rgba(SUCCESS, 0.16)};
    border: 1px solid {tokens.rgba(SUCCESS, 0.55)};
    color: {SUCCESS};
    font-weight: bold;
}}
QToolButton#startAction:hover {{
    background-color: {tokens.rgba(SUCCESS, 0.26)};
    border-color: {SUCCESS};
}}
QToolButton#startAction:disabled {{
    background-color: transparent;
    border-color: {BORDER};
    color: {TEXTD};
    font-weight: normal;
}}
QToolButton#pauseAction {{
    color: {WARNING};
}}
QToolButton#pauseAction:disabled {{ color: {TEXTD}; }}
QToolButton#resumeAction {{
    color: {SUCCESS};
}}
QToolButton#resumeAction:disabled {{ color: {TEXTD}; }}
QToolButton#stopAction {{
    color: {ERROR};
}}
QToolButton#stopAction:disabled {{ color: {TEXTD}; }}

/* ══════════════ Dock 面板 ══════════════ */
QDockWidget {{
    background-color: {BG_WINDOW};
    border: none;
    color: {TEXT2};
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}}
QDockWidget::title {{
    background-color: {BG_PANEL};
    padding: 5px 8px;
    border-bottom: 1px solid {BORDER};
    text-align: left;
    color: {TEXT2};
    font-size: {tokens.FONT_SIZE_UI}pt;
}}
/* 自定义标题栏（ui/title_bar.py） */
QWidget#dockTitleBar {{
    background-color: {BG_PANEL};
    border-bottom: 1px solid {BORDER};
}}
QLabel#dockTitleText {{
    color: {TEXT2};
    font-size: {tokens.FONT_SIZE_UI}pt;
    background-color: transparent;
}}
QPushButton#dockTitleButton {{
    background-color: transparent;
    border: none;
    border-radius: {tokens.RADIUS_SM}px;
    padding: 2px;
    margin: 0;
}}
QPushButton#dockTitleButton:hover {{
    background-color: {BG_HOVER};
}}

/* ══════════════ 状态栏 ══════════════ */
QStatusBar {{
    background-color: {BG_PANEL};
    border-top: 1px solid {BORDER};
    color: {TEXT2};
    min-height: {tokens.STATUSBAR_HEIGHT}px;
    font-size: {tokens.FONT_SIZE_UI - 1}pt;
}}
QStatusBar::item {{
    border: none;
    background: transparent;
}}
QStatusBar QLabel {{
    color: {TEXT2};
    font-size: {tokens.FONT_SIZE_UI - 1}pt;
    background-color: transparent;
    padding: 0 4px;
}}
QLabel#statusValue {{
    color: {TEXT};
}}
QLabel#statusSep {{
    color: {BORDER_S};
}}

/* ══════════════ 输入控件 ══════════════ */
QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {BG_ELEV};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {tokens.RADIUS_SM}px;
    padding: 5px 8px;
    selection-background-color: {SELECT};
    selection-color: {TEXT};
}}
QLineEdit:hover, QSpinBox:hover {{
    border-color: {BORDER_S};
}}
QLineEdit:focus, QSpinBox:focus {{
    border-color: {ACCENT};
}}
QLineEdit:disabled {{
    color: {TEXTD};
    background-color: {BG_PANEL};
}}
QLineEdit[role="search"] {{
    padding-left: 26px;
    border-radius: {tokens.RADIUS_SM}px;
}}

QComboBox {{
    background-color: {BG_ELEV};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {tokens.RADIUS_SM}px;
    padding: 4px 8px;
    min-width: 110px;
}}
QComboBox:hover {{
    border-color: {BORDER_S};
}}
QComboBox:focus {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_ELEV};
    color: {TEXT};
    border: 1px solid {BORDER_S};
    border-radius: {tokens.RADIUS_SM}px;
    padding: 4px;
    selection-background-color: {BG_HOVER};
    selection-color: {TEXT};
    outline: none;
}}

QCheckBox, QRadioButton {{
    background-color: transparent;
    color: {TEXT};
    spacing: 6px;
    padding: 2px 0;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 14px;
    height: 14px;
}}
QCheckBox::indicator {{
    border: 1px solid {BORDER_S};
    border-radius: 3px;
    background-color: {BG_ELEV};
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}
QRadioButton::indicator {{
    border: 1px solid {BORDER_S};
    border-radius: 7px;
    background-color: {BG_ELEV};
}}
QRadioButton::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

/* ══════════════ 按钮 ══════════════ */
QPushButton {{
    background-color: {BG_ELEV};
    color: {TEXT};
    border: 1px solid {BORDER_S};
    border-radius: {tokens.RADIUS_SM}px;
    padding: 6px 14px;
    min-width: 64px;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background-color: {BG_ACTIVE};
}}
QPushButton:disabled {{
    background-color: {BG_PANEL};
    color: {TEXTD};
    border-color: {BORDER};
}}
QPushButton[kind="primary"] {{
    background-color: {ACCENT};
    color: #ffffff;
    border: none;
    font-weight: bold;
}}
QPushButton[kind="primary"]:hover {{
    background-color: {ACCENT_H};
}}
QPushButton[kind="primary"]:pressed {{
    background-color: {ACCENT_P};
}}
QPushButton[kind="danger"] {{
    color: {ERROR};
    border-color: {tokens.rgba(ERROR, 0.5)};
}}
QPushButton[kind="danger"]:hover {{
    background-color: {tokens.rgba(ERROR, 0.15)};
}}
QPushButton[kind="flat"] {{
    background-color: transparent;
    border-color: transparent;
    color: {TEXT2};
}}
QPushButton[kind="flat"]:hover {{
    background-color: {BG_HOVER};
    color: {TEXT};
}}

/* ══════════════ 文本区 / 日志 ══════════════ */
QTextEdit, QPlainTextEdit, QTextBrowser {{
    background-color: {BG_CANVAS};
    color: {TEXT};
    border: none;
    padding: 6px 8px;
    font-family: "{MONO}", "Courier New", monospace;
    selection-background-color: {SELECT};
    selection-color: {TEXT};
}}
QTextEdit:focus, QPlainTextEdit:focus {{
    border: none;
}}

/* ══════════════ 列表 / 树 ══════════════ */
QListView, QTreeView, QListWidget, QTreeWidget, QListView QAbstractItemView {{
    background-color: {BG_WINDOW};
    color: {TEXT};
    border: none;
    outline: none;
    padding: 4px;
}}
QListView::item, QTreeView::item {{
    color: {TEXT};
    background-color: transparent;
    border-radius: {tokens.RADIUS_SM}px;
    margin: 1px 0;
}}
QListView::item:hover, QTreeView::item:hover {{
    background-color: {BG_HOVER};
}}
QListView::item:selected, QTreeView::item:selected {{
    background-color: {SELECT};
    color: {TEXT};
}}
QTreeView::branch {{
    background-color: transparent;
}}
QHeaderView::section {{
    background-color: {BG_PANEL};
    color: {TEXT2};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 4px 6px;
}}

/* 节点库条目（ui/nodes_panel.py 中的 NodeItemWidget） */
QWidget#nodeItem {{
    background-color: {BG_ELEV};
    border: 1px solid {BORDER};
    border-radius: {tokens.RADIUS_MD}px;
}}
QWidget#nodeItem:hover {{
    background-color: {BG_HOVER};
    border-color: {BORDER_S};
}}
QWidget#nodeItem:pressed {{
    background-color: {BG_ACTIVE};
}}
QLabel#nodeName {{
    color: {TEXT};
    font-size: {tokens.FONT_SIZE_UI + 1}px;
    font-weight: bold;
    background-color: transparent;
    border: none;
}}
QLabel#nodeDesc {{
    color: {TEXT2};
    font-size: {tokens.FONT_SIZE_UI - 1}px;
    background-color: transparent;
    border: none;
}}
/* 分组标题 */
QWidget#sectionHeader {{
    background-color: transparent;
    border: none;
}}
QLabel#sectionTitle {{
    color: {TEXT2};
    font-size: {tokens.FONT_SIZE_UI}pt;
    font-weight: bold;
    background-color: transparent;
    border: none;
}}
QPushButton#sectionToggle {{
    background-color: transparent;
    border: none;
    padding: 2px;
}}
QPushButton#sectionToggle:hover {{
    background-color: {BG_HOVER};
    border-radius: {tokens.RADIUS_SM}px;
}}

/* ══════════════ 选项卡 ══════════════ */
QTabWidget::pane {{
    background-color: {BG_WINDOW};
    border: 1px solid {BORDER};
    border-radius: {tokens.RADIUS_MD}px;
    top: -1px;
}}
QTabBar::tab {{
    background-color: transparent;
    color: {TEXT2};
    border: 1px solid transparent;
    border-bottom: 2px solid transparent;
    padding: 6px 14px;
    margin-right: 2px;
}}
QTabBar::tab:hover {{
    color: {TEXT};
    background-color: {BG_HOVER};
    border-top-left-radius: {tokens.RADIUS_SM}px;
    border-top-right-radius: {tokens.RADIUS_SM}px;
}}
QTabBar::tab:selected {{
    color: {TEXT};
    border-bottom: 2px solid {ACCENT};
}}

/* ══════════════ 分组框 ══════════════ */
QGroupBox {{
    background-color: transparent;
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {tokens.RADIUS_MD}px;
    margin-top: 10px;
    padding: 10px 8px 8px 8px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
    color: {TEXT2};
}}

/* ══════════════ 分割器 ══════════════ */
QSplitter::handle {{
    background-color: {BORDER};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}
QSplitter::handle:hover {{
    background-color: {ACCENT};
}}

/* ══════════════ 滚动条 ══════════════ */
QScrollBar:vertical {{
    background-color: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background-color: {BG_ACTIVE};
    min-height: 28px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {BORDER_S};
}}
QScrollBar:horizontal {{
    background-color: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background-color: {BG_ACTIVE};
    min-width: 28px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {BORDER_S};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0; height: 0;
    background: none;
    border: none;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: none;
}}
QAbstractScrollArea::corner {{
    background-color: transparent;
    border: none;
}}

/* ══════════════ 其它 ══════════════ */
QGraphicsView {{
    background-color: {BG_CANVAS};
    border: none;
}}
QToolTip {{
    background-color: {BG_ELEV};
    color: {TEXT};
    border: 1px solid {BORDER_S};
    border-radius: {tokens.RADIUS_SM}px;
    padding: 4px 8px;
}}
QMessageBox {{
    background-color: {BG_WINDOW};
}}
QMessageBox QLabel {{
    color: {TEXT};
    background-color: transparent;
}}
QProgressBar {{
    background-color: {BG_ELEV};
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 3px;
}}
QSizeGrip {{
    background-color: transparent;
}}
"""


def set_kind(widget, kind: str):
    """
    给按钮打语义标记并重新应用样式，配合 QSS 的 [kind="..."] 选择器。
    例：set_kind(btn, 'primary')
    """
    widget.setProperty('kind', kind)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


def apply_font(app: QCoreApplication):
    """全局字体（一次设置，所有控件继承）"""
    from PyQt5.QtGui import QFont
    font = QFont(tokens.FONT_FAMILY_UI, tokens.FONT_SIZE_UI)
    font.setHintingPreference(QFont.PreferFullHinting)
    app.setFont(font)
