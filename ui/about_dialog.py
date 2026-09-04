# -*- coding: utf-8 -*-
"""
about_dialog.py
功能描述: 关于对话框（应用信息 / 技术栈 / 许可证）
         图标改用 qtawesome 矢量图标，技术信息与实际依赖版本对齐。
         见 UI_DESIGN.md §5.7
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QTabWidget, QTextBrowser, QVBoxLayout, QWidget
)

from app.config import APP_NAME, APP_VERSION
from ui import icons, qss, tokens

# 技术栈（与 requirements.txt 保持一致）
_STACK_ROWS = [
    ('GUI 框架', 'PyQt5 5.15.11'),
    ('矢量图标', 'QtAwesome 1.4.2'),
    ('节点图引擎', 'NodeGraphQt 0.6.44'),
    ('Windows 自动化', 'uiautomation 2.0.29 / pywin32 311'),
    ('图像识别', 'opencv-python 4.13 / numpy 2.4'),
    ('剪贴板', 'pyperclip 1.11.0'),
    ('Python', '3.11+（Windows）'),
]

_FEATURES = [
    '可视化节点编排（拖拽创建、连线、框选）',
    '流程控制：条件分支 / 循环 / 等待',
    '窗口自动化：查找 / 激活 / 鼠标 / 键盘 / 图像定位',
    '子线程执行引擎：支持暂停 / 恢复 / 终止',
    '节点级实时状态与耗时反馈',
    '工作流校验与 JSON 持久化',
]


class AboutDialog(QDialog):
    """关于对话框"""

    def __init__(self, theme_state=None, parent=None):
        super().__init__(parent)
        self.theme_state = theme_state
        self.setWindowTitle('关于')
        self.setMinimumSize(520, 420)

        self._build()

    # ── 构建 ────────────────────────────────────────────
    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._about_tab(), '关于')
        tabs.addTab(self._tech_tab(), '技术信息')
        tabs.addTab(self._license_tab(), '许可证')
        layout.addWidget(tabs, 1)

        close_button = QPushButton('关闭')
        qss.set_kind(close_button, 'primary')
        close_button.clicked.connect(self.close)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

    def _about_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(20, 24, 20, 12)
        outer.setSpacing(10)

        # 头部：矢量图标 + 名称/版本/简介
        header = QHBoxLayout()
        header.setSpacing(16)

        logo = QLabel()
        logo.setPixmap(self._logo_pixmap(64))
        logo.setFixedSize(64, 64)
        logo.setAlignment(Qt.AlignCenter)
        header.addWidget(logo)

        info = QVBoxLayout()
        info.setSpacing(2)

        name = QLabel(APP_NAME)
        name.setStyleSheet(f"font-size: 20pt; font-weight: bold; color: {tokens.DARK['text']};")
        version = QLabel(f'版本 {APP_VERSION}')
        version.setStyleSheet(f"font-size: 10pt; color: {tokens.DARK['text_2nd']};")
        subtitle = QLabel('基于 PyQt5 与 NodeGraphQt 的可视化自动化工作流编辑器')
        subtitle.setStyleSheet(f"font-size: 10pt; color: {tokens.DARK['text_dim']};")

        info.addWidget(name)
        info.addWidget(version)
        info.addWidget(subtitle)
        header.addLayout(info, 1)
        outer.addLayout(header)

        # 主要功能
        features_title = QLabel('主要功能')
        features_title.setStyleSheet(f"font-weight: bold; color: {tokens.DARK['text']};")
        outer.addWidget(features_title)

        features = QLabel('\n'.join(f'• {text}' for text in _FEATURES))
        features.setStyleSheet(f"color: {tokens.DARK['text_2nd']};")
        outer.addWidget(features)

        outer.addStretch(1)

        copyright_label = QLabel('© 2026 reformLi · MIT License')
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet(f"color: {tokens.DARK['text_dim']};")
        outer.addWidget(copyright_label)
        return tab

    def _tech_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        browser = QTextBrowser()
        browser.setReadOnly(True)
        rows = ''.join(
            f'<tr><td style="padding:4px 16px 4px 0;color:{tokens.DARK["text_2nd"]}">{k}</td>'
            f'<td style="color:{tokens.DARK["text"]}">{v}</td></tr>'
            for k, v in _STACK_ROWS
        )
        browser.setHtml(
            f'<div style="font-family:"Microsoft YaHei UI";font-size:10pt">'
            f'<h4 style="color:{tokens.DARK["text"]}">技术栈</h4>'
            f'<table>{rows}</table>'
            f'<h4 style="color:{tokens.DARK["text"]}">运行环境</h4>'
            f'<ul style="color:{tokens.DARK["text_2nd"]}">'
            f'<li>Windows 10 / 11（依赖 pywin32、uiautomation）</li>'
            f'<li>Python 3.11 及以上</li>'
            f'<li>建议使用项目内 venv 解释器运行</li>'
            f'</ul></div>'
        )
        layout.addWidget(browser)
        return tab

    def _license_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        area = QScrollArea()
        area.setWidgetResizable(True)
        license_text = QTextBrowser()
        license_text.setPlainText(_MIT_LICENSE)
        area.setWidget(license_text)
        layout.addWidget(area)
        return tab

    @staticmethod
    def _logo_pixmap(size):
        """用矢量图标生成关于框 logo（分类色底 + 深色字形）"""
        pixmap = icons.tile_pixmap('fa5s.project-diagram', tokens.DARK['accent'],
                                   size=size, radius=size // 6)
        return pixmap


_MIT_LICENSE = """MIT License

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
SOFTWARE."""
