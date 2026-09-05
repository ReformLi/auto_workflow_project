# -*- coding: utf-8 -*-
"""
ocr_nodes.py
功能描述: OCR 识别节点——独立文字识别，负责从屏幕/窗口/框选区域截图并识别文字。
- 输出整段文本（text）与结构化文本块（results：内容、坐标、置信度）。
- 识别区域支持：全屏 / 窗口全部 / 窗口内框选（相对窗口偏移，跟随窗口移动） / 屏幕框选。
- 引擎：直接调用系统 Tesseract（见 automation/ocr.py），零新增依赖。
属性页使用自定义编辑器（OcrNodeEditor，见 ui/node_ocr_widget.py）。
"""
from automation.image_finder import ImageFinder
from automation.ocr import OcrEngine
from automation.window_manager import WindowManager
from nodes.base_node import WorkflowNode

engine = OcrEngine()
finder = ImageFinder()
window_manager = WindowManager()

_LANGS = ['简体中文', '英文', '简体中文+英文']
_LANG_CODE = {'简体中文': 'chi_sim', '英文': 'eng',
              '简体中文+英文': 'chi_sim+eng'}
_REGIONS = ['全屏', '窗口全部', '窗口内框选', '屏幕框选']
_PREPROCESS = ['无', '灰度', '二值化']
_PSMS = ['自动', '单行文本', '单字', '稀疏']
_PSM_CODE = {'自动': 3, '单行文本': 7, '单字': 10, '稀疏': 11}


class OcrNode(WorkflowNode):
    __identifier__ = 'workflow'
    NODE_NAME = 'OCR 识别'
    NODE_ICON = 'fa5s.font'
    NODE_CATEGORY = '图像识别'
    OCR_NODE = True  # 使用自定义属性编辑器（OcrNodeEditor）接管属性页

    def __init__(self):
        super().__init__()
        self.add_input('窗口对象', multi_input=False)
        self.add_output('text')
        self.add_output('results')

        # 属性均用 create_property 注册（可序列化），但不进入通用属性行，
        # 全部由 OcrNodeEditor 渲染（见 ui/node_ocr_widget.py）。
        self._register_storage('lang', _LANGS[0])
        self._register_storage('region_mode', _REGIONS[0])
        # region_rect 语义随 region_mode：
        #   窗口内框选 -> "dx,dy,宽,高"（相对窗口左上角）
        #   屏幕框选   -> "x,y,宽,高"（屏幕绝对坐标）
        self._register_storage('region_rect', '')
        self._register_storage('region_anchor', '')  # 设计期锚点窗口标题（仅信息展示，执行不依赖）
        self._register_storage('preprocess', _PREPROCESS[0])
        self._register_storage('min_conf', '0')
        self._register_storage('psm', _PSMS[0])

    def _register_storage(self, name, value):
        """注册为可序列化的模型属性，但不进入属性页通用行（由 OcrNodeEditor 接管）。"""
        self.create_property(name, value=value)

    # ---------------- 配置辅助 ----------------
    def _apply_lang(self):
        return _LANG_CODE.get(self.get_property('lang') or _LANGS[0], 'chi_sim')

    def _apply_psm(self):
        return _PSM_CODE.get(self.get_property('psm') or _PSMS[0], 3)

    def _apply_min_conf(self):
        try:
            return max(0, int(float(self.get_property('min_conf') or '0')))
        except (TypeError, ValueError):
            return 0

    def get_region_mode(self):
        return self.get_property('region_mode') or _REGIONS[0]

    def set_frame_region(self, rect_str, anchor=''):
        """由 UI 回填框选结果：rect_str="a,b,c,d"，anchor 为锚点窗口标题（可选）。"""
        self.set_property('region_rect', rect_str or '')
        self.set_property('region_anchor', anchor or '')

    @staticmethod
    def _parse_rect(rect_str, label):
        """解析 "a,b,c,d" 为 (a,b,c,d) 整数，并校验宽高>0。"""
        parts = (rect_str or '').split(',')
        if len(parts) != 4:
            raise RuntimeError(f'{label}区域无效，请重新框选')
        try:
            a, b, w, h = (int(float(p.strip())) for p in parts)
        except (TypeError, ValueError):
            raise RuntimeError(f'{label}区域坐标格式错误')
        if w <= 0 or h <= 0:
            raise RuntimeError(f'{label}区域的宽高需大于 0')
        return a, b, w, h

    def _require_window(self, window, mode):
        """窗口类区域模式统一校验：必须连接窗口对象输入。"""
        if window is None:
            raise RuntimeError(f'识别区域为「{mode}」，但未连接窗口对象输入')
        rect = window_manager.get_window_rect(window)
        if not rect:
            raise RuntimeError('无法获取窗口矩形区域')
        return rect

    def _resolve_region(self, inputs):
        """返回 (region or None, window)。region 为屏幕绝对坐标 (x, y, w, h)。
        全屏返回 (None, None)。"""
        mode = self.get_region_mode()
        window = inputs.get('窗口对象', None)

        if mode == '窗口全部':
            left, top, right, bottom = self._require_window(window, mode)
            return ((left, top, right - left, bottom - top), window)

        if mode == '窗口内框选':
            rect = self._require_window(window, mode)
            dx, dy, w, h = self._parse_rect(
                self.get_property('region_rect'), '窗口内框选')
            left, top = rect[0], rect[1]
            return ((left + dx, top + dy, w, h), window)

        if mode == '屏幕框选':
            x, y, w, h = self._parse_rect(
                self.get_property('region_rect'), '屏幕框选')
            return ((x, y, w, h), None)

        # 全屏
        return (None, None)

    # ---------------- 执行 ----------------
    def execute(self, inputs):
        if not engine.available():
            raise RuntimeError('未找到 Tesseract，无法执行 OCR 识别')

        region, _ = self._resolve_region(inputs)
        ox = oy = 0
        if region:
            x, y, w, h = region
            ox, oy = x, y
            screen = finder.capture_screen(region)
        else:
            screen = finder.capture_screen()

        result = engine.recognize(
            screen, lang=self._apply_lang(), psm=self._apply_psm(),
            min_conf=self._apply_min_conf(),
            preprocess=self.get_property('preprocess') or '无')
        text = result.get('text', '')
        results = result.get('results', [])
        # 坐标统一转为屏幕绝对坐标（与查找图片节点一致，便于后续定位/点击）
        for item in results:
            item['x'] += ox
            item['y'] += oy
        return {'text': text, 'results': results}, 'text'