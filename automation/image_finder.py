# -*- coding: utf-8 -*-
"""
image_finder.py
作者: reformLi
创建日期: 2026/4/28
最后修改: 2026/9/4
版本: 1.2.0

功能描述: 图像识别核心。
- 模板匹配：支持从文件路径或内存数组（ndarray，支持粘贴/内嵌 Base64）在屏幕/窗口/区域中检索。
- 颜色定位：以若干相对点的颜色组合定位目标，对缩放/光照有一定鲁棒性。
- 截屏与像素采样辅助。
"""
import base64
import io

import cv2
import numpy as np

from automation.window_manager import WindowManager


def _screenshot_to_bgr(region=None):
    """截取屏幕（region=(x,y,w,h) 可选）并返回 BGR ndarray。"""
    import pyautogui
    img = pyautogui.screenshot(region=region)
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def _hwnd_of(window):
    """把窗口对象/句柄统一解析为整数 hwnd；失败返回 None。"""
    if isinstance(window, int):
        return window
    for attr in ('NativeWindowHandle', 'native_window_handle', 'handle'):
        try:
            return int(getattr(window, attr))
        except Exception:
            continue
    try:
        return int(window)
    except Exception:
        return None


def capture_window_offscreen(hwnd):
    """PrintWindow 离屏抓取窗口客户区内容，返回 (BGR ndarray, (w, h))。

    与普通屏幕截图不同：直接让目标窗口离屏绘制到内存位图，
    即使窗口被其他窗口遮挡或最小化，也能拿到它自身的内容（"后台识别"）。
    失败或窗口不支持 PrintWindow 时返回 (None, (0, 0))。
    """
    import ctypes
    try:
        import win32gui
        import win32ui
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        w = right - left
        h = bottom - top
        if w <= 0 or h <= 0:
            return None, (0, 0)
        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(bmp)
        # PW_RENDERFULLCONTENT = 0x2：捕获经 DWM 合成的完整内容（UWP/多数现代窗口）
        ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)
        arr = np.frombuffer(bmp.GetBitmapBits(True), np.uint8)
        img_bgra = arr.reshape((h, w, 4))
        bgr = img_bgra[:, :, :3].copy()  # BGRA → BGR
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)
        return bgr, (w, h)
    except Exception:
        return None, (0, 0)


class ImageFinder:
    """基于图像模板/颜色点的定位器"""

    def __init__(self, confidence=0.8, method=cv2.TM_CCOEFF_NORMED):
        self.confidence = confidence
        self.method = method
        self.window_manager = WindowManager()

    # ---------------- 读取模板 ----------------
    @staticmethod
    def read_template_source(template_path=None, template_data=None):
        """按 内嵌数据(base64/ndarray) > 文件路径 的顺序返回 BGR ndarray 模板。

        template_data: 可为 base64 字符串（PNG/JPEG）或 ndarray 或 bytes。
        无法解析时返回 None。
        """
        if isinstance(template_data, np.ndarray):
            return template_data
        raw = None
        if isinstance(template_data, str) and template_data.strip():
            try:
                raw = base64.b64decode(template_data)
            except Exception:
                raw = None
        elif isinstance(template_data, (bytes, bytearray)):
            raw = bytes(template_data)
        if raw:
            arr = np.frombuffer(raw, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                return img
        if template_path:
            img = cv2.imread(template_path)
            if img is not None:
                return img
        return None

    @staticmethod
    def ndarray_to_base64(img_bgr, compress_jpeg=True, quality=80):
        """把 BGR 数组编码为 base64 字符串（可选 JPEG 压缩以减小体积）。"""
        if compress_jpeg:
            ok, buf = cv2.imencode('.jpg', img_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
        else:
            ok, buf = cv2.imencode('.png', img_bgr)
        if not ok:
            return None
        return base64.b64encode(buf.tobytes()).decode('ascii')

    # ---------------- 模板匹配 ----------------
    def match_from_array(self, screen_img, template_img, confidence=None,
                         search_region=None, count=1):
        """在 screen_img（或 search_region 裁剪）中匹配模板数组。

        search_region: 相对 screen 的 (x, y, w, h)，用于限制搜索区域。
        count: 需要返回的最佳匹配数量。
        返回列表 [{center, top_left, size, max_val}] 或空列表。
        """
        src = screen_img
        ox = oy = 0
        if search_region:
            x, y, w, h = search_region
            src = screen_img[y:y + h, x:x + w]
            ox, oy = x, y

        th, tw = template_img.shape[:2]
        limit = max(count, 1)
        results = []
        # 逐步剔除已匹配区域，支持多模板结果
        work = src.copy()
        try:
            for _ in range(limit):
                if work.shape[0] < th or work.shape[1] < tw:
                    break
                res = cv2.matchTemplate(work, template_img, self.method)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                conf = confidence if confidence is not None else self.confidence
                if max_val < conf:
                    break
                x, y = max_loc
                center = (ox + x + tw // 2, oy + y + th // 2)
                results.append({
                    'center': center,
                    'top_left': (ox + x, oy + y),
                    'size': (tw, th),
                    'max_val': float(max_val),
                })
                # 遮掉已匹配区域，避免重复
                x = max(0, x - tw); y = max(0, y - th)
                w = min(work.shape[1], x + tw * 2) - x
                h = min(work.shape[0], y + th * 2) - y
                work[y:y + h, x:x + w] = 0
        except Exception:
            pass
        return results

    def find_on_screen(self, template_path, confidence=None, region=None, count=1):
        """全屏匹配（兼容旧接口）。返回最佳中心坐标或 None。"""
        screen = _screenshot_to_bgr()
        template = self.read_template_source(template_path)
        if template is None:
            raise FileNotFoundError(f"模板图片不存在: {template_path}")
        res = self.match_from_array(screen, template, confidence, region, count)
        return res[0]['center'] if res else None

    def find_on_screen_array(self, template_img, confidence=None, region=None, count=1):
        """全屏匹配模板数组，返回结果列表。"""
        screen = _screenshot_to_bgr()
        return self.match_from_array(screen, template_img, confidence, region, count)

    def find_on_window(self, window, template_path, confidence=None, count=1):
        """在指定窗口内匹配（返回屏幕绝对坐标列表）。窗口为 uiautomation 控件。"""
        rect = self.window_manager.get_window_rect(window)
        if not rect:
            return []
        left, top, right, bottom = rect
        screen = _screenshot_to_bgr((left, top, right - left, bottom - top))
        template = self.read_template_source(template_path)
        if template is None:
            raise FileNotFoundError(f"模板图片不存在: {template_path}")
        results = self.match_from_array(screen, template, confidence, count=count)
        for r in results:
            cx, cy = r['center']
            r['center'] = (cx + left, cy + top)
        return results

    def find_on_window_array(self, window, template_img, confidence=None, count=1):
        rect = self.window_manager.get_window_rect(window)
        if not rect:
            return []
        left, top, right, bottom = rect
        screen = _screenshot_to_bgr((left, top, right - left, bottom - top))
        results = self.match_from_array(screen, template_img, confidence, count=count)
        for r in results:
            cx, cy = r['center']
            r['center'] = (cx + left, cy + top)
        return results

    # ---------------- 后台离屏识别（PrintWindow） ----------------
    def hwnd_of(self, window):
        """统一解析窗口句柄。"""
        return _hwnd_of(window)

    def capture_window_offscreen(self, window_or_hwnd):
        """离屏抓取窗口客户区，返回 (BGR ndarray, (w, h))。"""
        return capture_window_offscreen(_hwnd_of(window_or_hwnd))

    def find_on_window_offscreen(self, window_or_hwnd, template_img,
                                 confidence=None, count=1):
        """PrintWindow 离屏抓窗口客户区做模板匹配。

        结果坐标基于【客户区】原点（左上角为 0,0），可直接用于「鼠标点击」的
        「相对窗口客户区」后台点击。
        """
        hwnd = _hwnd_of(window_or_hwnd)
        if not hwnd:
            raise RuntimeError('后台识别需要有效的窗口句柄')
        img, (w, h) = capture_window_offscreen(hwnd)
        if img is None or img.size == 0:
            raise RuntimeError('后台离屏抓取窗口内容失败（窗口可能不支持 PrintWindow）')
        results = self.match_from_array(img, template_img, confidence, count=count)
        return results, (w, h)

    def find_color_points_offscreen(self, window_or_hwnd, points,
                                    tolerance=30, count=1):
        """离屏窗口客户区内颜色定位，结果坐标基于客户区。"""
        hwnd = _hwnd_of(window_or_hwnd)
        if not hwnd:
            raise RuntimeError('后台识别需要有效的窗口句柄')
        img, (w, h) = capture_window_offscreen(hwnd)
        if img is None or img.size == 0:
            raise RuntimeError('后台离屏抓取窗口内容失败（窗口可能不支持 PrintWindow）')
        hits = self.find_color_points(points, tolerance, screen_img=img, count=count)
        return hits, (w, h)

    # ---------------- 颜色定位 ----------------
    @staticmethod
    def capture_screen(region=None):
        """返回 BGR 屏幕数组。"""
        return _screenshot_to_bgr(region)

    @staticmethod
    def pixel_bgr(point, screen_img=None):
        """返回屏幕坐标处 BGR 颜色 (b,g,r)；screen_img 提供时在其上取值（相对坐标）。"""
        if screen_img is not None:
            x, y = int(point[0]), int(point[1])
            if 0 <= y < screen_img.shape[0] and 0 <= x < screen_img.shape[1]:
                b, g, r = screen_img[y, x]
                return int(b), int(g), int(r)
            return None
        img = _screenshot_to_bgr((point[0], point[1], 1, 1))
        if img is None or img.size == 0:
            return None
        b, g, r = img[0, 0]
        return int(b), int(g), int(r)

    def find_color_points(self, points, tolerance=30, region=None, count=1,
                          screen_img=None):
        """在屏幕上寻找颜色点组合的基准坐标。

        points: [{dx, dy, r, g, b}]，第一个点为基准 (dx=dy=0)。
        tolerance: 每通道允许的颜色偏差。
        region: (x, y, w, h) 限制搜索范围；None 为全屏。
        screen_img: 可选，供批量测试复用屏幕数组。
        返回 [{base_center, base_pt, max_mismatch, matched}] 或空列表。
        """
        if not points:
            return []
        base = points[0]
        rest = points[1:]
        if screen_img is None:
            screen_img = _screenshot_to_bgr(region)
        ox = oy = 0
        search = screen_img
        if region:
            rx, ry, rw, rh = region
            ox, oy = rx, ry
            search = screen_img[ry:ry + rh, rx:rx + rw]
        h, w = search.shape[:2]
        candidates = []
        for py in range(h):
            row = search[py]
            for px in range(w):
                b, g, r = int(row[px, 0]), int(row[px, 1]), int(row[px, 2])
                base_dev = max(abs(r - base['r']), abs(g - base['g']), abs(b - base['b']))
                if base_dev > tolerance:
                    continue
                score = base_dev
                matched = True
                max_dev = base_dev
                for pt in rest:
                    yy = py + pt['dy']
                    xx = px + pt['dx']
                    if not (0 <= xx < w and 0 <= yy < h):
                        matched = False
                        break
                    pb, pg, pr = int(search[yy, xx, 0]), int(search[yy, xx, 1]), int(search[yy, xx, 2])
                    dev = max(abs(pr - pt['r']), abs(pg - pt['g']), abs(pb - pt['b']))
                    max_dev = max(max_dev, dev)
                    if dev > tolerance:
                        matched = False
                        break
                    score += dev
                candidates.append({
                    'base_pt': (ox + px, oy + py),
                    'base_center': (ox + px, oy + py),
                    'max_dev': float(max_dev),
                    'matched': matched,
                })
        matched_list = [c for c in candidates if c['matched']]
        if not matched_list:
            return []
        matched_list.sort(key=lambda c: c['max_dev'])
        return matched_list[:max(count, 1)]