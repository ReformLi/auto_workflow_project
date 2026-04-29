#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动工作流设计器 - 主程序入口
"""

import sys
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from app.config import APP_NAME, APP_VERSION
from ui.main_window import WorkflowMainWindow
from app.logger import setup_logging


def main():
    """主函数"""
    # 设置应用程序
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 设置应用程序信息
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

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