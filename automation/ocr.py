# -*- coding: utf-8 -*-
"""
ocr.py
功能描述: 文字识别（OCR）核心——直接调用系统已安装的 Tesseract 可执行文件（子进程）。
- 零新增依赖：不依赖 pytesseract，通过 subprocess 调用 tesseract.exe。
- 支持从 BGR ndarray 截图识别，预处理（灰度/二值化），TSV 结构化输出。
- 输出：整段文本 + 文本块列表（内容、坐标、置信度）。
"""
import logging
import os
import shutil
import subprocess
import tempfile

import cv2

_logger = logging.getLogger(__name__)

# 常见安装路径（按优先级尝试），其余交给 PATH 环境变量
_TESSERACT_HINTS = [
    r'D:\Tesseract-OCR\tesseract.exe',
]


def find_tesseract():
    """定位 tesseract 可执行文件路径；找不到返回 None。"""
    for hint in _TESSERACT_HINTS:
        if hint and os.path.isfile(hint):
            return hint
    return shutil.which('tesseract')


class OcrEngine:
    """基于 Tesseract 的文字识别器"""

    def __init__(self):
        self._tesseract = find_tesseract()
        if not self._tesseract:
            _logger.error('未找到 Tesseract：请安装后设置环境变量，或放置到 %s', _TESSERACT_HINTS[0])

    # ---------------- 语言 ----------------
    def available(self):
        """tesseract 是否可用（可执行文件存在）"""
        return bool(self._tesseract)

    def list_languages(self):
        """返回可用语言代码集合（如 {'chi_sim','eng','eng'}）。失败返回空集。"""
        if not self._tesseract:
            return set()
        try:
            out = subprocess.run([self._tesseract, '--list-langs'],
                                 capture_output=True, text=True, timeout=15)
            langs = set()
            for line in (out.stdout or '').splitlines():
                line = line.strip()
                if line and not line.lower().startswith('list of'):
                    langs.add(line)
            return langs
        except Exception as e:
            _logger.warning('检测 Tesseract 语言失败: %s', e)
            return set()

    def _resolve_lang(self, lang):
        """剔除语言组合中缺失的代码，避免 tesseract 报错。全部缺失时回落可用语言。"""
        langs = set(self.list_languages()) or {'chi_sim'}
        codes = [c.strip() for c in (lang or '').split('+') if c.strip()]
        resolved = []
        for c in codes:
            if c in langs:
                resolved.append(c)
            else:
                _logger.warning('Tesseract 缺少语言包「%s」，已忽略（若需该语言请安装 tessdata）', c)
        if not resolved:
            resolved = sorted(langs)
            if not resolved:
                resolved = ['chi_sim']
            _logger.warning('所选语言均不可用，回落为: %s', '+'.join(resolved))
        return '+'.join(resolved)

    # ---------------- 识别 ----------------
    def recognize(self, image_bgr, lang='chi_sim', psm=3, min_conf=0, preprocess='无'):
        """识别图像中的文字。

        Args:
            image_bgr: BGR ndarray 截图。
            lang: 语言代码，可含 '+'（如 'chi_sim+eng'）。
            psm: tesseract 页面分割模式（常用 3 自动 / 7 单行 / 10 单字 / 11 稀疏）。
            min_conf: 最低置信度（0-100，0 表示不过滤）。
            preprocess: 预处理，'无' / '灰度' / '二值化'。

        Returns:
            dict: {'text': str, 'time': float, 'results': [{text,x,y,w,h,conf}, ...]}。
            图像为空或识别失败时 text 为空串、results 为空列表。
        """
        if not self._tesseract:
            raise RuntimeError('未找到 Tesseract，无法执行 OCR 识别')

        img = self._preprocess(image_bgr, preprocess)
        if img is None or img.size == 0:
            return {'text': '', 'time': 0.0, 'results': []}

        # 写入临时 PNG（tesseract 子进程需要文件路径）
        tmp_file = None
        try:
            ok, buf = cv2.imencode('.png', img)
            if not ok:
                return {'text': '', 'time': 0.0, 'results': []}
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tf:
                tf.write(buf.tobytes())
                tmp_file = tf.name

            resolved_lang = self._resolve_lang(lang)
            cmd = [self._tesseract, tmp_file, 'stdout', '-l', resolved_lang,
                   '--psm', str(psm), 'tsv']
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return self._parse_tsv(out.stdout or '', min_conf)
        except subprocess.TimeoutExpired:
            _logger.error('OCR 识别超时')
            return {'text': '', 'time': 0.0, 'results': []}
        except Exception as e:
            _logger.error('OCR 识别失败: %s', e)
            return {'text': '', 'time': 0.0, 'results': []}
        finally:
            if tmp_file and os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass

    @staticmethod
    def _preprocess(img, mode):
        """灰度 / 二值化预处理；返回处理后的图，mode 为 '无' 时原样返回。"""
        mode = mode or '无'
        if mode == '灰度':
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if mode == '二值化':
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, th = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            return th
        return img

    @staticmethod
    def _parse_tsv(tsv_text, min_conf=0):
        """解析 Tesseract TSV 输出为结构化结果。

        TSV 表头: level page_num block_num par_num line_num word_num left top width height conf text
        仅取 word 级（level==5）词条，过滤 conf 并拼接文本。
        """
        results = []
        lines = tsv_text.splitlines()
        if len(lines) < 2:
            return {'text': '', 'time': 0.0, 'results': []}
        header = lines[0].split('\t')
        idx = {name: i for i, name in enumerate(header)}

        word_parts = []
        for line in lines[1:]:
            cells = line.split('\t')
            try:
                if int(cells[idx['level']]) != 5:
                    continue
                conf_s = cells[idx['conf']].strip()
                if not conf_s:
                    continue
                conf = float(conf_s)  # TSV conf 可能含小数
                if conf < 0 or conf < min_conf:
                    continue
                text = cells[idx['text']].rstrip() if len(cells) > idx['text'] else ''
                if not text:
                    continue
            except (ValueError, IndexError):
                continue
            try:
                x = int(cells[idx['left']]); y = int(cells[idx['top']])
                w = int(cells[idx['width']]); h = int(cells[idx['height']])
            except (ValueError, IndexError):
                x = y = w = h = 0
            results.append({'text': text, 'x': x, 'y': y, 'w': w, 'h': h,
                            'conf': conf})
            word_parts.append(text)

        return {'text': ''.join(word_parts), 'time': 0.0, 'results': results}