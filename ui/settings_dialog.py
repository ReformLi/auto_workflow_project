# -*- coding: utf-8 -*-
"""
settings_dialog.py
设置对话框
提供主题切换和其他应用设置
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QComboBox,
    QGroupBox, QFormLayout, QDialogButtonBox, QWidget, QHBoxLayout, QLabel, QCheckBox
)

from tests.mytest23 import Switch


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.setWindowTitle('设置')
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """设置用户界面"""
        main_layout = QVBoxLayout(self)

        # 外观设置组
        appearance_group = QGroupBox('外观设置')
        appearance_layout = QFormLayout()

        # 主题选择
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['深色主题', '浅色主题'])
        self.theme_combo.setCurrentIndex(0 if self.theme_manager.current_theme == 'dark' else 1)

        appearance_layout.addRow('主题模式:', self.theme_combo)
        appearance_group.setLayout(appearance_layout)

        # 显示状态栏选项（复选框）
        self.statusbar_checkbox = QCheckBox('显示网格线')
        self.statusbar_checkbox.setChecked(self.theme_manager.grid_display)  # 默认显示，可按需调整
        appearance_layout.addRow('', self.statusbar_checkbox)  # 第二个参数作为标签右侧的控件，留空标签
        self._old_statusbar_state = self.statusbar_checkbox.isChecked()

        main_layout.addWidget(appearance_group)

        # 工作流设置组
        workflow_group = QGroupBox('工作流设置')
        workflow_layout = QFormLayout()

        # 自动保存
        self.auto_save_combo = QComboBox()
        self.auto_save_combo.addItems(['关闭', '5分钟', '10分钟', '30分钟'])
        self.auto_save_combo.setCurrentIndex(1)  # 默认5分钟

        workflow_layout.addRow('自动保存:', self.auto_save_combo)

        # 执行超时
        self.timeout_combo = QComboBox()
        self.timeout_combo.addItems(['30秒', '1分钟', '5分钟', '10分钟', '不限制'])
        self.timeout_combo.setCurrentIndex(2)  # 默认5分钟

        workflow_layout.addRow('执行超时:', self.timeout_combo)

        workflow_group.setLayout(workflow_layout)
        main_layout.addWidget(workflow_group)

        # 日志设置组
        log_group = QGroupBox('日志设置')
        log_layout = QFormLayout()

        # 日志级别
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR'])
        self.log_level_combo.setCurrentIndex(1)  # 默认INFO

        log_layout.addRow('日志级别:', self.log_level_combo)

        # 最大日志行数
        self.max_log_lines_combo = QComboBox()
        self.max_log_lines_combo.addItems(['1000行', '5000行', '10000行', '无限制'])
        self.max_log_lines_combo.setCurrentIndex(1)  # 默认5000行

        log_layout.addRow('最大日志行数:', self.max_log_lines_combo)

        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)

        main_layout.addWidget(button_box)

        # 应用当前主题样式
        self.apply_theme_styling()

    def apply_theme_styling(self):
        """应用主题样式"""
        stylesheet = self.theme_manager.get_stylesheet('settings_dialog')
        self.setStyleSheet(stylesheet)

    def load_settings(self):
        """加载当前设置"""
        # 这里可以从配置文件加载设置
        # 目前使用默认值
        pass

    def apply_settings(self):
        """应用设置"""
        # 应用主题设置
        theme_index = self.theme_combo.currentIndex()
        new_theme = 'dark' if theme_index == 0 else 'light'
        if new_theme != self.theme_manager.current_theme:
            self.theme_manager.set_theme(new_theme)
            # 通知父窗口主题已更改
            if hasattr(self.parent(), 'apply_theme'):
                self.parent().apply_theme()

        statusbar_checkbox = self.statusbar_checkbox.isChecked()
        if statusbar_checkbox != self.theme_manager.grid_display :
            # 更新旧值
            self.theme_manager.grid_display = statusbar_checkbox
            # 通知父窗口需更换网格线
            if hasattr(self.parent(), 'update_grid'):
                self.parent().update_grid(self.theme_manager.grid_display)
        # 这里可以保存其他设置到配置文件
        # TODO: 实现设置保存功能

    def accept(self):
        """接受设置（确定按钮）"""
        self.apply_settings()
        super().accept()

    def get_settings(self):
        """获取当前设置"""
        return {
            'theme': 'dark' if self.theme_combo.currentIndex() == 0 else 'light',
            'statusbar_checkbox': self.statusbar_checkbox.isChecked(),
            'auto_save': self.auto_save_combo.currentText(),
            'timeout': self.timeout_combo.currentText(),
            'log_level': self.log_level_combo.currentText(),
            'max_log_lines': self.max_log_lines_combo.currentText(),
        }