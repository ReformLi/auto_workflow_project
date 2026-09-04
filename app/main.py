#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动工作流设计器 - 主程序入口
"""

import sys
import logging
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from app.config import APP_NAME, APP_VERSION
from ui.main_window import WorkflowMainWindow
from ui import qss
from app.logger import setup_logging

# 应用图标（按项目根定位，不依赖当前工作目录）
APP_ICON_PATH = Path(__file__).resolve().parent.parent / 'resources' / 'icons' / 'app.ico'


def setup_app_icon(app):
    """设置窗口/任务栏图标；图标缺失时静默跳过，不影响启动"""
    try:
        if APP_ICON_PATH.exists():
            app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    except Exception:
        pass

    # Windows：显式声明 AppUserModelID，避免任务栏按钮继承 python.exe 的图标
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                'ReformLi.AutoWorkflowDesigner.1')
        except Exception:
            pass


def main():
    """主函数"""
    # 设置应用程序
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 设置应用程序信息
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    setup_app_icon(app)

    # 全局字体 + 全局样式表（唯一 QSS 入口，见 UI_DESIGN.md §6）
    qss.apply_font(app)
    app.setStyleSheet(qss.build_qss())

    # 设置高DPI支持
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # 创建主窗口
        window = WorkflowMainWindow()
        window.show()

        logger.info(f'{APP_NAME} v{APP_VERSION} 启动成功')

        # 运行应用程序
        sys.exit(app.exec_())

    except Exception as e:
        logger.error(f'应用程序启动失败: {str(e)}')
        sys.exit(1)


if __name__ == '__main__':
    main()