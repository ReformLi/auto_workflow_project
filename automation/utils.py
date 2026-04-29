# -*- coding: utf-8 -*-
"""
utils.py
作者: reformLi
创建日期: 2026/4/28
最后修改: 2026/4/28
版本: 1.0.0

功能描述: 自动化模块的通用工具函数
"""
# automation/utils.py
"""
自动化工具函数：等待条件、重试装饰器、截图、坐标格式化等。
所有函数均保持纯 Python 实现，不依赖特定后端，可在其他自动化子模块中安全使用。
"""
import time
from functools import wraps

# ---------- 等待/重试 ----------

def wait_until(condition, timeout=10.0, interval=0.5, on_timeout=None):
    """
    轮询等待条件函数返回 True。
    :param condition: 无参可调用对象，返回 bool
    :param timeout: 超时秒数
    :param interval: 轮询间隔
    :param on_timeout: 超时时的回调函数（可选）
    :return: 成功返回 True，超时返回 False
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        if condition():
            return True
        time.sleep(interval)
    if on_timeout:
        on_timeout()
    return False


def retry(exception=Exception, tries=3, delay=1.0, backoff=2.0):
    """
    装饰器：函数抛出指定异常时自动重试。
    :param exception: 要捕获的异常类型或元组
    :param tries: 最大尝试次数（包括首次）
    :param delay: 首次重试前的等待秒数
    :param backoff: 延迟倍数（指数退避）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _tries = tries
            _delay = delay
            while True:
                try:
                    return func(*args, **kwargs)
                except exception as e:
                    _tries -= 1
                    if _tries == 0:
                        raise
                    time.sleep(_delay)
                    _delay *= backoff
        return wrapper
    return decorator


# ---------- 截图 ----------

def screenshot(region=None):
    """
    获取屏幕截图，返回 PIL Image 对象。
    :param region: 元组 (left, top, width, height)，None 表示全屏
    :return: PIL.Image
    """
    try:
        from PIL import ImageGrab
    except ImportError:
        raise ImportError("请安装 Pillow: pip install Pillow")
    return ImageGrab.grab(bbox=region)


# ---------- 坐标/格式化 ----------

def point_to_str(point):
    """将 (x, y) 坐标转为字符串，方便日志输出"""
    return f"({point[0]}, {point[1]})" if point else "None"

def clip_point_to_rect(point, rect):
    """
    将点裁剪到矩形区域内。
    rect: (left, top, right, bottom)
    返回 (x, y) 保证在矩形内。
    """
    x, y = point
    left, top, right, bottom = rect
    x = max(left, min(x, right))
    y = max(top, min(y, bottom))
    return (x, y)