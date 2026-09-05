# -*- coding: utf-8 -*-
"""
image_nodes.py
作者: reformLi
创建日期: 2026/4/28
最后修改: 2026/9/4
版本: 2.0.0

功能描述: 查找图片节点（模板匹配 / 颜色定位双模式）。
- 模板匹配：模板可来自文件路径或内嵌 Base64 数据（粘贴/截图），支持阈值、偏移、窗口区域检索。
- 颜色定位：以若干相对点的颜色组合定位目标，支持容差、窗口区域检索。
界面属性编辑器见 ui/node_image_widget.py 的 ImageNodeEditor。
"""
import json

import cv2

from automation.image_finder import ImageFinder
from nodes.base_node import WorkflowNode

finder = ImageFinder()

_MODES = ['模板匹配', '颜色定位']
_PREPROCESS = ['无', '灰度', '二值化']


class FindImageNode(WorkflowNode):
    __identifier__ = 'workflow'
    NODE_NAME = "查找图片"
    NODE_ICON = 'fa5s.search-plus'
    NODE_CATEGORY = "图像识别"
    IMAGE_NODE = True

    def __init__(self):
        super().__init__()
        self.add_input('窗口对象', multi_input=False)
        self.add_output('坐标')
        self.add_output('中心坐标')
        self.add_output('匹配度')
        self._register_storage('mode', _MODES[0])
        self._register_storage('template_path', '')
        self._register_storage('template_data', '')   # base64 PNG/JPEG（内嵌）
        self._register_storage('points', '[]')        # 颜色定位点 [{dx,dy,r,g,b}]
        self._register_storage('threshold', '0.8')
        self._register_storage('offset_x', '0')
        self._register_storage('offset_y', '0')
        self._register_storage('click_after', '0')   # 匹配后自动点击 0/1
        self._register_storage('tolerance', '40')    # 颜色定位逐通道容差
        self._register_storage('preprocess', '无')    # 模板匹配预处理：无/灰度/二值化
        self._register_storage('bg_mode', '0')       # 后台离屏识别(PrintWindow) 0/1

    def _register_storage(self, name, value):
        """注册为可序列化的模型属性，但不进入属性页通用行（由 ImageNodeEditor 接管）。"""
        self.create_property(name, value=value)

    # ---------------- 配置辅助（供编辑器读写） ----------------
    def set_image_source(self, path='', data=''):
        if data:
            self.set_property('template_path', '')
            self.set_property('template_data', data)
        else:
            self.set_property('template_path', path)
            self.set_property('template_data', '')

    def get_template(self):
        """按 内嵌数据 > 文件 返回 BGR 数组模板或 None。"""
        return finder.read_template_source(
            self.get_property('template_path'),
            self.get_property('template_data'))

    def get_colored_points(self):
        raw = self.get_property('points') or '[]'
        try:
            pts = json.loads(raw)
        except Exception:
            return []
        return [p for p in pts if isinstance(p, dict) and 'r' in p]

    def set_colored_points(self, points):
        self.set_property('points', json.dumps(points, ensure_ascii=False))

    # ---------------- 执行 ----------------
    def _resolve_search(self, inputs):
        """返回(region, window) 或 (None, None) 表示全屏。"""
        window = inputs.get('窗口对象', None)
        if window is not None:
            rect = finder.window_manager.get_window_rect(window)
            if rect:
                left, top, right, bottom = rect
                return (left, top, right - left, bottom - top), window
        return None, None

    def _apply_threshold(self):
        try:
            return float(self.get_property('threshold') or '0.8')
        except (TypeError, ValueError):
            return 0.8

    def _apply_tolerance(self):
        try:
            return int(float(self.get_property('tolerance') or '40'))
        except (TypeError, ValueError):
            return 40

    def _apply_offset(self, point):
        try:
            ox = int(float(self.get_property('offset_x') or 0))
            oy = int(float(self.get_property('offset_y') or 0))
        except (TypeError, ValueError):
            ox = oy = 0
        return (point[0] + ox, point[1] + oy)

    def _preprocess(self, img):
        mode = self.get_property('preprocess') or '无'
        if mode == '灰度':
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if mode == '二值化':
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, th = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            return th
        return img

    def _should_click(self):
        return (self.get_property('click_after') or '0') in ('1', 'true', 'yes')

    def _is_bg(self):
        return (self.get_property('bg_mode') or '0') in ('1', 'true', 'yes')

    def _resolve_bg_hwnd(self, inputs):
        """后台离屏识别：校验并返回窗口句柄；未开启或未连窗口时按需抛错。"""
        if not self._is_bg():
            return None
        window = inputs.get('窗口对象', None)
        if window is None:
            raise RuntimeError('后台离屏识别需要连接「窗口对象」输入端口')
        hwnd = finder.hwnd_of(window)
        if not hwnd:
            raise RuntimeError('后台离屏识别无法解析窗口句柄')
        return hwnd

    def _click_if_enabled(self, x, y):
        if not self._should_click():
            return
        if self._is_bg():
            # 后台模式下坐标为客户区相对坐标，不能按屏幕绝对坐标真实点击；
            # 真正的后台点击交给下游「鼠标点击」节点处理。
            return
        try:
            import pyautogui
            pyautogui.click(int(x), int(y))
        except Exception:
            pass

    def execute(self, inputs):
        mode = self.get_property('mode') or _MODES[0]
        region, window = self._resolve_search(inputs)
        bg_hwnd = self._resolve_bg_hwnd(inputs)

        if bg_hwnd is not None:
            # ---------------- 后台离屏识别：结果坐标为【客户区相对坐标】 ----------------
            if mode == '颜色定位':
                points = self.get_colored_points()
                if len(points) < 1:
                    raise RuntimeError('颜色定位需要至少 1 个采集点，请在属性中执行「开始采集」')
                tolerance = self._apply_tolerance()
                hits, _size = finder.find_color_points_offscreen(
                    bg_hwnd, points, tolerance=tolerance)
                if not hits:
                    raise RuntimeError('后台未找到匹配的颜色点组合（可增大容差）')
                best = hits[0]
                center = self._apply_offset(best['base_center'])
                return {'坐标': center, '中心坐标': center,
                        '匹配度': 1.0 - min(1.0, best['max_dev'] / 255.0)}, '坐标'

            template = self.get_template()
            if template is None:
                raise RuntimeError('未设置模板图片：请粘贴 / 选择图片，或提供内嵌模板')
            confidence = self._apply_threshold()
            if self.get_property('preprocess') and self.get_property('preprocess') != '无':
                template = self._preprocess(template)
            results, _size = finder.find_on_window_offscreen(
                bg_hwnd, template, confidence=confidence)
            if not results:
                raise RuntimeError('后台窗口内未找到匹配的模板（阈值 %.2f）' % confidence)
            best = results[0]
            center = self._apply_offset(best['center'])
            return {'坐标': best['top_left'], '中心坐标': center,
                    '匹配度': best['max_val']}, '坐标'

        if mode == '颜色定位':
            points = self.get_colored_points()
            if len(points) < 1:
                raise RuntimeError('颜色定位需要至少 1 个采集点，请在属性中执行「开始采集」')
            tolerance = self._apply_tolerance()
            if region:
                screen = finder.capture_screen(region)
                hits = finder.find_color_points(points, tolerance, screen_img=screen)
            else:
                hits = finder.find_color_points(points, tolerance, region=region)
            if not hits:
                raise RuntimeError('未找到匹配的颜色点组合（可增大容差或检查区域）')
            best = hits[0]
            center = self._apply_offset(best['base_center'])
            self._click_if_enabled(*center)
            return {'坐标': center, '中心坐标': center,
                    '匹配度': 1.0 - min(1.0, best['max_dev'] / 255.0)}, '坐标'

        # 模板匹配
        template = self.get_template()
        if template is None:
            raise RuntimeError('未设置模板图片：请粘贴 / 选择图片，或提供内嵌模板')
        confidence = self._apply_threshold()
        screen = finder.capture_screen(region) if region else finder.capture_screen()
        if self.get_property('preprocess') and self.get_property('preprocess') != '无':
            screen = self._preprocess(screen)
            template = self._preprocess(template)
        results = finder.match_from_array(screen, template, confidence, search_region=region)
        if not results:
            raise RuntimeError('未在屏幕上找到匹配的模板（阈值 %.2f）' % confidence)
        best = results[0]
        center = self._apply_offset(best['center'])
        self._click_if_enabled(*center)
        return {'坐标': best['top_left'], '中心坐标': center,
                '匹配度': best['max_val']}, '坐标'