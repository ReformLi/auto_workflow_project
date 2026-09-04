# -*- coding: utf-8 -*-
"""
status_bar.py
功能描述: 状态栏视图组件
         左侧 = 状态圆点 + 状态消息；右侧 = 定宽分栏指标（节点/连线/耗时/文件/缩放）
         见 UI_DESIGN.md §5.6
"""

from PyQt5.QtCore import Qt, QElapsedTimer, QTimer
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWidgets import QLabel

from ui import tokens

# 状态 → 圆点颜色 / 默认消息
_STATE_STYLE = {
    'idle':    ('text_dim', '就绪 — 从左侧节点库拖拽节点开始编排'),
    'running': ('success',  '工作流执行中…'),
    'paused':  ('warning',  '工作流已暂停'),
    'stopped': ('text_2nd', '工作流已停止'),
    'error':   ('error',    '工作流执行失败'),
    'success': ('success',  '工作流执行完成'),
}


class StatusBarView:
    """状态栏组装与刷新（宿主 QStatusBar 由主窗口传入）"""

    def __init__(self, status_bar):
        self._bar = status_bar
        self._state = 'idle'
        self._elapsed = QElapsedTimer()
        self._timing = False
        self._file_name = '未命名'
        self._dirty = False
        self._restore_timer = None
        self._ticker = None

        self._build()
        self.set_state('idle')

    # ── 构建 ────────────────────────────────────────────
    def _build(self):
        # 左侧：状态圆点 + 消息
        self._dot = QLabel()
        self._dot.setFixedSize(10, 10)
        self._dot.setCursor(Qt.PointingHandCursor)
        self._dot.setToolTip('当前执行状态')
        self._bar.addWidget(self._dot)

        self._message = QLabel()
        self._message.setObjectName('statusMessage')
        self._bar.addWidget(self._message, 1)

        # 右侧：定宽分栏指标（等宽数字保证上下对齐）
        self._mono = QFont(tokens.FONT_FAMILY_MONO, tokens.FONT_SIZE_UI - 1)
        fm = QFontMetrics(self._mono)

        self._values = {}
        self._nodes = self._add_metric('nodes', '节点', fm, '9999')
        self._connections = self._add_metric('connections', '连线', fm, '9999')
        self._elapsed_label = self._add_metric('elapsed', '耗时', fm, '999.9s')
        self._zoom = self._add_metric('zoom', '缩放', fm, '1000%')
        self._file = self._add_metric('file', '文件', fm, '未命名工作流.json')

        self._bar.addPermanentWidget(self._make_separator())
        self._refresh_elapsed('—')

    def _add_metric(self, key, label_text, fm, sample):
        """一个指标 = 标签 + 定宽数值；定宽按该指标的最宽形态取样，避免右对齐时裁字"""
        label = QLabel(label_text)
        label.setObjectName('statusLabel')
        value = QLabel()
        value.setObjectName('statusValue')
        value.setFont(self._mono)
        value.setFixedWidth(fm.horizontalAdvance(sample) + 8)
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._bar.addPermanentWidget(label)
        self._bar.addPermanentWidget(value)
        self._values[key] = value
        if key != 'file':
            self._bar.addPermanentWidget(self._make_separator())
        return value

    @staticmethod
    def _make_separator():
        sep = QLabel('·')
        sep.setObjectName('statusSep')
        return sep

    def _set_dot_color(self, token_key):
        color = tokens.DARK[token_key]
        self._dot.setStyleSheet(
            f'background-color: {color}; border-radius: 5px;'
        )

    # ── 对外接口 ────────────────────────────────────────
    def set_state(self, state, message=None):
        """切换执行状态（idle/running/paused/stopped/error/success）"""
        color_key, default_message = _STATE_STYLE.get(state, _STATE_STYLE['idle'])
        self._state = state
        self._set_dot_color(color_key)
        self.set_message(message or default_message)

        if state == 'running':
            if not self._timing:
                self._elapsed.start()
                self._timing = True
            self._start_elapsed_ticker()
        elif state in ('paused',):
            self._stop_elapsed_ticker()
        else:
            self._stop_elapsed_ticker()
            if state in ('stopped', 'error', 'success'):
                self._refresh_elapsed(self._current_elapsed_text())

    def set_message(self, text, timeout_ms=0):
        """设置状态消息；timeout_ms>0 时到期恢复为状态默认消息"""
        self._message.setText(text)
        if timeout_ms > 0:
            if self._restore_timer:
                self._restore_timer.stop()
            self._restore_timer = QTimer(self._message)
            self._restore_timer.setSingleShot(True)
            self._restore_timer.timeout.connect(
                lambda: self._message.setText(_STATE_STYLE.get(self._state, _STATE_STYLE['idle'])[1])
            )
            self._restore_timer.start(timeout_ms)

    def set_counts(self, node_count, connection_count):
        """刷新节点/连线计数"""
        self._values['nodes'].setText(str(node_count))
        self._values['connections'].setText(str(connection_count))

    def set_zoom(self, scale):
        """刷新缩放百分比（传入 NodeGraph.get_zoom() 的倍数）"""
        try:
            percent = int(round(float(scale) * 100))
        except (TypeError, ValueError):
            percent = 100
        self._values['zoom'].setText(f'{percent}%')

    def set_file(self, file_path, dirty=False):
        """刷新当前文件名（None 表示未命名）"""
        self._dirty = dirty
        if file_path:
            name = str(file_path).replace('\\', '/').rsplit('/', 1)[-1]
        else:
            name = '未命名'
        self._file_name = name
        self._values['file'].setText(f'{name}{" *" if dirty else ""}')
        self._values['file'].setToolTip(str(file_path or ''))

    def set_dirty(self, dirty):
        """标记/清除未保存状态"""
        self._dirty = bool(dirty)
        current = self._values['file'].text()
        base = current.rstrip(' *')
        self._values['file'].setText(f'{base}{" *" if self._dirty else ""}')

    # ── 耗时计时 ────────────────────────────────────────
    def _current_elapsed_text(self):
        if not self._timing:
            return '—'
        return f'{self._elapsed.elapsed() / 1000:.1f}s'

    def _refresh_elapsed(self, text):
        self._values['elapsed'].setText(text)

    def _start_elapsed_ticker(self):
        if getattr(self, '_ticker', None) is None:
            self._ticker = QTimer(self._bar)
            self._ticker.setInterval(100)
            self._ticker.timeout.connect(lambda: self._refresh_elapsed(self._current_elapsed_text()))
        if not self._ticker.isActive():
            self._ticker.start()

    def _stop_elapsed_ticker(self):
        if getattr(self, '_ticker', None) is not None and self._ticker.isActive():
            self._ticker.stop()

    def reset_elapsed(self):
        """清零耗时显示（新建/打开工作流时调用）"""
        self._timing = False
        self._stop_elapsed_ticker()
        self._refresh_elapsed('—')
