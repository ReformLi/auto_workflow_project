## 项目模块化架构方案

该项目本质上是 **"可视化节点编辑器 + 窗口自动化执行引擎"** 的组合应用。基于 MVC（Model-View-Controller）架构模式以及 PyQt5 开发最佳实践中的关注点分离原则，将系统拆分为 **7 个一级模块**，每个模块可进一步划分二级子模块。

### 架构总览

```
window_automation_workflow/
├── app                        # 应用入口与全局配置
├── core/                       # 核心业务层（逻辑中枢）
├── nodes/                     # 节点模块
│   └── base_nodes.py          # 基础节点定义 (5KB)
├── ui/                         # 用户界面层（视图组件）
├── automation/                 # 窗口自动化引擎（底层执行）
├── resources/                  # 静态资源
└── tests/                      # 测试模块
```

### 一、app —— 应用入口与全局配置

**职责说明：** 应用启动入口，负责全局初始化、配置加载、日志系统建立以及各模块的装配与协调。这是整个项目的 "组装车间"，不包含具体业务逻辑。

**关键实现要点：**

- **`main.py`**：创建 QApplication 实例，初始化日志配置，实例化 CoreManager，启动主事件循环。这是程序的唯一入口，避免在多个文件中分散创建顶层组件
- **`config.py`**：集中管理全局配置常量，包括默认窗口大小、日志级别、自动化操作的超时时间、鼠标默认点击间隔等参数。所有模块应从此处读取配置，而非硬编码
- **`logger.py`**：基于 Python 标准库 logging 模块封装日志系统，统一日志格式，支持控制台输出与文件轮转。可为 node 执行、automation 调用等不同来源设置 logger name，便于追踪

**拆分理由：** app 模块将启动流程与业务逻辑完全解耦，便于后续扩展命令行参数解析、插件注册、启动时自检等功能，同时降低模块间耦合——下游模块不需要知道 QApplication 的存在。


### 二、core —— 核心业务层

**职责说明：** core 模块是整个应用的"大脑"，扮演 MVC 中 Controller（控制器）与一部分 Model（数据模型）的角色。它负责管理 NodeGraphQt 图实例、工作流文件（JSON）的读写、节点注册调度、执行引擎的协调，以及模块间信号的转发。

**子模块与详细分工：**

| 子模块 | 职责 |
|---|---|
| `core/manager.py` | 应用核心管理器，聚合所有子模块，协调 graph 和 executor 之间通信 |
| `core/graph.py` | 封装 NodeGraphQt 的图实例，管理节点的创建、连接、删除、序列化等全生命周期操作 |
| `core/workflow.py` | 工作流数据模型——定义 JSON 序列化/反序列化格式、工作流元信息管理 |
| `core/executor.py` | 工作流执行引擎——负责节点拓扑排序，按依赖顺序调度节点执行 |
| `core/events.py` | 事件总线——定义 PyQt5 信号（pyqtSignal），解耦 UI 与执行逻辑之间的通信 |

**关键实现要点：**

1. **manager.py（核心中枢）** ：持有 `NodeGraph` 实例和 `WorkflowExecutor` 实例的引用，负责初始化 UI 并建立信号/槽连接。当用户从 UI 触发 "执行工作流" 时，manager 接收信号，将当前的图数据传递给 executor 启动执行。

2. **graph.py（图管理）** ：封装 `NodeGraphQt.NodeGraph`，提供统一的高层 API。参考 Borealis-Legacy 项目的实现模式，动态导入 nodes 目录下的自定义节点类并注册到图中，同时负责右键菜单的节点添加命令和 "删除选中节点" 选项。

3. **workflow.py（数据模型）** ：定义工作流文件的 JSON 结构，至少应包含：节点列表（每个节点的类型、位置、属性值）、连接列表（源节点/端口与目标节点/端口的映射）、元数据（创建时间、版本号）。负责序列化（保存）与反序列化（加载）。

4. **executor.py（执行引擎）** ：对图进行拓扑排序，确保先执行上游节点、再执行下游节点。支持顺序执行模式。每个节点执行时调用其 `execute()` 方法，收集返回值传递给下游节点。执行状态（空闲、运行中、暂停、完成）通过信号通知 UI。

5. **events.py（事件总线）** ：定义全局 pyqtSignal，包括：`workflow_execution_started`、`workflow_execution_finished`、`node_execution_started(node_id)`、`node_execution_finished(node_id, result)`、`node_execution_failed(node_id, error)` 等，实现模块间对等通信，避免 UI 层直接操作业务对象。

**拆分理由：** 将图管理、数据模型、执行逻辑、事件通信各自独立，避免单一文件膨胀至数千行。根据软件开发中模块行数超过 600 行则需要分解的实践经验，core 模块提前拆分可显著提升可维护性。


### 三、nodes —— 自定义节点库

**职责说明：** nodes 模块存放所有自定义的节点类型，每个节点代表一个窗口自动化操作的原子动作（如启动应用、点击按钮、输入文本、等待窗口出现等）。该模块是 NodeGraphQt 的扩展层，也是项目可扩展性的核心体现。

**子模块详细分工：**

| 子模块/文件 | 节点功能描述 |
|---|---|
| `nodes/__init__.py` | 节点包入口，负责动态收集所有节点类供 graph 模块注册 |
| `nodes/base_node.py` | 自定义基类，继承 BaseNode，定义 execute() 接口和通用属性 |
| `nodes/app_nodes.py` | 应用相关节点——启动应用、关闭应用、获取应用窗口 |
| `nodes/mouse_nodes.py` | 鼠标操作节点——鼠标移动、左键点击、右键点击、双击、拖拽 |
| `nodes/keyboard_nodes.py` | 键盘操作节点——文本输入、快捷键组合、特殊按键 |
| `nodes/window_nodes.py` | 窗口操作节点——查找窗口、激活窗口、关闭窗口、设置窗口大小位置 |
| `nodes/wait_nodes.py` | 等待/条件节点——等待指定时间、等待窗口出现、等待元素可用 |
| `nodes/flow_nodes.py` | 流程控制节点——循环、条件分支（if/else）、变量设置与获取 |
| `nodes/utility_nodes.py` | 工具节点——日志输出节点、屏幕截图节点、运行 Python 脚本节点 |

**关键实现要点：**

1. **base_node.py 设计：** 继承 NodeGraphQt 的 `BaseNode`，添加统一的属性定义（如超时时间、错误处理策略等）和抽象方法 `execute(inputs: dict) -> dict`。所有业务节点必须重写该方法。基类还应处理执行状态标记（成功/失败/待执行），便于 UI 层根据状态渲染不同颜色。

2. **节点外观差异化：** 不同功能的节点应使用不同的颜色或图标进行区分，让用户在画布上一眼辨识别节点类型。例如鼠标操作节点用蓝色、键盘操作节点用绿色、流程控制节点用橙色。

3. **端口设计规范：** 节点的输入/输出端口应有统一的命名约定：`"in"` 表示数据输入端口，`"out"` 表示数据输出端口。支持多输入端口时设置 `multi_input=True`，允许同一端口接受多条连接。不同数据类型（如字符串、坐标、布尔值）可考虑用不同形状或颜色的端口区分。

4. **动态注册机制：** 在 `nodes/__init__.py` 中使用反射机制，自动扫描目录下所有模块，收集继承自 BaseNode 的子类，返回一个节点类列表供 core/graph.py 调用注册，参考开源项目 Borealis-Legacy 中的 `import_nodes_from_folder()` 实现。

**拆分理由：** 将节点按功能类别拆分到独立文件，避免单个文件承载几十个节点类。新增自动化能力只需添加新的节点文件，在 `core/graph.py` 的注册流程中自动挂载，无需改动其他模块。


### 四、ui —— 用户界面层

**职责说明：** ui 模块包含所有 PyQt5 界面相关代码，遵循 MVC 中 View 的职责——只负责展示数据和收集用户输入，不包含业务逻辑。

**子模块详细分工：**

| 子模块 | 职责 |
|---|---|
| `ui/main_window.py` | 主窗口框架——包含菜单栏、工具栏、状态栏，作为所有子面板的容器 |
| `ui/node_graph_panel.py` | 节点图画布面板——集成 NodeGraphQt 的 widget，放置到主窗口中央 |
| `ui/properties_panel.py` | 节点属性编辑面板——选中节点时显示其可编辑属性 |
| `ui/toolbox_panel.py` | 节点工具箱面板——分类展示所有可用节点，支持拖拽添加 |
| `ui/execution_panel.py` | 执行控制面板——播放/暂停/停止按钮、进度显示、执行日志 |
| `ui/dialogs/` | 对话框集合——设置对话框、关于对话框、确认对话框等 |
| `ui/styles.py` | 全局样式定义——QSS 样式表、主题颜色常量、节点颜色映射表 |

**关键实现要点：**

1. **main_window.py：** 使用 QMainWindow 作为顶层窗口，QSplitter 或 QDockWidget 布局实现可拖拽调整大小的面板区域。菜单栏应包含文件操作（新建/打开/保存/另存为）、编辑操作（撤销/重做）、执行控制、视图设置等选项。

2. **node_graph_panel.py：** 将 `NodeGraphQt.NodeGraph().widget` （返回 QWidget 包装器）嵌入到 PyQt5 布局中，设置为主界面的中心区域。该面板不直接操作图数据，而是通过 core 层的 API 进行交互。

3. **properties_panel.py：** 监听节点选择变化信号，当用户选中节点时动态渲染节点的可编辑属性控件（如文本框、滑块、下拉框、颜色选择器等）。属性值修改后通过信号传递给 core 层更新图数据。

4. **toolbox_panel.py：** 以分类树或分类列表形式展示所有已注册的节点类型，用户点击或拖拽节点类型到画布上即可创建实例。分类信息可从节点类的元数据中读取。

5. **execution_panel.py：** 通过订阅 core/events.py 中定义的事件信号，实时更新执行状态、当前执行节点的高亮显示、以及输出日志。

**拆分理由：** UI 层与业务逻辑层的彻底分离是 GUI 应用开发的核心原则，不这样做会导致各 widget 之间形成"意大利面条式"相互调用关系，产生难以维护的代码。同时，每个面板独立为单独文件也便于 UI 布局的单独调试和替换。


### 五、automation —— 窗口自动化引擎

**职责说明：** automation 模块是实际执行窗口自动化操作的底层引擎，封装对操作系统层面 API 的调用。它作为 nodes 模块的依赖项——节点调用 automation 提供的统一 API 来执行实际的自动化动作，而非直接在节点内部调用第三方库。

**子模块详细分工：**

| 子模块 | 职责 |
|---|---|
| `automation/window_manager.py` | 窗口管理——查找窗口、枚举所有窗口、激活窗口、关闭窗口 |
| `automation/mouse_controller.py` | 鼠标控制——移动、点击、拖拽、滚轮 |
| `automation/keyboard_controller.py` | 键盘控制——文本输入、组合键、特殊按键模拟 |
| `automation/element_locator.py` | UI 元素定位——按标题/类名/控件类型/自动化 ID 等属性查找控件元素 |
| `automation/utils.py` | 工具函数——坐标计算、截图、等待条件检测 |

**关键实现要点：**

1. **底层库选择策略：** 推荐同时封装 `pywinauto` 和 `uiautomation` 两套底层引擎，通过配置或控制节点上的 backend 选项切换。pywinauto 基于 Win32 API，适合老式 Windows 应用；uiautomation 封装了 Microsoft 的 UI Automation API，对 Qt5、WPF、现代 Windows 应用支持更好。

2. **window_manager.py：** 提供统一的窗口操作 API，如 `find_window(title, class_name)` 返回窗口对象引用，`activate_window(window)` 将窗口置于前台，`get_active_window()` 获取当前活动窗口。这些方法内部根据 backend 配置调用相应的底层库。

3. **mouse_controller.py：** 封装鼠标操作，支持基于屏幕坐标的绝对操作和基于控件元素的相对操作。应包含 move / click / double_click / right_click / drag / scroll 等方法。

4. **keyboard_controller.py：** 封装键盘输入，支持普通文本输入（自动处理中文输入）、组合键（Ctrl+C、Alt+Tab 等）、以及特殊按键（F1-F12、方向键等）。

5. **element_locator.py：** 这是自动化引擎中最复杂的部分。提供多种元素查找策略：按 AutomationId、按 Name/Title、按 ClassName、按 ControlType，以及 XPath 式路径查找。应设计为链式调用风格，便于节点构建查找条件。

**拆分理由：** 将自动化底层能力与节点逻辑分离，当需要切换底层库或添加新的操作能力时，仅需修改 automation 模块内部，nodes 模块保持不变。这是典型的"适配器模式"应用。


### 六、resources —— 静态资源

**职责说明：** 存放项目中的所有非代码资源文件。

**子模块：**

| 子模块 | 说明 |
|---|---|
| `resources/icons/` | 节点图标、工具栏图标、应用图标 |
| `resources/styles/` | QSS 样式表文件（可选，也可在 ui/styles.py 中内联定义） |
| `resources/examples/` | 示例工作流 JSON 文件，供新用户快速上手 |


### 七、tests —— 测试模块

**职责说明：** 包含单元测试和集成测试，确保各模块功能正确。

**子模块：**

| 子模块 | 说明 |
|---|---|
| `tests/test_nodes/` | 对每个自定义节点类的单元测试 |
| `tests/test_automation/` | 对自动化引擎各模块的单元测试（需 Windows 环境） |
| `tests/test_core/` | 对工作流加载/保存、执行引擎的测试 |
| `tests/test_integration/` | 端到端集成测试 |


### 模块间依赖关系与通信规则

各模块之间遵循严格的依赖层级：

- **ui → 依赖 core**：UI 层通过 core 提供的 API 和事件信号获取数据，不直接操作 automation 或 nodes，确保界面与业务逻辑解耦
- **core → 依赖 nodes 和 automation**：core 的 executor 调度 nodes 执行，nodes 调用 automation 的 API 完成实际操作
- **nodes → 依赖 automation**：节点通过 automation 模块的统一接口执行底层操作，不直接调用 pywinauto 或 uiautomation
- **automation → 外部依赖**：底层调用 pywinauto、uiautomation 等第三方库

通信规则如下：

1. **单向依赖原则：** 上层可依赖下层，下层绝不依赖上层。nodes 不知道 UI 的存在，automation 不知道 nodes 的存在
2. **信号驱动通信：** 同级模块之间通过 core/events.py 中定义的 PyQt5 信号进行解耦通信，不直接持有对方的引用
3. **接口抽象原则：** core 模块定义清晰的抽象接口，ui 和 nodes 通过这些接口交互，而非直接访问对方的内部实现


### 项目整体设计建议

**1. 工作流 JSON 保存格式设计**

工作流文件建议设计为如下 JSON 结构：

```json
{
    "version": "1.0",
    "name": "我的自动化工作流",
    "created_at": "2026-04-25T00:00:00",
    "nodes": [
        {
            "id": "node_1",
            "type": "nodes.mouse_nodes.ClickNode",
            "name": "点击按钮",
            "x": 100, "y": 200,
            "properties": {"button": "left", "clicks": 1}
        }
    ],
    "connections": [
        {"source_node": "node_1", "source_port": "out",
         "target_node": "node_2", "target_port": "in"}
    ]
}
```

**2. 扩展性设计**

- 新增自动化操作类型时，只需在 `nodes/` 下创建新文件，继承 BaseNode 并实现 execute() 方法，运行时自动发现与注册，无需修改其他模块
- 如需支持更多操作系统（如 macOS、Linux），只需实现对应的 automation 适配层，nodes 层代码无需更改
- 如需添加新的 UI 面板，只需在 `ui/` 目录下添加新文件并在 main_window.py 中挂载即可，不影响其他模块

**3. 项目初始化包依赖**

核心依赖包：

| 包名 | 版本 | 用途 |
|---|---|---|
| PyQt5 | 5.15.10 | GUI 框架 |
| NodeGraphQt | 0.6.44 | 节点图编辑器框架 |
| pywinauto | latest | Windows GUI 自动化（Win32 后端） |
| uiautomation | latest | Windows UI Automation（UIA 后端） |
| PyAutoGUI | latest | 跨平台鼠标键盘模拟（辅助方案） |


### 总结

以上架构方案遵循以下核心原则：

- **关注点分离**：UI、业务逻辑、自动化执行各司其职，任何一层的变化不会波及其他层，这是 GUI 应用程序设计的黄金法则
- **开闭原则**：新增节点类型无需修改 core 和 ui 的现有代码，实现"对扩展开放，对修改关闭"
- **单一职责**：每个模块只负责一个明确的功能领域，node、automation、ui 的职责边界清晰不重叠
- **低耦合高内聚**：模块间通过事件总线通信，同一个模块内的方法紧密协作——这是衡量架构质量的核心指标

通过这种模块化架构，项目在初始阶段即可保持代码整洁有序，随着功能不断增加，只需在对应模块的目录下添加新文件，而无需大规模重构现有代码。