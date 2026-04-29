# -*- coding: utf-8 -*-
"""
graph.py
作者: reformLi
创建日期: 2026/4/25
最后修改: 2026/4/25
版本: 1.0.0

功能描述: 节点图管理器--该模块封装 NodeGraphQt.NodeGraph，提供高级 API：注册自定义节点、构建图、从数据模型还原图、导出图数据等
"""
# core/graph.py
import json
import logging

from NodeGraphQt import NodeGraph, BaseNode
from PyQt5.QtCore import Qt, QMimeData, QPointF
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QTextEdit, QApplication, QMenu

from core.events import event_bus
from core.workflow import WorkflowModel

class NodeGraphManager:
    """封装 NodeGraphQt 实例，管理节点图的生命周期"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        self.node_graph = None
        self.graph_widget = None
        self.view = None

        self.setup_node_graph()
        # 设置自定义属性面板的回调
        self._on_node_changed_callback = None

    def setup_node_graph(self):
        try:
            # 清理旧的图对象（如果存在）
            if hasattr(self, 'node_graph') and self.node_graph:
                # 断开可能存在的信号连接（可选）
                pass

            self.node_graph = NodeGraph()
            # 允许节点循环
            self.node_graph.set_acyclic(mode=False)
            self.graph_widget = self.node_graph.widget
            self.graph_widget.resize(1000, 600)

            self.view = self.node_graph.viewer()

            # 连接信号（用于日志）
            self.node_graph.node_created.connect(self.on_node_created)
            self.node_graph.nodes_deleted.connect(self.on_node_deleted)
            self.node_graph.port_connected.connect(self.on_node_connected)
            self.node_graph.port_disconnected.connect(self.on_node_disconnected)

            self.logger.info('节点图管理器初始化成功')

        except Exception as e:
            self.logger.error(f'节点图管理器初始化失败: {str(e)}')
            self.graph_widget = QTextEdit()
            self.graph_widget.setPlainText(f"节点图编辑器加载失败: {str(e)}\n\n请确保 NodeGraphQt 已正确安装。")

    def get_widget(self):
        return self.graph_widget

    def register_node_classes(self,classes):
        """注册节点类型（从节点注册表获取）"""
        try:
            # 获取所有节点类
            # node_classes = NodeRegistry.get_node_classes()
            # for node_class in node_classes:
            #     self.node_graph.register_node(node_class)
            for cls in classes:
                # NodeGraphQt.NodeGraph.register_node 要求类有 NODE_NAME 属性
                self.node_graph.register_node(cls)
            self.logger.info('节点类型注册成功')
        except Exception as e:
            self.logger.error(f'节点类型注册失败: {str(e)}')
            import traceback
            self.logger.error(traceback.format_exc())

    def _on_graph_changed(self, *args):
        """图结构发生变化时发射全局事件"""
        event_bus.graph_changed.emit()

    def set_on_node_changed(self, callback):
        self._on_node_changed_callback = callback

    def _on_node_double_clicked(self, node_id):
        # 根据 id 获取节点对象
        for node in self.node_graph.all_nodes():
            if node.id == node_id:
                event_bus.node_double_clicked.emit(node)
                return

    # --------------- 节点操作 ---------------
    def on_node_created(self, node):
        try:
            self.logger.info(f'创建节点: {node.name()}')
        except Exception as e:
            self.logger.debug(f"节点创建回调异常: {e}")

    def on_node_deleted(self, node):
        try:
            # 节点可能已部分销毁，直接记录名称可能失败
            if node:
                self.logger.info(f'删除节点: {node.name()}')
        except Exception:
            self.logger.info('删除节点（无法获取名称）')

    def on_node_connected(self, src_port, trg_port):
        try:
            src_node = src_port.node().name()
            trg_node = trg_port.node().name()
            self.logger.info(f'连接节点: {src_node} -> {trg_node}')
        except Exception as e:
            self.logger.debug(f"连接回调异常: {e}")

    def on_node_disconnected(self, src_port, trg_port):
        try:
            src_node = src_port.node().name()
            trg_node = trg_port.node().name()
            self.logger.info(f'断开节点: {src_node} -> {trg_node}')
        except Exception as e:
            self.logger.debug(f"断开回调异常: {e}")

    def get_all_nodes(self):
        """返回图中所有节点对象"""
        return self.node_graph.all_nodes()

    # --------------- 序列化与反序列化 ---------------
    def to_workflow_model(self) -> WorkflowModel:
        """将当前图导出为 WorkflowModel"""
        graph_dict = self.node_graph.serialize_session()  # NodeGraphQt 内置序列化
        model = WorkflowModel()
        model.nodes = graph_dict.get("nodes", {})
        model.connections = graph_dict.get("connections", [])
        return model

    def from_workflow_model(self, model: WorkflowModel):
        """清空当前图，并从 WorkflowModel 重建"""
        self.node_graph.clear_session()
        self.node_graph.deserialize_session({
            "nodes": model.nodes,
            "connections": model.connections,
        })

    def save_to_file(self, file_path: str):
        """保存为 .json 工作流文件"""
        # model = self.to_workflow_model()
        # model.save_to_file(filepath)
        if not self.node_graph:
            self.logger.warning("节点图未初始化，无法保存")
            return False
        try:
            self.node_graph.save_session(file_path)
            self.logger.info(f"节点图已保存到: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"保存节点图失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def load_from_file(self, file_path: str):
        """从文件加载工作流"""
        # model = WorkflowModel.load_from_file(filepath)
        # self.from_workflow_model(model)
        """从文件加载节点图（使用 NodeGraphQt 的 load_session）"""
        if not self.node_graph:
            self.logger.warning("节点图未初始化，无法加载")
            return False
        try:
            # 断开所有信号连接，防止加载过程中触发回调
            try:
                self.node_graph.node_created.disconnect(self.on_node_created)
                self.node_graph.nodes_deleted.disconnect(self.on_node_deleted)
                self.node_graph.port_connected.disconnect(self.on_node_connected)
                self.node_graph.port_disconnected.disconnect(self.on_node_disconnected)
            except (TypeError, AttributeError):
                # 如果没有连接，忽略
                pass

            # 加载会话（内部会清空现有图并重新创建节点）
            self.node_graph.load_session(file_path)
            self.logger.info(f"从文件加载节点图: {file_path}")

            # 重新连接信号
            self.node_graph.node_created.connect(self.on_node_created)
            self.node_graph.nodes_deleted.connect(self.on_node_deleted)
            self.node_graph.port_connected.connect(self.on_node_connected)
            self.node_graph.port_disconnected.connect(self.on_node_disconnected)

            return True
        except Exception as e:
            self.logger.error(f"加载节点图失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def clear(self):
        """清空节点图（安全断开信号）"""
        if not self.node_graph:
            return

        # 临时断开 nodes_deleted 信号，避免清空时回调
        try:
            self.node_graph.nodes_deleted.disconnect(self.on_node_deleted)
        except (TypeError, AttributeError):
            pass

        try:
            # 使用官方方法清空
            if hasattr(self.node_graph, 'clear_session'):
                self.node_graph.clear_session()
            elif hasattr(self.node_graph, 'clear'):
                self.node_graph.clear()
            else:
                # 手动删除所有节点
                nodes = []
                if hasattr(self.node_graph, 'all_nodes'):
                    nodes = self.node_graph.all_nodes()
                elif hasattr(self.node_graph, '_nodes'):
                    nodes = list(self.node_graph._nodes.values())
                for node in nodes:
                    self.node_graph.delete_node(node)
        except Exception as e:
            self.logger.error(f"清空失败: {e}")
        finally:
            # 重新连接信号
            self.node_graph.nodes_deleted.connect(self.on_node_deleted)

        self.logger.info("节点图已清空")

    def undo(self):
        """安全撤销"""
        if not self.node_graph:
            return

        # 临时断开可能导致崩溃的信号
        self._disconnect_signals()

        try:
            # 方法1：尝试使用内置 undo 方法（部分版本）
            if hasattr(self.node_graph, 'undo'):
                self.node_graph.undo()
            else:
                # 方法2：通过 undo_stack 访问 QUndoStack
                undo_stack = getattr(self.node_graph, 'undo_stack', None)
                if undo_stack and callable(undo_stack):
                    stack = undo_stack()
                    if stack and stack.canUndo():
                        stack.undo()
                else:
                    self.logger.warning("无法找到撤销方法")
        except Exception as e:
            self.logger.error(f"撤销失败: {e}")
        finally:
            # 重新连接信号
            self._connect_signals()

    def redo(self):
        """安全重做"""
        if not self.node_graph:
            return

        self._disconnect_signals()

        try:
            if hasattr(self.node_graph, 'redo'):
                self.node_graph.redo()
            else:
                undo_stack = getattr(self.node_graph, 'undo_stack', None)
                if undo_stack and callable(undo_stack):
                    stack = undo_stack()
                    if stack and stack.canRedo():
                        stack.redo()
                else:
                    self.logger.warning("无法找到重做方法")
        except Exception as e:
            self.logger.error(f"重做失败: {e}")
        finally:
            self._connect_signals()

    def _disconnect_signals(self):
        """断开所有信号连接"""
        if not self.node_graph:
            return
        signals = [
            (self.node_graph.node_created, self.on_node_created),
            (self.node_graph.nodes_deleted, self.on_node_deleted),
            (self.node_graph.port_connected, self.on_node_connected),
            (self.node_graph.port_disconnected, self.on_node_disconnected),
        ]
        for sig, slot in signals:
            try:
                sig.disconnect(slot)
            except (TypeError, AttributeError):
                pass

    def _connect_signals(self):
        """重新连接信号"""
        if not self.node_graph:
            return
        signals = [
            (self.node_graph.node_created, self.on_node_created),
            (self.node_graph.nodes_deleted, self.on_node_deleted),
            (self.node_graph.port_connected, self.on_node_connected),
            (self.node_graph.port_disconnected, self.on_node_disconnected),
        ]
        for sig, slot in signals:
            try:
                sig.connect(slot)
            except (TypeError, AttributeError):
                pass

    def cleanup(self):
        """清理节点图资源，断开信号，移除事件过滤器"""
        if not self.node_graph:
            return

        # 移除事件过滤器（视口）
        if self.view:
            viewport = self.view.viewport()
            if viewport:
                try:
                    viewport.removeEventFilter(self)
                except:
                    pass
            # 可选：移除视图本身的过滤器（如果之前安装过）
            try:
                self.view.removeEventFilter(self)
            except:
                pass

        # 断开所有信号连接
        try:
            self.node_graph.node_created.disconnect(self.on_node_created)
        except (TypeError, AttributeError):
            pass
        try:
            self.node_graph.nodes_deleted.disconnect(self.on_node_deleted)
        except:
            pass
        try:
            self.node_graph.port_connected.disconnect(self.on_node_connected)
        except:
            pass
        try:
            self.node_graph.port_disconnected.disconnect(self.on_node_disconnected)
        except:
            pass

        # 删除图形部件
        if self.graph_widget:
            self.graph_widget.deleteLater()

        # 释放引用
        self.node_graph = None
        self.graph_widget = None
        self.view = None

    def copy_selected_nodes(self):
        """复制选中的节点"""
        if not self.node_graph:
            return
        selected = self.node_graph.selected_nodes()
        if not selected:
            self.logger.debug("没有选中节点，无法复制")
            return

        # 序列化选中的节点（手动提取必要信息）
        nodes_data = []
        for node in selected:
            # 获取节点类型标识符（如 input.InputNode）
            node_type = node.type_
            # 获取节点属性（位置、自定义属性等）
            pos = node.pos()
            properties = {}
            # 如果有自定义属性，可以在这里收集
            # 示例：获取所有端口值（如有）
            # 这里只保存位置和类型
            nodes_data.append({
                'type': node_type,
                'x': pos[0],
                'y': pos[1],
                'properties': properties,
                # 可选：保存节点名称（可能重复）
                'name': node.name(),
            })

        # 转换为 JSON 并存入剪贴板
        data_str = json.dumps(nodes_data)
        mime_data = QMimeData()
        mime_data.setText(data_str)
        QApplication.clipboard().setMimeData(mime_data)
        self.logger.info(f"已复制 {len(selected)} 个节点")

    def paste_nodes(self, scene_pos=None):
        """粘贴节点到场景指定位置（默认鼠标位置）"""
        if not self.node_graph:
            return

        mime_data = QApplication.clipboard().mimeData()
        if not mime_data or not mime_data.hasText():
            self.logger.debug("剪贴板无节点数据")
            return

        try:
            nodes_data = json.loads(mime_data.text())
        except Exception as e:
            self.logger.error(f"解析剪贴板数据失败: {e}")
            return

        # 获取粘贴位置（场景坐标）
        if scene_pos is None:
            # 获取鼠标的全局位置（使用 QCursor）
            global_pos = QCursor.pos()
            # 转换为视图坐标
            view_pos = self.view.mapFromGlobal(global_pos)
            # 转换为场景坐标
            scene_pos = self.view.mapToScene(view_pos)
            # 如果场景坐标无效（例如视图外），则使用视图中心
            if not scene_pos or (scene_pos.x() == 0 and scene_pos.y() == 0):
                rect = self.view.sceneRect()
                scene_pos = rect.center() if rect.isValid() else QPointF(0, 0)

        offset_x, offset_y = 30, 30
        created_nodes = []
        for i, data in enumerate(nodes_data):
            try:
                node_type = data.get('type')
                if not node_type:
                    self.logger.warning(f"数据缺少 'type' 字段: {data}")
                    continue

                # 创建节点
                node = self.node_graph.create_node(node_type)
                if not node:
                    self.logger.warning(f"无法创建节点类型: {node_type}")
                    continue

                # 设置位置（以鼠标位置为基准，网格偏移）
                new_x = scene_pos.x() + (i % 5) * offset_x
                new_y = scene_pos.y() + (i // 5) * offset_y
                node.set_pos(new_x, new_y)

                # 设置其他属性（如名称）
                new_name = data.get('name')
                if new_name and new_name != node.name():
                    node.set_name(new_name)

                created_nodes.append(node)
                self.logger.debug(f"粘贴节点 {node_type} 成功，位置 ({new_x}, {new_y})")
            except Exception as e:
                self.logger.error(f"粘贴单个节点失败: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                # 继续处理下一个节点

        self.logger.info(f"已粘贴 {len(created_nodes)} 个节点")
        return created_nodes

    def delete_selected_nodes(self):
        """删除所有选中的节点（同时自动删除相关连接）"""
        if not self.node_graph:
            return
        selected_nodes = self.node_graph.selected_nodes()
        if not selected_nodes:
            self.logger.debug("没有选中的节点")
            return

        # 临时断开信号，避免删除时回调引发崩溃
        self._disconnect_signals()
        try:
            for node in selected_nodes:
                self.node_graph.delete_node(node)
            self.logger.info(f"已删除 {len(selected_nodes)} 个节点")
        except Exception as e:
            self.logger.error(f"删除节点失败: {e}")
        finally:
            self._connect_signals()

    def delete_selected_connections(self):
        """删除所有选中的连接线"""
        if not self.node_graph:
            return
        # NodeGraphQt 中获取选中连接的方法通常是 selected_connections()
        if hasattr(self.node_graph, 'selected_connections'):
            selected_conns = self.node_graph.selected_connections()
        else:
            selected_conns = []
        if not selected_conns:
            self.logger.debug("没有选中的连接")
            return

        self._disconnect_signals()
        try:
            for conn in selected_conns:
                # 获取端口并断开
                if hasattr(conn, 'source_port') and hasattr(conn, 'target_port'):
                    src_port = conn.source_port
                    trg_port = conn.target_port
                    if src_port and trg_port:
                        src_port.disconnect(trg_port)
            self.logger.info(f"已删除 {len(selected_conns)} 条连接")
        except Exception as e:
            self.logger.error(f"删除连接失败: {e}")
        finally:
            self._connect_signals()

    def delete_selected(self):
        """删除所有选中的节点和连接（综合）"""
        # 删除选中连接（先删连接，再删节点，避免节点删除时重复触发）
        self.delete_selected_connections()
        self.delete_selected_nodes()
