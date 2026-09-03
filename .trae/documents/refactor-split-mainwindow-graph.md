# 重构计划：拆分 main_window.py 与 graph.py，修复执行控制链路

## Context

用户反馈项目"笨重不好用"，代码审查发现两个文件职责过载：
- `ui/main_window.py`（888行）：主窗口混杂布局、菜单/工具栏构建、日志搜索（~250行）、文件操作、执行控制、主题管理等 7 类职责
- `core/graph.py`（519行）：信号"断开→操作→重连"逻辑重复 6 遍，剪贴板/序列化/undo/删除混杂

重构过程中确认了多个**阻断性/潜伏 bug**（一并修复）：

1. **验证恒失败（阻断）**：`CoreManager.validate_workflow` 用 `'start' in node.NODE_NAME.lower()` 找开始节点，但所有节点 NODE_NAME 均为中文（`'开始'`/`'结束'`），匹配恒 False → **F5 永远无法执行工作流**
2. **暂停/恢复/终止从未生效**：主窗口检查 `hasattr(self, '_executor')` 但从未持有 executor；CoreManager 未暴露控制方法；executor 无 pause/resume；worker 的 `_on_pause/_on_resume` 槽未连接任何信号
3. **executor.py:41 双参 emit**：`error_occurred.emit("", "未找到开始节点")` 对单参信号 `pyqtSignal(str)` 传两参，运行时 TypeError 被外层 except 吞掉
4. **连接泄漏**：`WorkflowExecutor.start()` 每次执行都 connect `node_exec_started/finished` 且从不 disconnect，第 N 次运行后回调触发 N 次
5. **graph.py 三处死代码**：`_on_graph_changed`（从未连接）、`set_on_node_changed`（无调用方）、`_on_node_double_clicked`（引用不存在的 `node_double_clicked` 信号，调用即崩溃）
6. `load_from_file` 中 `load_session` 抛异常时信号永不重连（重连代码在异常路径之后）

## 目标结构

```
ui/
  main_window.py            瘦身为组装器（~250行）：布局、面板挂载、主题、对话框、closeEvent、编辑命令薄委托
  actions.py                新增：build_menu_bar(window) / build_tool_bar(window) 纯结构构建（~200行）
  file_actions.py           新增：FileActions 类——新建/打开/保存/另存为/清空，持有 current_file 状态（~110行）
  execution_controller.py   新增：ExecutionController 类——启动/暂停/恢复/终止/验证 + 按钮状态机 + event_bus 订阅（~180行）
  log_search_bar.py         新增：LogSearchBar(QToolBar)——日志搜索框/高亮/计数/导航（~280行）
core/
  graph/                    由 graph.py 单文件转为包
    __init__.py             re-export NodeGraphManager（保持 `from core.graph import NodeGraphManager` 兼容）
    manager.py              宿主类：生命周期 + 节点注册 + mixin 组装（~140行）
    signals.py              GraphSignalManager：四信号连接/断开/日志回调 + suppressed() 上下文管理器（~130行）
    serialization.py        GraphSerializerMixin：WorkflowModel 与 .json 互转（~120行）
    editing.py              GraphEditingMixin：undo/redo/删除选中（~150行）
    clipboard.py            GraphClipboardMixin：复制/粘贴（~120行）
  validation.py             新增：WorkflowValidator——基于 is_start_node()/is_end_node() 的唯一验证实现（~90行）
  events.py                 修改：新增 pause_signal / resume_signal
  executor.py               修改：pause()/resume() 方法、worker 连接控制信号并广播状态、修双参 emit、修连接泄漏、删死代码
  manager.py                修改：新增 pause/resume/stop_workflow()；validate 委托 WorkflowValidator；get_node_property_defs 加 getattr 防护
```

**不变契约**（保证 `app/main.py`、`ui/node_graph_panel.py`、`ui/nodes_panel.py` 零改动）：
`WorkflowMainWindow` 类名、`CoreManager` 现有方法名、`NodeGraphManager` 类名与 `node_graph/view/graph_widget` 属性、event_bus 既有信号、window 上的 `start_action` 等 action 属性名。

依赖方向不变：ui → core → nodes → automation。

## 关键设计

### 1. 信号管理收敛（graph/signals.py）

```python
class GraphSignalManager:
    def __init__(self, node_graph): ...   # 四个绑定: node_created/nodes_deleted/port_connected/port_disconnected
    def connect_all(self): ...            # 幂等（先断后连，防重复叠加）
    def disconnect_all(self): ...
    @contextmanager
    def suppressed(self): ...             # 断开→yield→finally 恢复；禁止嵌套
    def dispose(self): ...                # 永久断开（仅 cleanup 用）
    # 四个日志回调从 graph.py 原样迁移（保留 try/except 与文案）
```

替换 6 处重复的断连/重连代码；`finally` 保证异常时也回连（修 bug #6）。
`clear` 从"只断 nodes_deleted"统一为全断再全连（clear_session 只触发 nodes_deleted，观察行为等价）。

### 2. 执行控制链路修复

```
工具栏 ⏸ → ExecutionController.pause_workflow()
  → CoreManager.pause_workflow() [新增]
    → WorkflowExecutor.pause() [新增: if self._worker: event_bus.pause_signal.emit()]
      → (队列) WorkflowWorker._on_pause()  [worker __init__ 连接 pause/resume 信号]
        → _pause_flag = True + event_bus.execution_paused.emit()
          → (队列) ExecutionController.update_execution_buttons('paused')
```

- resume 同构；stop 复用现有 stop_signal，`_on_stop` 补发 `execution_stopped` 信号
- `pause_workflow` 等三个 UI 方法删除 `hasattr(self, '_executor')` 分支和乐观状态更新，状态由信号驱动
- `node_exec_started/finished` 连接从 `start()` 移到 `WorkflowExecutor.__init__`（只连一次，修泄漏）
- `run()` 中 `error_occurred.emit("未找到开始节点")` 单参修复，并补 `execution_finished.emit(False)` 保证按钮回 idle

### 3. 验证统一（core/validation.py）

```python
class WorkflowValidator:
    @staticmethod
    def validate(nodes) -> dict:   # 用 is_start_node()/is_end_node()，返回 {'success', 'message'}
```

`CoreManager.validate_workflow` 委托之（返回结构与文案不变）。删除 executor 中从未被调用的 `WorkflowWorker._validate_workflow` 与空方法 `finished`。`utils/workflow_utils.py` 无调用方，不动。

### 4. main_window.py 拆分映射（方法名保留）

| 现有方法 | 去向 |
|---|---|
| setup_menu_bar / setup_tool_bar | ui/actions.py 的 build_menu_bar / build_tool_bar（命令绑定 window.file_actions.* / window.execution.*） |
| setup_log_search_toolbar / search_logs / clear_search_highlights / highlight_current_match / search_next / search_previous / hide_search_toolbar | LogSearchBar（主窗口留 _show/_hide 两小方法管理 action 使能） |
| new/open/save/save_as/clear_workflow | FileActions |
| start/pause/resume/stop/execute/validate_workflow、update_execution_buttons | ExecutionController |
| 其余（setup_ui、面板挂载、setup_logging、show_settings/about、apply_theme、undo/redo/copy/paste/delete 薄委托、closeEvent） | 留在 main_window |

`__init__` 顺序：logger → theme → core_manager → file_actions → execution → setup_ui → setup_logging。

### 5. graph.py 拆分映射

NodeGraphManager(GraphSerializerMixin, GraphEditingMixin, GraphClipboardMixin)，宿主提供 `node_graph/view/logger/_signals` 属性协议（mixin 文件头注明）。
死代码删除：`_on_graph_changed`、`set_on_node_changed`、`_on_node_double_clicked`。
`undo/redo` 简化为 `undo_stack()` 直调（已实测 NodeGraphQt 0.6.44 无 undo() 方法），外层 try/except 保留。
`delete_selected_connections` 保留 hasattr 回退（0.6.44 无 selected_connections，现状即 no-op，不顺手改行为）。

## 实施步骤（每步结束程序可运行，独立 commit）

| 步骤 | 内容 | 验证 |
|---|---|---|
| 0 | 建分支；清理 core/ui 的 `__pycache__`；跑 `python -m app.main` 留基线 | 正常启动 |
| 1 | **bug 修复**：events 加信号 → executor（连接/方法/emit/泄漏/死代码）→ validation.py + manager 委托与控制方法 → main_window 三方法改调 core_manager | 搭 开始→等待→结束 链：F5 能执行（基线本应恒失败）；⏸/⏯/⏹ 生效；无开始节点时日志显示正确错误 |
| 2 | **graph.py → core/graph/ 包**：按 signals → serialization → editing → clipboard → manager 顺序建模块，删旧文件（注意删 `core/__pycache__/graph.cpython-*.pyc`） | 建节点/连线/删除/复制粘贴/undo/redo/保存/打开/清空/关闭，日志与基线一致 |
| 3 | **拆 main_window**（4 个子 commit）：3a LogSearchBar → 3b actions.py → 3c FileActions → 3d ExecutionController | Ctrl+F 搜索全流程；菜单/快捷键/工具栏逐一对照；文件操作确认框；四按钮状态机 |
| 4 | 收尾：settings_dialog 删未使用的 `from tests.mytest23 import Switch`；全文件行数复核（均 <300）；全量回归 | 完整用户行为清单走查 |

## 风险与回退

- 包转换残留 pyc → 明确删除 `core/__pycache__`
- Qt 信号重复叠加 → connect_all 幂等化；suppressed 禁止嵌套（delete_selected 两步顺序用）
- mixin 隐式依赖宿主属性 → 文件头声明宿主协议；__init__ 固定顺序，漏序首次启动即暴露
- 暂停/终止仅在节点间隙生效（Delay 睡眠中无法中断）→ 现有设计固有行为，不改，类文档标注
- 每步独立 commit，出问题 revert 单步即可；对外契约全程不变

## 验证方式（端到端）

```bash
python -m app.main
```
1. 拖拽/右键创建节点、连线、框选删除、Ctrl+Z/Y、Ctrl+C/V
2. 新建/打开/保存/另存为（含确认框三态）
3. F6 验证：空图/缺开始/缺结束 三类文案正确
4. F5 执行 开始→等待(1s)→结束：节点显示"▶运行中→✓成功⏱x.xx秒"
5. 执行长等待链，验证 ⏸ 暂停（状态栏"已暂停"）/⏯ 恢复/⏹ 终止（按钮回 idle）
6. Ctrl+F 日志搜索：高亮、↑↓ 导航、计数、关闭
7. 设置切换主题/网格显示
