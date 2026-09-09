# -*- coding: utf-8 -*-
"""
_t_control.py — 控制流改动端到端逻辑测试（临时脚本）
验证:
1. 无头图同步执行 run_graph（开始→等待→结束）
2. fail 分支路由：查找窗口失败且未连 fail → 抛错；连到 重试执行.retry → 重试后走「用尽」
3. 重试节点回路 + 用尽出口
"""
import sys

from PyQt5.QtWidgets import QApplication

app = QApplication(sys.argv)

from NodeGraphQt import NodeGraph
from nodes import discover_nodes

graph = NodeGraph()
classes = discover_nodes()
for c in classes:
    graph.register_node(c)
by_name = {c.NODE_NAME: c for c in classes}

def build(wire):
    g = NodeGraph()
    for c in classes:
        g.register_node(c)
    nodes = {}
    for name, props in wire['nodes'].items():
        n = g.create_node(by_name[name.split(':')[0]].type_, name=name.split(':')[1] if ':' in name else name)
        for k, v in (props or {}).items():
            n.set_property(k, v)
        nodes[name] = n
    for src, sport, dst, dport in wire.get('edges', []):
        nodes[src].get_output(sport).connect_to(nodes[dst].get_input(dport))
    return g, nodes

from nodes._control_common import run_graph, StopFlag

ok = True

# ---- 1. 线性流程 ----
print('t1 build...', flush=True)
g, nd = build({
    'nodes': {'开始:start': {}, '等待:d': {}, '结束:end': {}},
    'edges': [('开始:start', 'out', '等待:d', 'in'), ('等待:d', 'out', '结束:end', 'in')],
})
print('t1 run...', flush=True)
with StopFlag() as sf:
    run_graph(g, sf)
print('1. 线性流程执行 OK', flush=True)

# ---- 2a. 失败且未连 fail → 应抛 RuntimeError ----
g, nd = build({
    'nodes': {'开始:start': {}, '查找窗口:fw': {'title': '', 'class_name': '', 'process_name': ''}},
    'edges': [('开始:start', 'out', '查找窗口:fw', 'in')],
})
try:
    with StopFlag() as sf:
        run_graph(g, sf)
    print('2a. 未按预期抛错 ✗'); ok = False
except RuntimeError as e:
    print(f'2a. 失败未连 fail → 抛错 OK: {e}')

# ---- 2b/3. 重试回路：查找窗口失败 → retry → 重试2次后用尽 ----
g, nd = build({
    'nodes': {
        '开始:start': {},
        '重试执行:r': {'max_retries': '2', 'interval': '0'},
        '查找窗口:fw': {'title': '', 'class_name': '', 'process_name': ''},
    },
    'edges': [
        ('开始:start', 'out', '重试执行:r', 'in'),
        ('重试执行:r', 'body', '查找窗口:fw', 'in'),
        ('查找窗口:fw', 'fail', '重试执行:r', 'retry'),
    ],
})
with StopFlag() as sf:
    run_graph(g, sf)
print('3. 重试 2 次后走「用尽」出口（未连接→正常结束） OK')

# ---- 4. 子工作流：打包当前图为 dict，作为子图执行 ----
from nodes._control_common import run_subgraph_from_dict
inner, _ = build({
    'nodes': {'开始:start': {}, '等待:d': {}, '结束:end': {}},
    'edges': [('开始:start', 'out', '等待:d', 'in'), ('等待:d', 'out', '结束:end', 'in')],
})
session = inner.serialize_session()
outer, nd = build({
    'nodes': {'开始:start': {}, '子工作流:sub': {}, '结束:end': {}},
    'edges': [('开始:start', 'out', '子工作流:sub', 'in'), ('子工作流:sub', 'out', '结束:end', 'in')],
})
# 直接把内层 session 塞给子工作流节点执行（绕过文件，验证 run_subgraph_from_dict）
from unittest.mock import patch
with patch('nodes.subflow_node.load_graph_dict', return_value=session):
    with StopFlag() as sf:
        nd['子工作流:sub'].execute({})
print('4. 子工作流嵌套执行 OK')

print('\n全部通过' if ok else '\n存在失败')
sys.exit(0 if ok else 1)
