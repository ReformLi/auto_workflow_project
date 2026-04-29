# -*- coding: utf-8 -*-
"""
window_manager.py
作者: reformLi
创建日期: 2026/4/27
最后修改: 2026/4/27
版本: 1.0.0

功能描述: 窗口管理器
"""
# automation/window_manager.py
import time
import uiautomation as auto


class WindowManager:
    """窗口管理器，专注于窗口层面的操作"""

    DEFAULT_TIMEOUT = 10.0

    def __init__(self):
        auto.SetGlobalSearchTimeout(self.DEFAULT_TIMEOUT)

    # ---------- 1. 查找窗口 ----------
    def find_window(self, title=None, class_name=None, automation_id=None, timeout=None):
        """
        查找匹配的顶层窗口。
        参数:
            title (str): 窗口标题（使用 Name 属性进行匹配）。
        Returns:
            Control or None: 找到的窗口控件，如果未找到则返回 None。
        """
        if timeout is not None:
            auto.SetGlobalSearchTimeout(timeout)
        try:
            # 直接利用构造函数查找，清晰且符合库的惯用法
            # WindowControl 默认在桌面层级(searchDepth=1)的第一层进行查找
            window = auto.WindowControl(Name=title)

            # 验证查找结果是否存在
            if window.Exists():
                return window
            return None
        except Exception:
            return None
        finally:
            if timeout is not None:
                auto.SetGlobalSearchTimeout(self.DEFAULT_TIMEOUT)  # 恢复默认超时

    # ---------- 2. 等待窗口 ----------
    def wait_window(self, title=None, class_name=None, automation_id=None, timeout=None, interval=0.5):
        """等待指定窗口出现，轮询检查"""
        if timeout is None:
            timeout = self.DEFAULT_TIMEOUT
        end_time = time.time() + timeout
        while time.time() < end_time:
            window = self.find_window(title=title, class_name=class_name, automation_id=automation_id, timeout=0.5)
            if window:
                return window
            time.sleep(interval)
        return None

    # ---------- 3. 窗口操作 ----------
    def activate_window(self, window):
        """激活（置前）窗口"""
        try:
            # 调用库封装好的 SetFocus
            window.SetFocus()
            # 也可以调用更底层的 SetForeground，但 SetFocus 通常足够并更简洁
            # 如果窗口最小化，可以尝试调用 window.GetWindowPattern().SetWindowVisualState(1)
            return True
        except Exception:
            return False

    def close_window(self, window):
        """通过 UIA 模式关闭窗口"""
        try:
            # 尝试通过 WindowPattern 关闭，这是最标准的 UIA 方式
            window.GetWindowPattern().Close()
            return True
        except Exception:
            try:
                # 失败时打印一条警告或直接忽略
                print(f"警告：通过 UIA 模式关闭窗口失败，尝试发送 Alt+F4。")
            except:
                pass
            return False

    # ---------- 4. 获取窗口信息 ----------
    def get_window_rect(self, window):
        """返回窗口矩形 (left, top, right, bottom)"""
        try:
            rect = window.BoundingRectangle
            return (rect.left, rect.top, rect.right, rect.bottom)
        except Exception:
            return None

    def get_window_center(self, window):
        """返回窗口中心点屏幕坐标 (x, y)"""
        rect = self.get_window_rect(window)
        if rect:
            return ((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)
        return None