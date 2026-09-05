# -*- coding: utf-8 -*-
"""
awflow.py
功能描述: .awflow 打包工作流格式（ZIP 容器）
         ├── workflow.json       # 节点图数据（NodeGraphQt serialize_session 结果）
         └── resources/images/   # 图片节点模板资源
设计要点:
- JSON 保持轻量：图片节点序列化时把 Base64 清空，改存 resources/ 内相对路径。
- 加载时从包内读回图片并转回 Base64 内嵌到节点，内存自洽、可再次保存，无临时文件。
- 兼容旧 .json：仍由 GraphSerializerMixin 走原逻辑；此处额外提供相对资源路径重定位，
  使「JSON + 外部资源文件夹」导出可被直接打开。
"""
import base64
import copy
import json
import logging
import os
import zipfile

_logger = logging.getLogger(__name__)

_RESOURCES_PREFIX = 'resources/'
_IMAGE_NODE_KEY = 'template_data'   # 仅查找图片节点带此自定义属性


def is_awflow(file_path):
    """按扩展名判断是否为打包格式（.awflow，不区分大小写）"""
    return str(file_path).lower().endswith('.awflow')


def _is_image_node(node_dict):
    custom = node_dict.get('custom') or {}
    return _IMAGE_NODE_KEY in custom or 'template_path' in custom


def _node_image_bytes(node_dict, base_dir=None):
    """取节点模板图片字节：内嵌 Base64 优先，否则读文件。无法获得返回 None。"""
    custom = node_dict.get('custom') or {}
    data = custom.get(_IMAGE_NODE_KEY) or ''
    if data:
        try:
            return base64.b64decode(data)
        except Exception:
            return None
    path = custom.get('template_path') or ''
    if not path:
        return None
    if base_dir is not None and not os.path.isabs(path):
        path = os.path.join(base_dir, path)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'rb') as f:
            return f.read()
    except Exception:
        return None


def _prepare_for_resources(graph_dict, base_dir=None):
    """收集图片资源并改写节点 custom（template_data 清空、template_path 指向包内相对路径）。
    返回 (graph_dict, {相对路径: bytes})。base_dir 用于解析外部相对路径。
    注意：NodeGraphQt serialize_session 返回的 dict 与节点属性共享引用，必须先深拷贝，
    避免改写污染节点内存状态（否则再次保存时资源会丢失）。"""
    graph_dict = copy.deepcopy(graph_dict)
    resources = {}
    idx = 0
    for node in (graph_dict.get('nodes') or {}).values():
        if not _is_image_node(node):
            continue
        data = _node_image_bytes(node, base_dir)
        if data is None:
            _logger.warning('图片节点资源不可用，已跳过: %s', node.get('name', ''))
            continue
        idx += 1
        rel = '{0}images/template{1}.png'.format(_RESOURCES_PREFIX, idx)
        resources[rel] = data
        custom = node.setdefault('custom', {})
        custom[_IMAGE_NODE_KEY] = ''
        custom['template_path'] = rel
    return graph_dict, resources


def _dump_json(graph_dict):
    """与 NodeGraphQt save_session 保持一致的序列化参数"""
    def default(obj):
        if isinstance(obj, set):
            return list(obj)
        return obj

    return json.dumps(graph_dict, indent=2, separators=(',', ':'),
                      ensure_ascii=False, default=default)


def pack_workflow(graph_dict, file_path):
    """将图数据保存为 .awflow（ZIP：workflow.json + resources/images/*）"""
    prepared, resources = _prepare_for_resources(graph_dict)
    with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('workflow.json', _dump_json(prepared))
        for rel, data in resources.items():
            zf.writestr(rel, data)
    return True


def unpack_workflow(file_path):
    """读取 .awflow：包内资源转回 Base64 内嵌到节点，返回可直接 deserialize 的图数据"""
    with zipfile.ZipFile(file_path, 'r') as zf:
        graph_dict = json.loads(zf.read('workflow.json').decode('utf-8'))
        for node in (graph_dict.get('nodes') or {}).values():
            custom = node.get('custom') or {}
            rel = custom.get('template_path') or ''
            if not rel.startswith(_RESOURCES_PREFIX):
                continue
            try:
                data = zf.read(rel)
            except KeyError:
                _logger.warning('打包文件缺少资源，已忽略: %s', rel)
                continue
            custom[_IMAGE_NODE_KEY] = base64.b64encode(data).decode('ascii')
            custom['template_path'] = ''
    return graph_dict


def export_json_resources(graph_dict, json_path):
    """导出为纯 JSON + 外部资源文件夹（资源写在与 json 同目录的 resources/ 下）"""
    prepared, resources = _prepare_for_resources(graph_dict)
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(_dump_json(prepared))
    base = os.path.dirname(os.path.abspath(json_path))
    for rel, data in resources.items():
        full = os.path.join(base, *rel.split('/'))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'wb') as f:
            f.write(data)
    return True


def resolve_relative_resources(graph_dict, base_dir):
    """旧 .json 兼容：把图片节点中相对 template_path 重定位到 json 所在目录（绝对路径）。
    同时支持「JSON + 外部 resources/ 文件夹」导出的重定位（template_path 以 resources/ 开头）。"""
    if not base_dir:
        return graph_dict
    for node in (graph_dict.get('nodes') or {}).values():
        custom = node.get('custom') or {}
        path = custom.get('template_path') or ''
        if path and not os.path.isabs(path):
            abs_path = os.path.join(base_dir, path)
            if os.path.isfile(abs_path):
                custom['template_path'] = os.path.abspath(abs_path)
    return graph_dict
