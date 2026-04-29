#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
工作流工具类
提供工作流相关的工具函数
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional


class WorkflowUtils:
    """工作流工具类"""

    @staticmethod
    def validate_workflow(graph) -> Dict[str, Any]:
        """验证工作流的有效性"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        nodes = graph.all_nodes() if hasattr(graph, 'all_nodes') else []

        # 检查是否有开始节点
        start_nodes = [node for node in nodes if node.name() == '开始']
        if not start_nodes:
            result['errors'].append('工作流必须包含开始节点')
            result['valid'] = False
        elif len(start_nodes) > 1:
            result['warnings'].append('工作流包含多个开始节点')

        # 检查是否有结束节点
        end_nodes = [node for node in nodes if node.name() == '结束']
        if not end_nodes:
            result['errors'].append('工作流必须包含结束节点')
            result['valid'] = False

        # 检查孤立节点
        for node in nodes:
            if not node.input_ports() and not node.output_ports():
                continue

            has_connections = False
            for port in node.input_ports():
                if port.connected_ports():
                    has_connections = True
                    break
            for port in node.output_ports():
                if port.connected_ports():
                    has_connections = True
                    break

            if not has_connections:
                result['warnings'].append(f'节点 "{node.name()}" 是孤立节点')

        return result

    @staticmethod
    def save_workflow(graph, filepath: str) -> bool:
        """保存工作流到文件"""
        try:
            workflow_data = {
                'metadata': {
                    'version': '1.0',
                    'created_at': datetime.now().isoformat(),
                    'node_count': len(graph.all_nodes()),
                    'connection_count': len(graph.all_pipes())
                },
                'nodes': [],
                'connections': []
            }

            # 保存节点信息
            for node in graph.all_nodes():
                node_data = {
                    'id': node.id(),
                    'name': node.name(),
                    'type': node.type_,
                    'position': node.xy_pos(),
                    'properties': {}
                }

                # 保存节点属性
                for prop_name, prop_value in node.get_properties().items():
                    node_data['properties'][prop_name] = prop_value

                workflow_data['nodes'].append(node_data)

            # 保存连接信息
            for pipe in graph.all_pipes():
                connection_data = {
                    'source': {
                        'node_id': pipe.output_port.node.id(),
                        'port_name': pipe.output_port.name()
                    },
                    'target': {
                        'node_id': pipe.input_port.node.id(),
                        'port_name': pipe.input_port.name()
                    }
                }
                workflow_data['connections'].append(connection_data)

            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(workflow_data, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            print(f'保存工作流失败: {str(e)}')
            return False

    @staticmethod
    def load_workflow(graph, filepath: str) -> bool:
        """从文件加载工作流"""
        try:
            if not os.path.exists(filepath):
                print(f'工作流文件不存在: {filepath}')
                return False

            with open(filepath, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)

            # 清空当前图
            graph.clear()

            # 创建节点
            node_map = {}
            for node_data in workflow_data.get('nodes', []):
                node_type = node_data.get('type')
                node_name = node_data.get('name')

                # 根据类型创建节点
                if hasattr(graph, 'create_node'):
                    node = graph.create_node(node_type, name=node_name)
                    if node:
                        node.set_xy_pos(*node_data.get('position', [0, 0]))
                        node.set_id(node_data.get('id'))

                        # 恢复节点属性
                        for prop_name, prop_value in node_data.get('properties', {}).items():
                            if hasattr(node, 'set_property'):
                                node.set_property(prop_name, prop_value)

                        node_map[node_data['id']] = node

            # 创建连接
            for connection_data in workflow_data.get('connections', []):
                source_node = node_map.get(connection_data['source']['node_id'])
                target_node = node_map.get(connection_data['target']['node_id'])

                if source_node and target_node:
                    source_port = source_node.output_ports()[connection_data['source']['port_name']]
                    target_port = target_node.input_ports()[connection_data['target']['port_name']]

                    if source_port and target_port:
                        graph.connect_ports(source_port, target_port)

            return True

        except Exception as e:
            print(f'加载工作流失败: {str(e)}')
            return False

    @staticmethod
    def export_workflow_image(graph, filepath: str) -> bool:
        """导出工作流为图片"""
        try:
            # TODO: 实现图片导出功能
            # 这里可以集成图形导出库，如matplotlib或cairo
            print(f'导出工作流图片到: {filepath}')
            return True
        except Exception as e:
            print(f'导出图片失败: {str(e)}')
            return False

    @staticmethod
    def generate_workflow_report(graph) -> Dict[str, Any]:
        """生成工作流报告"""
        nodes = graph.all_nodes() if hasattr(graph, 'all_nodes') else []
        connections = graph.all_pipes() if hasattr(graph, 'all_pipes') else []

        # 节点类型统计
        node_type_count = {}
        for node in nodes:
            node_type = node.name()
            node_type_count[node_type] = node_type_count.get(node_type, 0) + 1

        # 连接统计
        connection_count = len(connections)

        # 工作流复杂度分析
        complexity = len(nodes) + len(connections)

        report = {
            'summary': {
                'total_nodes': len(nodes),
                'total_connections': connection_count,
                'complexity_score': complexity
            },
            'node_statistics': node_type_count,
            'validation': WorkflowUtils.validate_workflow(graph),
            'generated_at': datetime.now().isoformat()
        }

        return report


class WorkflowLogger:
    """工作流日志器"""

    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        self.log_levels = {
            'DEBUG': 10,
            'INFO': 20,
            'WARNING': 30,
            'ERROR': 40,
            'CRITICAL': 50
        }

    def log(self, level: str, message: str, context: Optional[Dict] = None):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'context': context or {}
        }

        # 输出到控制台
        print(f"[{timestamp}] {level}: {message}")

        # 写入文件
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            except Exception as e:
                print(f'写入日志文件失败: {str(e)}')

    def debug(self, message: str, context: Optional[Dict] = None):
        """调试日志"""
        self.log('DEBUG', message, context)

    def info(self, message: str, context: Optional[Dict] = None):
        """信息日志"""
        self.log('INFO', message, context)

    def warning(self, message: str, context: Optional[Dict] = None):
        """警告日志"""
        self.log('WARNING', message, context)

    def error(self, message: str, context: Optional[Dict] = None):
        """错误日志"""
        self.log('ERROR', message, context)

    def critical(self, message: str, context: Optional[Dict] = None):
        """严重错误日志"""
        self.log('CRITICAL', message, context)