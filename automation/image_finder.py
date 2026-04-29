# -*- coding: utf-8 -*-
"""
image_finder.py
作者: reformLi
创建日期: 2026/4/28
最后修改: 2026/4/28
版本: 1.0.0

功能描述: 对指定窗口或屏幕截图
"""
# automation/image_finder.py
import cv2
import numpy as np
from automation.window_manager import WindowManager  # 用于截图


class ImageFinder:
    """基于图像模板的定位器"""

    def __init__(self, confidence=0.8, method=cv2.TM_CCOEFF_NORMED):
        self.confidence = confidence
        self.method = method
        self.window_manager = WindowManager()

    def find_on_screen(self, template_path, confidence=None):
        """
        在整个屏幕上查找模板图片。
        返回匹配中心坐标 (x, y)，未找到返回 None。
        """
        # 全屏截图
        import pyautogui  # 仅用于截图，或使用win32api
        screenshot = pyautogui.screenshot()
        screen_img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        return self._match_template(screen_img, template_path, confidence)

    def find_on_window(self, window, template_path, confidence=None):
        """
        在指定窗口内查找模板图片。
        window: uiautomation 控件对象。
        """
        rect = self.window_manager.get_window_rect(window)
        if not rect:
            return None
        left, top, right, bottom = rect
        # 截取窗口区域
        import pyautogui
        region_screenshot = pyautogui.screenshot(region=(left, top, right - left, bottom - top))
        region_img = cv2.cvtColor(np.array(region_screenshot), cv2.COLOR_RGB2BGR)
        match_pt = self._match_template(region_img, template_path, confidence)
        if match_pt:
            # 转换为屏幕绝对坐标
            return (match_pt[0] + left, match_pt[1] + top)
        return None

    def _match_template(self, img, template_path, confidence):
        """在 img 中匹配模板，返回中心点（相对于 img 左上角）或 None"""
        template = cv2.imread(template_path)
        if template is None:
            raise FileNotFoundError(f"模板图片不存在: {template_path}")

        h, w = template.shape[:2]
        result = cv2.matchTemplate(img, template, self.method)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        conf = confidence or self.confidence
        if max_val >= conf:
            # 返回中心点
            return (max_loc[0] + w // 2, max_loc[1] + h // 2)
        return None