# -*- coding: utf-8 -*-
"""实机诊断：确认高DPI坐标错位 + 验证引擎在真实屏幕出字。运行后把输出贴回来。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QGuiApplication

app = QApplication([])

from automation.ocr import OcrEngine
from automation.image_finder import ImageFinder

dpr = QGuiApplication.primaryScreen().devicePixelRatio()
geo = QGuiApplication.primaryScreen().availableGeometry()
print(f"Qt 屏幕可用(逻辑): {geo.width()}x{geo.height()}")

try:
    import pyautogui
    print(f"pyautogui 屏幕(物理): {pyautogui.size().width}x{pyautogui.size().height}")
except Exception as e:
    print("pyautogui.size 失败:", e)

print(f"DPR(devicePixelRatio) = {dpr}   <-- 若 >1 则坐标会错位")

engine = OcrEngine()
print("tesseract:", engine._tesseract, "| 语言:", sorted(engine.list_languages()))

# 全屏截图识别：若真机桌面有文字，这里应能吐出字
full = ImageFinder.capture_screen()
print(f"全屏截图 shape: {full.shape}")
r = engine.recognize(full, lang='chi_sim')
print(f"全屏识别 text={r['text']!r}  results数={len(r['results'])}")

# 用 Qt 逻辑坐标(100,100,300,100)直接作为 pyautogui 区域截图
region = (100, 100, 300, 100)  # 逻辑坐标
clip = ImageFinder.capture_screen(region)
print(f"逻辑(100,100,300,100)直接截 -> {clip.shape} 像素范围 min={clip.min()} max={clip.max()}")
# 若 DPR>1，物理区域应为 (100*dpr, ...) 才准
if dpr > 1:
    region_p = (int(100*dpr), int(100*dpr), int(300*dpr), int(100*dpr))
    clipp = ImageFinder.capture_screen(region_p)
    rc = engine.recognize(clipp, lang='chi_sim')
    print(f"若按 DPR 换算截物理区域 -> {clipp.shape} 识别 text={rc['text']!r}")

print("DONE")