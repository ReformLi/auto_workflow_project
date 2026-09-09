# -*- coding: utf-8 -*-
"""
node_subflow_widget.py
功能描述: 子工作流节点专用属性编辑器——路径输入 + 浏览按钮 + 文件状态检查。
接管 SUBFLOW_NODE 节点的属性页（见 ui/node_properties_panel.py）。
"""
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QWidget,
)

from ui import tokens


class SubflowNodeEditor(QWidget):
    """子工作流节点属性编辑器。"""

    def __init__(self, node, parent=None):
        super().__init__(parent)
        self.node = node
        self._updating = False    # 防止 setText 触发 textChanged 回写循环

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(8)

        # ── 路径行 ──
        row = QHBoxLayout()
        row.setSpacing(4)
        self._path_edit = QLineEdit(str(node.get_property('workflow_path') or ''))
        self._path_edit.setPlaceholderText(r'选择或粘贴 .awflow / .json 文件路径')
        self._path_edit.textChanged.connect(self._on_path_changed)
        browse_btn = QPushButton("浏览…")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet(self._secondary_button_style())
        browse_btn.clicked.connect(self._on_browse)
        row.addWidget(self._path_edit, 1)
        row.addWidget(browse_btn)
        layout.addLayout(row)

        # ── 文件状态 ──
        self._status = QLabel()
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        # ── 使用说明 ──
        tip = QLabel(
            "子工作流从其「开始」节点独立执行到结束。\n"
            "· 内部支持条件 / 循环 / 重试等全部节点\n"
            "· 内部失败未接 fail 分支时，走本节点的 fail 出口\n"
            "· 嵌套调用最多 8 层，防止自调用死循环\n"
            "· 执行期间可随时终止 / 暂停")
        tip.setWordWrap(True)
        tip.setStyleSheet(f"color:{tokens.DARK['text_dim']};font-size:12px;")
        layout.addWidget(tip)
        layout.addStretch(1)

        self._update_status()

    # ── 交互 ────────────────────────────────────────────
    def _on_browse(self):
        start_dir = os.path.dirname(self._path_edit.text().strip()) or ''
        path, _ = QFileDialog.getOpenFileName(
            self, "选择子工作流文件", start_dir,
            "工作流文件 (*.awflow *.json)")
        if path:
            self._path_edit.setText(os.path.normpath(path))

    def _on_path_changed(self, text):
        if self._updating:
            return
        self.node.set_property('workflow_path', text.strip())
        self._update_status()

    def _update_status(self):
        path = self._path_edit.text().strip()
        if not path:
            self._status.setText("尚未选择子工作流文件")
            self._status.setStyleSheet(f"color:{tokens.DARK['text_dim']};")
            return
        if not os.path.isfile(path):
            self._status.setText("✗ 文件不存在，请检查路径")
            self._status.setStyleSheet(f"color:{tokens.DARK['error']};")
            return
        try:
            from nodes._control_common import load_graph_dict
            graph_dict = load_graph_dict(path)
            count = len(graph_dict.get('nodes') or {})
            self._status.setText(f"✓ 文件有效，包含 {count} 个节点")
            self._status.setStyleSheet(f"color:{tokens.DARK['success']};")
        except Exception as e:
            self._status.setText(f"✗ 文件无法解析: {e}")
            self._status.setStyleSheet(f"color:{tokens.DARK['error']};")

    # ── 样式（与属性面板次要按钮一致） ────────────────────
    def _secondary_button_style(self):
        elev = tokens.DARK['bg_elevated']
        border = tokens.DARK['border_strong']
        text = tokens.DARK['text']
        return (f"QPushButton {{ background:{elev}; color:{text};"
                f"border:1px solid {border}; border-radius:4px;"
                f"padding:4px 12px; }}"
                f"QPushButton:hover {{ background:{tokens.DARK['bg_hover']}; }}")
