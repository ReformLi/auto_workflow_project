# -*- coding: utf-8 -*-
"""
window_manager.py
作者: reformLi
创建日期: 2026/4/27
最后修改: 2026/9/4
版本: 2.0.0

功能描述: 窗口管理器——窗口查找（标题/类名/进程名组合过滤）、等待、激活、关闭、信息获取
"""
import ctypes
import re
import time
from ctypes import wintypes

import uiautomation as auto
import win32gui
import win32process

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# kernel32 进程查询函数（用于按进程名过滤窗口）
_kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
_kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
_kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


class WindowManager:
    """窗口管理器，专注于窗口层面的操作"""

    DEFAULT_TIMEOUT = 10.0

    def __init__(self):
        auto.SetGlobalSearchTimeout(self.DEFAULT_TIMEOUT)

    # ---------- 1. 查找窗口 ----------
    def find_window(self, title=None, match_mode='contains', class_name=None,
                    process_name=None, timeout=None):
        """查找匹配的顶层窗口（标题/类名/进程名组合过滤，条件间为 AND 关系）

        Args:
            title (str): 窗口标题，按 match_mode 指定的方式匹配
            match_mode (str): 'exact' 完全匹配 / 'contains' 包含 / 'regex' 正则（search）
            class_name (str): 窗口类名，精确匹配（可选）
            process_name (str): 进程名如 'notepad.exe'，不区分大小写、可省略 .exe（可选）
            timeout (float): 等待超时秒数；None 或 0 表示单次查找不等待

        Returns:
            uiautomation.Control 或 None: 找到的窗口控件；正则表达式非法时抛出 ValueError
        """
        if not any([title, class_name, process_name]):
            return None

        pattern = None
        if title and match_mode == 'regex':
            try:
                pattern = re.compile(title)
            except re.error as e:
                raise ValueError(f"无效的窗口标题正则表达式: {title}（{e}）")

        deadline = time.time() + (timeout or 0)
        while True:
            hwnd = self._match_one(title, match_mode, pattern,
                                   class_name, process_name)
            if hwnd:
                try:
                    return auto.ControlFromHandle(hwnd)
                except Exception:
                    return None
            if time.time() >= deadline:
                return None
            time.sleep(0.3)

    def _match_one(self, title, match_mode, pattern, class_name, process_name):
        """枚举可见顶层窗口，返回第一个满足全部过滤条件的句柄"""
        proc_key = process_name.lower().rsplit('.', 1)[0] if process_name else None
        for hwnd, w_title, w_class, pid in self._enumerate_windows():
            if title:
                if match_mode == 'exact':
                    if w_title != title:
                        continue
                elif match_mode == 'regex':
                    if not pattern.search(w_title):
                        continue
                else:  # contains
                    if title not in w_title:
                        continue
            if class_name and w_class != class_name:
                continue
            if proc_key is not None:
                p_name = self._get_process_name(pid)
                if not p_name or p_name.lower().rsplit('.', 1)[0] != proc_key:
                    continue
            return hwnd
        return None

    @classmethod
    def _enumerate_windows(cls):
        """枚举所有可见且有标题的窗口（含顶层窗口及其可见子窗口）
        → [(hwnd, title, class_name, pid)]

        说明：UWP 应用（如计算器）点击捕获命中的是内层的
        ``Windows.UI.Core.CoreWindow``（顶层 ``ApplicationFrameWindow`` 的子窗口），
        只枚举顶层会找不到，故把可见子窗口一并纳入。
        """
        results = []

        def _collect(hwnd):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return
                title = win32gui.GetWindowText(hwnd)
                if not title:
                    return
                class_name = win32gui.GetClassName(hwnd)
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                results.append((hwnd, title, class_name, pid))
            except Exception:
                pass  # 单个窗口枚举失败不影响整体

        def _on_window(hwnd, _):
            _collect(hwnd)
            cls._collect_descendants(hwnd, results, _collect, depth=4)

        try:
            win32gui.EnumWindows(_on_window, None)
        except Exception:
            pass
        return results

    @staticmethod
    def _collect_descendants(hwnd, results, collect, depth):
        """递归收集 hwnd 的可见且有标题的子窗口，深度不超过 depth"""
        if depth <= 0:
            return
        children_window = []

        def _child(child, _):
            children_window.append(child)
            return True

        try:
            win32gui.EnumChildWindows(hwnd, _child, None)
        except Exception:
            children_window = []
        for child in children_window:
            collect(child)
            WindowManager._collect_descendants(child, results, collect, depth - 1)

    @staticmethod
    def _get_process_name(pid):
        """通过 PID 查询进程名（如 notepad.exe），失败返回 None"""
        try:
            handle = _kernel32.OpenProcess(
                _PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
            if not handle:
                return None
            try:
                buf = ctypes.create_unicode_buffer(1024)
                size = wintypes.DWORD(len(buf))
                if _kernel32.QueryFullProcessImageNameW(handle, 0, buf,
                                                        ctypes.byref(size)):
                    return buf.value.rsplit('\\', 1)[-1]
            finally:
                _kernel32.CloseHandle(handle)
        except Exception:
            return None
        return None

    # ---------- 2. 等待窗口 ----------
    def wait_window(self, title=None, match_mode='contains', class_name=None,
                    process_name=None, timeout=None):
        """等待指定窗口出现（内部轮询查找），超时返回 None"""
        if timeout is None:
            timeout = self.DEFAULT_TIMEOUT
        return self.find_window(title=title, match_mode=match_mode,
                                class_name=class_name,
                                process_name=process_name, timeout=timeout)

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

    # ---------- 5. 捕获窗口信息（取色器式） ----------
    def capture_window_info(self, point):
        """返回屏幕坐标 point 处顶层窗口的 标题/类名/进程名。

        Args:
            point (tuple): 屏幕像素坐标 (x, y)。

        Returns:
            dict 或 None: {'title', 'class_name', 'process_name'}；
            该点无有效顶层窗口时返回 None。
        """
        try:
            hwnd = win32gui.WindowFromPoint(point)
            if not hwnd:
                return None
            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return {
                'title': title,
                'class_name': class_name,
                'process_name': self._get_process_name(pid),
            }
        except Exception:
            return None
