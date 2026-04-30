# -*- coding: utf-8 -*-
"""
about_dialog.py
关于对话框
显示应用程序信息、版本和版权信息
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextBrowser, QTabWidget, QWidget
)

from app.config import APP_NAME, APP_VERSION
from ui.styles import ThemeManager


class AboutDialog(QDialog):
    """关于对话框"""

    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.setWindowTitle('关于')
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self.setup_ui()

    def setup_ui(self):
        """设置用户界面"""
        main_layout = QVBoxLayout(self)

        # 创建选项卡
        tab_widget = QTabWidget()

        # 关于选项卡
        about_tab = QWidget()
        about_layout = QVBoxLayout(about_tab)

        # 应用程序信息
        app_info_layout = QHBoxLayout()

        # 应用程序图标（使用文本代替）
        icon_label = QLabel('🚀')
        icon_label.setStyleSheet("font-size: 64px;")
        icon_label.setAlignment(Qt.AlignCenter)
        app_info_layout.addWidget(icon_label)

        # 应用程序详细信息
        app_details_layout = QVBoxLayout()

        app_name_label = QLabel(APP_NAME)
        app_name_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        app_name_label.setAlignment(Qt.AlignCenter)

        version_label = QLabel(f'版本 {APP_VERSION}')
        version_label.setStyleSheet("font-size: 16px;")
        version_label.setAlignment(Qt.AlignCenter)

        description_label = QLabel('基于PyQt5和NodeGraphQt的\n可视化脚本工作流编辑器')
        description_label.setStyleSheet("font-size: 14px;")
        description_label.setAlignment(Qt.AlignCenter)

        app_details_layout.addWidget(app_name_label)
        app_details_layout.addWidget(version_label)
        app_details_layout.addWidget(description_label)

        app_info_layout.addLayout(app_details_layout)
        about_layout.addLayout(app_info_layout)

        # 功能特性
        features_label = QLabel('主要功能:')
        features_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        about_layout.addWidget(features_label)

        features_text = QLabel(
            '• 可视化节点编辑器\n'
            '• 丰富的节点类型\n'
            '• 完整的用户界面\n'
            '• 工作流管理\n'
            '• 实时日志\n'
            '• 工作流验证'
        )
        features_text.setStyleSheet("font-size: 14px;")
        about_layout.addWidget(features_text)

        about_layout.addStretch()

        # 版权信息
        copyright_label = QLabel('© 2026 reformLi. MIT License')
        copyright_label.setStyleSheet("font-size: 12px; color: #888888;")
        copyright_label.setAlignment(Qt.AlignCenter)
        about_layout.addWidget(copyright_label)

        tab_widget.addTab(about_tab, '关于')

        # 技术信息选项卡
        tech_tab = QWidget()
        tech_layout = QVBoxLayout(tech_tab)

        tech_info = QTextBrowser()
        tech_info.setReadOnly(True)
        tech_info.setHtml("""
        <h3>技术栈</h3>
        <ul>
            <li><b>GUI框架:</b> PyQt5 5.15.10</li>
            <li><b>节点图库:</b> NodeGraphQt 0.6.44</li>
            <li><b>Python版本:</b> 3.7+</li>
            <li><b>开发环境:</b> Windows 11</li>
        </ul>

        <h3>系统要求</h3>
        <ul>
            <li>Python 3.7或更高版本</li>
            <li>PyQt5 5.15.10</li>
            <li>NodeGraphQt 0.6.44</li>
            <li>Windows 7或更高版本</li>
        </ul>

        <h3>依赖包</h3>
        <ul>
            <li>PyQt5 - GUI框架</li>
            <li>NodeGraphQt - 节点图编辑器</li>
            <li>pywinauto - Windows自动化</li>
            <li>uiautomation - UI自动化</li>
        </ul>
        """)

        tech_layout.addWidget(tech_info)
        tab_widget.addTab(tech_tab, '技术信息')

        # 许可证选项卡
        license_tab = QWidget()
        license_layout = QVBoxLayout(license_tab)

        license_text = QTextBrowser()
        license_text.setReadOnly(True)
        license_text.setPlainText("""
MIT License

Copyright (c) 2026 reformLi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
        """)

        license_layout.addWidget(license_text)
        tab_widget.addTab(license_tab, '许可证')

        main_layout.addWidget(tab_widget)

        # 关闭按钮
        close_button = QPushButton('关闭')
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        main_layout.addLayout(button_layout)

        # 应用主题样式
        self.apply_theme_styling()

    def apply_theme_styling(self):
        """应用主题样式"""
        stylesheet = self.theme_manager.get_stylesheet('about_dialog')
        self.setStyleSheet(stylesheet)

        # 特殊样式保持独立（这些是动态内容，不适合放在通用样式表中）
        icon_color = self.theme_manager.colors['accent']
        copyright_color = self.theme_manager.colors['text_tertiary']

        # 应用特殊样式
        self.setStyleSheet(self.styleSheet() + f"""
            QLabel[style*="font-size: 64px;"] {{
                color: {icon_color};
            }}
            QLabel[style*="color: #888888;"] {{
                color: {copyright_color};
            }}
        """)