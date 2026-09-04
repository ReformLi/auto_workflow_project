# -*- coding: utf-8 -*-
"""
theme.py
功能描述: 界面状态持有者（主题、网格、日志显示参数）
         样式本身在 ui/qss.py + ui/tokens.py；本文件只存「用户可改的状态值」。
         取代旧的 ui/styles.py（其按组件生成 QSS 的做法已被全局样式表替代）。
"""

import logging


class ThemeState:
    """界面状态（当前仅提供深色主题，保留多主题扩展位）"""

    def __init__(self):
        self.current_theme = 'dark'
        self.grid_display = True
        # 捕获级别：根记录器实际记录进面板的最低级别（设置对话框控制）
        self.log_capture_level = logging.INFO
        # 显示过滤：面板上只看该级别及以上（日志工具条胶囊控制，NOTSET = 全部）
        self.log_display_filter = logging.NOTSET
        self.max_log_lines = 5000

    def set_theme(self, theme_name):
        """设置主题（浅色主题本次重设计不提供，统一保持深色）"""
        name = (theme_name or 'dark').lower()
        if name != 'dark':
            logging.getLogger(__name__).warning('浅色主题未在 UI 重设计中提供，已保持深色主题')
        self.current_theme = 'dark'

    @property
    def is_dark(self):
        return self.current_theme == 'dark'
