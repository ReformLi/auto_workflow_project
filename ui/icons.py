# -*- coding: utf-8 -*-
"""
icons.py
功能描述: qtawesome 矢量图标统一入口
         - 集中管理图标着色（全部取自 tokens，跟随主题）
         - 缓存 QIcon，避免重复构造
         - 提供节点库用的「圆角色块 + 图标」贴图
"""

import os
import tempfile
from functools import lru_cache

from PyQt5.QtCore import Qt, QRectF, QSize
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor

import qtawesome as qta

from ui import tokens

# QIcon 缓存：key = (name, color, color_active, color_disabled, scale)
_ICON_CACHE = {}


def icon(name: str, color: str = None, color_active: str = None,
         color_disabled: str = None, scale: float = 1.0) -> QIcon:
    """
    取矢量图标。
    :param name: qtawesome 图标名，如 'fa5s.play'
    :param color: 常态颜色（默认 text_2nd）
    :param color_active: hover/pressed 颜色（默认 text）
    :param color_disabled: 禁用颜色（默认 text_dim）
    :param scale: 图标在按钮内的缩放比例
    """
    color = color or tokens.DARK['text_2nd']
    color_active = color_active or tokens.DARK['text']
    color_disabled = color_disabled or tokens.DARK['text_dim']

    key = (name, color, color_active, color_disabled, scale)
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        return cached

    qicon = qta.icon(
        name,
        color=color,
        color_active=color_active,
        color_disabled=color_disabled,
        options=[{'scale_factor': scale}],
    )
    _ICON_CACHE[key] = qicon
    return qicon


def toolbar_icon(name: str, scale: float = 0.9) -> QIcon:
    """工具栏/菜单图标（统一 tint，禁用态自动变灰）"""
    return icon(name, scale=scale)


def tinted(name: str, color: str, scale: float = 1.0) -> QIcon:
    """指定单色图标（执行按钮状态色、级别徽章等场景）"""
    return icon(name, color=color, color_active=color, color_disabled=color, scale=scale)


def tile_pixmap(name: str, color: str, size: int = 28, radius: int = 6) -> QPixmap:
    """
    生成「分类色 15% 半透明底 + 分类色描边 + 分类色图标」的圆角方块贴图。
    用于节点库条目左侧图标位（见 UI_DESIGN.md §5.3）。
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    # 底色 + 描边
    painter.setBrush(QColor(tokens.rgba(color, 0.15)))
    painter.setPen(QColor(tokens.rgba(color, 0.40)))
    painter.drawRoundedRect(QRectF(0.5, 0.5, size - 1.0, size - 1.0), radius, radius)

    # 图标居中
    glyph_size = int(size * 0.55)
    qicon = tinted(name, color)
    glyph = qicon.pixmap(QSize(glyph_size, glyph_size))
    offset = (size - glyph_size) // 2
    painter.drawPixmap(offset, offset, glyph)

    painter.end()
    return pixmap


def tile_icon(name: str, color: str, size: int = 28, radius: int = 6) -> QIcon:
    """tile_pixmap 的 QIcon 版本"""
    return QIcon(tile_pixmap(name, color, size, radius))


@lru_cache(maxsize=64)
def node_icon_path(name: str, color: str = None, size: int = 28) -> str:
    """
    生成画布节点用的图标 PNG 路径。

    NodeGraphQt 的 BaseNode.set_icon() 只接受图片文件路径（内部 QPixmap(path)），
    因此把矢量字形落盘到系统临时目录（按 名称+颜色+尺寸 命名，存在即复用）。
    """
    color = color or tokens.DARK['bg_canvas']
    directory = os.path.join(tempfile.gettempdir(), 'auto_workflow_icons')
    os.makedirs(directory, exist_ok=True)

    file_name = f"{name.replace('.', '_').replace('-', '_')}_{color.lstrip('#')}_{size}.png"
    path = os.path.join(directory, file_name)
    if os.path.exists(path):
        return path

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    glyph = tinted(name, color).pixmap(QSize(size, size))
    painter.drawPixmap(0, 0, glyph)
    painter.end()
    pixmap.save(path, 'PNG')
    return path


def clear_cache():
    """主题切换时清空缓存（当前仅深色主题，预留）"""
    _ICON_CACHE.clear()
    node_icon_path.cache_clear()
