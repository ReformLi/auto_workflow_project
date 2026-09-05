#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动工作流设计器 - 主程序入口
"""

import sys
import logging
import os
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, qInstallMessageHandler, QtMsgType
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


def setup_qt_message_handler():
    """把 Qt 的 qDebug/qWarning/qCritical/qFatal 转发到 Python 日志，
    便于定位 Qt 断言/致命错误（0xC0000409 崩溃前最后一条消息）。"""

    def handler(msg_type, context, message):
        if msg_type == QtMsgType.QtDebugMsg:
            logging.getLogger('qt').debug(message)
        elif msg_type == QtMsgType.QtWarningMsg:
            logging.getLogger('qt').warning(message)
        elif msg_type == QtMsgType.QtCriticalMsg:
            logging.getLogger('qt').error(message)
        elif msg_type == QtMsgType.QtFatalMsg:
            # 记录致命消息后按 Qt 默认行为终止，保留崩溃现场
            logging.getLogger('qt').critical('QtFatal: %s', message)
            os.abort()

    qInstallMessageHandler(handler)


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

    # 转发 Qt 消息到日志（崩溃前定位致命断言）
    setup_qt_message_handler()

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