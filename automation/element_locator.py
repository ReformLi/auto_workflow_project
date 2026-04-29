# -*- coding: utf-8 -*-
"""
element_locator.py
作者: reformLi
创建日期: 2026/4/28
最后修改: 2026/4/28
版本: 1.0.0

功能描述: 控件定位器
"""
# automation/element_locator.py
import time
import uiautomation as auto

class ElementLocator:
    """UI 控件定位器（使用递归遍历控件树，不依赖 FindFirst）"""

    DEFAULT_TIMEOUT = 10.0
    DEFAULT_DEPTH  = 0xFFFFFFFF  # 无深度限制

    def __init__(self):
        auto.SetGlobalSearchTimeout(self.DEFAULT_TIMEOUT)

    # ----- 公开查找接口 -----
    def find_element(self, window, name=None, class_name=None,
                     automation_id=None, control_type=None,
                     depth=None, timeout=None):
        """
        在指定窗口（或桌面）下查找第一个匹配控件。
        如果 window 为 None，则从桌面根控件开始。
        """
        condition = self._build_condition(name, class_name, automation_id, control_type)
        search_root = window if window else auto.GetRootControl()
        try:
            if timeout is not None:
                auto.SetGlobalSearchTimeout(timeout)
            return self._find_first_recursive(search_root, condition, depth)
        finally:
            if timeout is not None:
                auto.SetGlobalSearchTimeout(self.DEFAULT_TIMEOUT)

    def find_elements(self, window, name=None, class_name=None,
                      automation_id=None, control_type=None,
                      depth=None, timeout=None):
        """查找所有匹配控件"""
        condition = self._build_condition(name, class_name, automation_id, control_type)
        search_root = window if window else auto.GetRootControl()
        try:
            if timeout is not None:
                auto.SetGlobalSearchTimeout(timeout)
            return self._find_all_recursive(search_root, condition, depth)
        finally:
            if timeout is not None:
                auto.SetGlobalSearchTimeout(self.DEFAULT_TIMEOUT)

    def wait_element(self, window, name=None, class_name=None,
                     automation_id=None, control_type=None,
                     timeout=None, interval=0.5):
        if timeout is None:
            timeout = self.DEFAULT_TIMEOUT
        end_time = time.time() + timeout
        while time.time() < end_time:
            elem = self.find_element(window, name, class_name,
                                     automation_id, control_type, timeout=0.5)
            if elem:
                return elem
            time.sleep(interval)
        return None

    def get_element_rect(self, element):
        try:
            r = element.BoundingRectangle
            return (r.left, r.top, r.right, r.bottom)
        except Exception:
            return None

    def get_element_center(self, element):
        rect = self.get_element_rect(element)
        if rect:
            return ((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)
        return None

    # ----- 内部递归实现 -----
    def _find_first_recursive(self, root, condition, max_depth, current_depth=0):
        """深度优先递归查找第一个匹配的控件"""
        if max_depth is not None and current_depth > max_depth:
            return None
        try:
            if condition(root):
                return root
        except Exception:
            pass
        # 递归子控件
        try:
            children = root.GetChildren()
        except Exception:
            children = []
        for child in children:
            result = self._find_first_recursive(child, condition, max_depth, current_depth + 1)
            if result:
                return result
        return None

    def _find_all_recursive(self, root, condition, max_depth, current_depth=0):
        """递归查找所有匹配控件"""
        results = []
        if max_depth is not None and current_depth > max_depth:
            return results
        try:
            if condition(root):
                results.append(root)
        except Exception:
            pass
        try:
            children = root.GetChildren()
        except Exception:
            children = []
        for child in children:
            results.extend(self._find_all_recursive(child, condition, max_depth, current_depth + 1))
        return results

    # ----- 条件构建（返回布尔回调） -----
    def _build_condition(self, name, class_name, automation_id, control_type):
        def condition(ctrl):
            if name is not None and ctrl.Name != name:
                return False
            if class_name is not None and ctrl.ClassName != class_name:
                return False
            if automation_id is not None and ctrl.AutomationId != automation_id:
                return False
            if control_type is not None:
                actual = ctrl.ControlTypeName
                if isinstance(control_type, str):
                    if actual.lower() != control_type.lower():
                        return False
                # 若将来需要支持数字 ID，可在此扩展
            return True
        return condition