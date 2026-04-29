# -*- coding: utf-8 -*-
"""
workflow.py
作者: reformLi
创建日期: 2026/4/25
最后修改: 2026/4/25
版本: 1.0.0

功能描述: 工作流数据模型
"""
# core/workflow.py
import json
from datetime import datetime


class WorkflowModel:
    """工作流数据模型（纯数据，不包含行为）"""

    def __init__(self, name="Untitled", version="1.0"):
        self.name = name
        self.version = version
        self.created_at = datetime.now().isoformat()
        self.nodes = []          # list of node dicts
        self.connections = []    # list of connection dicts

    def to_dict(self):
        """序列化为字典"""
        return {
            "version": self.version,
            "name": self.name,
            "created_at": self.created_at,
            "nodes": self.nodes,
            "connections": self.connections,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典反序列化"""
        model = cls(
            name=data.get("name", "Untitled"),
            version=data.get("version", "1.0"),
        )
        model.created_at = data.get("created_at", datetime.now().isoformat())
        model.nodes = data.get("nodes", [])
        model.connections = data.get("connections", [])
        return model

    def save_to_file(self, filepath: str):
        """保存为 JSON 文件"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, filepath: str):
        """从 JSON 文件加载"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)