# -*- coding: utf-8 -*-
"""
styles.py
UI样式定义文件
包含所有UI组件的样式定义和主题配置
"""

from PyQt5.QtGui import QColor


class ThemeColors:
    """主题颜色配置"""

    # 深色主题
    DARK = {
        # 主色调
        'primary_bg': '#1e1e1e',
        'secondary_bg': '#252526',
        'tertiary_bg': '#2d2d30',

        # 文本颜色
        'text_primary': '#ffffff',
        'text_secondary': '#cccccc',
        'text_tertiary': '#888888',

        # 边框和分割线
        'border': '#3e3e42',
        'border_light': '#555555',
        'border_hover': '#666666',

        # 按钮颜色
        'button_bg': '#3c3c3c',
        'button_hover': '#4c4c4c',
        'button_pressed': '#2a2a2a',
        'button_disabled': '#2a2a2a',

        # 特殊颜色
        'accent': '#007acc',
        'accent_hover': '#005a9e',
        'success': '#4CAF50',
        'warning': '#ffcc00',
        'error': '#ff6b6b',
        'critical': '#ff0000',

        # 搜索高亮
        'search_highlight': '#ffa502',
        'search_text': '#000000',

        # 日志背景
        'log_bg': '#0c0c0c',
    }

    # 浅色主题
    LIGHT = {
        # 主色调
        'primary_bg': '#f0f2f5',
        'secondary_bg': '#ffffff',
        'tertiary_bg': '#e8e8e8',

        # 文本颜色
        'text_primary': '#000000',
        'text_secondary': '#333333',
        'text_tertiary': '#666666',

        # 边框和分割线
        'border': '#cccccc',
        'border_light': '#dddddd',
        'border_hover': '#999999',

        # 按钮颜色
        'button_bg': '#e0e0e0',
        'button_hover': '#d0d0d0',
        'button_pressed': '#c0c0c0',
        'button_disabled': '#f0f0f0',

        # 特殊颜色
        'accent': '#0066cc',
        'accent_hover': '#0052a3',
        'success': '#28a745',
        'warning': '#ffc107',
        'error': '#dc3545',
        'critical': '#dc3545',

        # 搜索高亮
        'search_highlight': '#fff3cd',
        'search_text': '#856404',

        # 日志背景
        'log_bg': '#f0f2f5',
    }


class NodeColors:
    """节点颜色配置"""

    NODE_COLORS = {
        'Start': '#00ff88',      # 亮绿色
        'End': '#ff4757',        # 亮红色
        'Process': '#3742fa',    # 蓝色
        'Condition': '#ffa502',  # 橙色
        'Loop': '#a55eea',       # 紫色
        'File': '#26de81',       # 绿色
        'Network': '#2d98da',    # 天蓝色
        'Database': '#45aaf2',   # 浅蓝色
        'default': '#778ca3',    # 默认颜色
    }

    NODE_ICONS = {
        'Start': '🚀',
        'End': '🎯',
        'Process': '⚙️',
        'Condition': '❓',
        'Loop': '🔄',
        'File': '📄',
        'Network': '🌐',
        'Database': '🗄️',
        'default': '⚡',
    }


class StylesheetGenerator:
    """样式表生成器"""

    @staticmethod
    def generate_main_window_stylesheet(colors):
        """生成主窗口样式表"""
        return f"""
            QMainWindow {{
                background-color: {colors['primary_bg']};
            }}
            QMenuBar {{
                background-color: {colors['tertiary_bg']};
                color: {colors['text_primary']};
                border-bottom: 1px solid {colors['border']};
                padding: 4px;
            }}
            QMenuBar::item {{
                background-color: transparent;
                color: {colors['text_primary']};
                padding: 6px 10px;
                margin: 2px;
                border-radius: 4px;
            }}
            QMenuBar::item:selected {{
                background-color: {colors['border']};
            }}
            QMenu {{
                background-color: {colors['tertiary_bg']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 20px;
                border-radius: 4px;
                margin: 2px 4px;
            }}
            QMenu::item:selected {{
                background-color: {colors['accent']};
            }}
            QToolBar {{
                background-color: {colors['tertiary_bg']};
                border: none;
                border-bottom: 1px solid {colors['border']};
                padding: 4px;
                spacing: 6px;
            }}
            QToolButton {{
                background-color: {colors['button_bg']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_light']};
                border-radius: 6px;
                padding: 8px 12px;
                margin: 2px;
                font-weight: 500;
            }}
            QToolButton:hover {{
                background-color: {colors['button_hover']};
                border: 1px solid {colors['border_hover']};
            }}
            QToolButton:pressed {{
                background-color: {colors['button_pressed']};
                border: 1px solid {colors['border_light']};
            }}
            QToolButton:disabled {{
                background-color: {colors['button_disabled']};
                color: {colors['text_tertiary']};
                border: 1px solid {colors['border']};
            }}
            QDockWidget {{
                color: {colors['text_primary']};
                background-color: {colors['secondary_bg']};
                border: none;
                titlebar-close-icon: url(resources/icons/close.png);
                titlebar-normal-icon: url(resources/icons/float.png);
            }}
            QDockWidget::title {{
                background-color: {colors['tertiary_bg']};
                color: {colors['text_primary']};
                padding: 8px;
                border-bottom: 1px solid {colors['border']};
                text-align: center;
                font-weight: bold;
                font-size: 14px;
            }}
            QTextEdit {{
                background-color: {colors['log_bg']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 8px;
                selection-background-color: {colors['accent']};
                selection-color: {colors['text_primary']};
            }}
            QSplitter::handle {{
                background-color: {colors['border']};
                width: 1px;
            }}
            QSplitter::handle:hover {{
                background-color: {colors['accent']};
            }}
            QStatusBar {{
                background-color: {colors['accent']};
                color: {colors['text_primary']};
                padding: 4px;
            }}
            QMessageBox {{
                background-color: {colors['tertiary_bg']};
            }}
            QMessageBox QLabel {{
                color: {colors['text_primary']};
            }}
            QMessageBox QPushButton {{
                background-color: {colors['accent']};
                color: {colors['text_primary']};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {colors['accent_hover']};
            }}
        """

    @staticmethod
    def generate_node_library_stylesheet(colors):
        """生成节点库样式表"""
        return f"""
            NodeLibraryWidget {{
                background-color: {colors['primary_bg']};
                border: none;
            }}
            QListWidget {{
                background-color: {colors['primary_bg']};
                border: none;
                outline: none;
                padding: 8px;
            }}
            QListWidget::item {{
                color: {colors['text_primary']};
                margin: 3px 0;
                border-radius: 12px;
            }}
            QListWidget::item:selected {{
                background-color: rgba(0, 122, 204, 0.2);
            }}
            QListWidget::item:hover {{
                background-color: rgba(255, 255, 255, 0.03);
            }}
            QScrollBar:vertical {{
                background-color: {colors['log_bg']};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {colors['button_bg']};
                min-height: 30px;
                border-radius: 5px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {colors['button_hover']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """

    @staticmethod
    def generate_dock_widget_stylesheet(colors):
        """生成DockWidget样式表"""
        return f"""
            QDockWidget {{
                color: {colors['text_primary']};
                background-color: {colors['secondary_bg']};
                border: none;
                titlebar-close-icon: url(resources/icons/close.png);
                titlebar-normal-icon: url(resources/icons/float.png);
            }}
            QDockWidget::title {{
                background-color: {colors['tertiary_bg']};
                color: {colors['text_primary']};
                padding: 8px;
                border-bottom: 1px solid {colors['border']};
                text-align: center;
                font-weight: bold;
                font-size: 14px;
            }}
        """

    @staticmethod
    def generate_search_toolbar_stylesheet(colors):
        """生成搜索工具栏样式表"""
        return f"""
            QToolBar {{
                background-color: {colors['tertiary_bg']};
                border-bottom: 1px solid {colors['border']};
                padding: 4px;
                spacing: 6px;
            }}
            QLineEdit {{
                background-color: {colors['primary_bg']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 200px;
            }}
            QLabel {{
                color: {colors['text_secondary']};
                font-size: 11px;
            }}
            QToolButton {{
                background-color: {colors['button_bg']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_light']};
                border-radius: 4px;
                padding: 4px;
                min-width: 30px;
            }}
            QToolButton:hover {{
                background-color: {colors['button_hover']};
            }}
        """

    @staticmethod
    def generate_log_search_stylesheet(colors):
        """生成日志搜索工具栏样式表"""
        return f"""
            QToolBar {{
                background-color: {colors['tertiary_bg']};
                border-bottom: 1px solid {colors['border']};
                padding: 4px;
                spacing: 6px;
            }}
            QLineEdit {{
                background-color: {colors['primary_bg']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 200px;
            }}
            QLabel {{
                color: {colors['text_secondary']};
                font-size: 11px;
            }}
            QToolButton {{
                background-color: {colors['button_bg']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_light']};
                border-radius: 4px;
                padding: 4px;
                min-width: 30px;
            }}
            QToolButton:hover {{
                background-color: {colors['button_hover']};
            }}
        """

    @staticmethod
    def generate_draggable_node_item_stylesheet(node_bg_color, node_border_color, node_hover_color, node_hover_border_color, node_pressed_color):
        """生成可拖拽节点项样式表"""
        return f"""
            DraggableNodeItem {{
                background-color: {node_bg_color};
                border: 1px solid {node_border_color};
                border-radius: 10px;
                margin: 3px 0;
                padding: 2px;
            }}
            DraggableNodeItem:hover {{
                background-color: {node_hover_color};
                border: 1px solid {node_hover_border_color};
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
                margin: 2px 0;
            }}
            DraggableNodeItem:pressed {{
                background-color: {node_pressed_color};
                border: 1px solid {node_hover_border_color};
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
            }}
        """

    @staticmethod
    def generate_settings_dialog_stylesheet(colors):
        """生成设置对话框样式表"""
        return f"""
            QDialog {{
                background-color: {colors['primary_bg']};
            }}
            QGroupBox {{
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 16px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QLabel {{
                color: {colors['text_primary']};
            }}
            QComboBox {{
                background-color: {colors['button_bg']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 5px;
                min-width: 150px;
            }}
            
            QComboBox:hover {{
                background-color: {colors['button_hover']};
                border: 1px solid {colors['border_hover']};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 8px solid {colors['text_secondary']};
                width: 0;
                height: 0;
            }}
            QComboBox QAbstractItemView {{
                background-color: {colors['button_bg']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                selection-background-color: {colors['accent']};
                selection-color: {colors['text_primary']};
            }}
            QPushButton {{
                background-color: {colors['accent']};
                color: {colors['text_primary']};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {colors['accent_hover']};
            }}
            QPushButton:pressed {{
                background-color: {colors['button_pressed']};
            }}
        """

    @staticmethod
    def generate_about_dialog_stylesheet(colors):
        """生成关于对话框样式表"""
        return f"""
            QDialog {{
                background-color: {colors['primary_bg']};
            }}
            QTabWidget::pane {{
                border: 1px solid {colors['border']};
                border-radius: 6px;
            }}
            QTabBar::tab {{
                background-color: {colors['button_bg']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {colors['primary_bg']};
                border-bottom: 1px solid {colors['primary_bg']};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {colors['button_hover']};
            }}
            QLabel {{
                color: {colors['text_primary']};
            }}
            QTextBrowser {{
                background-color: {colors['secondary_bg']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 8px;
            }}
            QWidget {{
                background-color: {colors['primary_bg']};
                color: {colors['text_primary']};
            }}
            QPushButton {{
                background-color: {colors['accent']};
                color: {colors['text_primary']};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {colors['accent_hover']};
            }}
        """

    @staticmethod
    def generate_log_text_edit_stylesheet(colors):
        """生成日志文本框样式表"""
        return f"""
            QTextEdit {{
                background-color: {colors['log_bg']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 8px;
                selection-background-color: {colors['accent']};
                selection-color: {colors['text_primary']};
            }}
        """


class ThemeManager:
    """主题管理器"""

    def __init__(self):
        self.current_theme = 'light'  # 'dark' or 'light'
        self.colors = ThemeColors.LIGHT

    def set_theme(self, theme_name):
        """设置主题"""
        if theme_name.lower() == 'light':
            self.current_theme = 'light'
            self.colors = ThemeColors.LIGHT
        else:
            self.current_theme = 'dark'
            self.colors = ThemeColors.DARK

    def get_stylesheet(self, component='main_window'):
        """获取指定组件的样式表"""
        if component == 'main_window':
            return StylesheetGenerator.generate_main_window_stylesheet(self.colors)
        elif component == 'node_library':
            return StylesheetGenerator.generate_node_library_stylesheet(self.colors)
        elif component == 'dock_widget':
            return StylesheetGenerator.generate_dock_widget_stylesheet(self.colors)
        elif component == 'search_toolbar':
            return StylesheetGenerator.generate_search_toolbar_stylesheet(self.colors)
        elif component == 'log_search':
            return StylesheetGenerator.generate_log_search_stylesheet(self.colors)
        elif component == 'settings_dialog':
            return StylesheetGenerator.generate_settings_dialog_stylesheet(self.colors)
        elif component == 'about_dialog':
            return StylesheetGenerator.generate_about_dialog_stylesheet(self.colors)
        elif component == 'log_text_edit':
            return StylesheetGenerator.generate_log_text_edit_stylesheet(self.colors)
        else:
            return StylesheetGenerator.generate_main_window_stylesheet(self.colors)

    def get_node_color(self, node_type):
        """获取节点颜色"""
        return NodeColors.NODE_COLORS.get(node_type, NodeColors.NODE_COLORS['default'])

    def get_node_icon(self, node_type):
        """获取节点图标"""
        return NodeColors.NODE_ICONS.get(node_type, NodeColors.NODE_ICONS['default'])