# UI_DESIGN.md — 「自动工作流设计器」UI 全面重设计方案

> 版本：1.0（2026-09-03）
> 方向：**深色专业工具风**（Blender / Nuke / UE 蓝图一系），**全面重做**，图标统一 **qtawesome** 矢量图标。
> 范围约束：只动「表现层与布局结构」，**不改任何执行/自动化逻辑**（executor、automation、nodes 的业务行为保持不变）。

---

## 1. 背景与现状问题

基于对 `ui/` 全部代码与运行截图的审查，当前 UI 的核心问题：

| # | 问题 | 证据 |
|---|------|------|
| 1 | 画布浅色底 + 纯黑节点，反差生硬；节点全部使用 NodeGraphQt 默认黑色，无任何 `set_color` 定制 | `nodes/*.py` 无 set_color 调用；截图 img.png |
| 2 | 工具栏/节点库/关于框大量使用 emoji 当图标（📄📂💾🗑️▶️…），跨机器渲染不一、大小不齐、无法跟随主题 | `ui/actions.py:119-186`、`nodes_panel.py:42` |
| 3 | 节点库图标映射失效：`NodeColors.NODE_COLORS/NODE_ICONS` 的 key 是 `'Start'/'End'/'Process'…`，而实际匹配值是 `'workflow.StartNode'` 这样的类型串，**全部落到 default（橙色闪电）** | `ui/styles.py:96-118` vs `core/manager.py:107` |
| 4 | 状态栏整条蓝色高亮（`accent` 背景），视觉噪音大、不像专业工具 | `ui/styles.py:223-227` |
| 5 | 灰阶混乱：`primary_bg/secondary_bg/tertiary_bg` 三层灰在菜单/工具栏/dock 标题间无明确层级语义；浅色主题下 `log_bg` 与主背景撞色 | `ui/styles.py:15-90` |
| 6 | dock 标题栏粗体 14px 居中，占高且土气；节点库 `minWidth=220/maxWidth=320` 不可收起 | `ui/styles.py:198-206`、`nodes_panel.py:134-135` |
| 7 | 设置对话框「工作流设置/日志设置」两组是摆设（自动保存/超时/日志级别/行数均未接线） | `ui/settings_dialog.py:52-91` |
| 8 | 日志面板信息层级混乱：浅色主题下 INFO 正文整行蓝色（`#0066cc`），深色主题下 INFO 级别徽章是荧光绿（`#00ff00`），时间戳/级别/正文缺乏一致的主次关系 | `ui/log_panel.py:59-89` |
| 9 | QSS 分散在 8 个 generator 函数中，样式字符串内嵌在 `nodes_panel.py`、`about_dialog.py` 等处重复出现；换主题靠逐个 setStyleSheet，样式漂移风险高 | `ui/styles.py` 全文件、`main_window.apply_theme` |

**结论：推倒重来主题层与布局细节，统一到一套 Design Token + 单一 QSS 入口。**

---

## 2. 设计原则

1. **深色画布优先**：节点图是主角，画布用最深色，四周面板逐级抬高（elevation），视线聚焦中央。
2. **颜色即语义**：颜色只用于表达「节点分类」与「运行状态」，不用于装饰。同一分类在节点库、画布节点头、搜索结果中颜色严格一致。
3. **密度与留白**：工具类界面信息密度优先，但统一间距基数（4px 网格），拒绝现在 2/3/4/6/8/10px 混用。
4. **一屏一眼**：执行状态（空闲/运行中/暂停/失败）必须在工具栏执行区、状态栏、画布节点三处同步可见。
5. **可落地**：所有设计均映射到已验证的 API（NodeGraphQt 0.6.44 `set_color/set_icon/set_background_color/set_grid_color/set_grid_mode/get_zoom`；PyQt5 QSS；qtawesome）。

---

## 3. 设计规范（Design Tokens）

### 3.1 色板

替换 `ThemeColors` 为单一深色主题（本次**不做浅色主题**，避免双主题色值对称维护成本；架构上保留多主题能力）。

```python
# ui/tokens.py —— 唯一色值来源（实际落地即此名：DARK）
DARK = {
    # ── 背景层级（由深到浅） ─────────────────────────
    'bg_canvas':    '#16181d',   # 画布（最深）
    'bg_window':    '#1e2127',   # 主窗口底
    'bg_panel':     '#23262e',   # 面板 / 工具栏 / 菜单栏 / 状态栏
    'bg_elevated':  '#2a2e37',   # 输入框 / 悬浮菜单 / 卡片
    'bg_hover':     '#31353f',
    'bg_active':    '#3a3f4b',

    # ── 边框 ───────────────────────────────────────
    'border':       '#333844',
    'border_strong':'#454b58',

    # ── 文字 ───────────────────────────────────────
    'text':         '#e8eaed',   # 主文字
    'text_2nd':     '#a8b0bb',   # 次要文字 / 图标默认色
    'text_dim':     '#6b7280',   # 占位 / 禁用 / 时间戳

    # ── 强调色 ─────────────────────────────────────
    'accent':       '#4c8dff',
    'accent_hover': '#6ba2ff',
    'accent_press': '#3a6fd0',
    'selection':    'rgba(76,141,255,0.25)',

    # ── 语义色（深色底可读性校准过） ───────────────
    'success':      '#3fb950',
    'warning':      '#d29922',
    'error':        '#f85149',
    'critical':     '#f85149',
    'info':         '#58a6ff',

    # ── 画布网格（低对比线状，见 §5.4） ────────────
    'grid_dot':     '#262a31',

    # ── 日志搜索高亮 ───────────────────────────────
    'search_highlight': '#d29922',
    'search_text':      '#16181d',
}
```

> 设计期曾保留一份旧键名兼容映射（`primary_bg` 等）用于新旧样式双轨过渡；
> P3 删除 `ui/styles.py` 时该映射一并移除，现在全局只有 `DARK` 一套语义键。

### 3.2 节点分类色（颜色即语义的核心）

分类键采用**中文**（与 `NODE_NAME` 全中文的代码风格一致，且 `nodes/window_nodes.py`、`image_nodes.py` 原本就已声明中文 `NODE_CATEGORY`）。8 个分类归入 3 个分组，分组即节点库的折叠小节与画布右键菜单的一级菜单。

| 分组 | 分类键 | 覆盖节点 | 色值 | qtawesome 图标 |
|------|--------|----------|------|----------------|
| 流程 | `开始` | 开始 | `#3fb950` 绿 | `fa5s.play-circle` |
| 流程 | `结束` | 结束 | `#f85149` 红 | `fa5s.stop-circle` |
| 控制流 | `条件判断` | 条件判断 | `#d29922` 琥珀 | `fa5s.code-branch` |
| 控制流 | `循环` | 循环判断、循环 | `#a371f7` 紫 | `fa5s.sync` / `fa5s.sync-alt` |
| 控制流 | `等待` | 等待 | `#8b949e` 灰 | `fa5s.clock` |
| 自动化操作 | `输入操作` | 点击、键盘输入 | `#58a6ff` 蓝 | `fa5s.mouse-pointer` / `fa5s.keyboard` |
| 自动化操作 | `窗口操作` | 查找窗口、激活窗口 | `#39c5cf` 青 | `fa5s.window-restore` / `fa5s.layer-group` |
| 自动化操作 | `图像识别` | 查找图片 | `#db61a2` 洋红 | `fa5s.search-plus` |

分类色同时用于：节点头色条（`node.set_color`）、节点库左侧色条与图标 tint、连线颜色（见 §5.4）。

**声明机制（避免两处事实来源）**：

- `ui/tokens.py` 只存「分类 → 色值/图标/所属分组」表 `NODE_CATEGORIES` 与分组顺序 `GROUP_ORDER`；
- 具体节点归属哪一类、用哪个图标，由节点类自己声明 `NODE_CATEGORY` / `NODE_ICON`（纯字符串，与节点定义同处）；
- `core/manager.py` 的 `get_available_nodes()` 把 `category` / `icon` / `description` 一并交给 UI；
- 未声明分类的节点回落到 `NODE_STYLE_DEFAULT`（灰 + `fa5s.cube`）。

这是**纯属性声明**，不涉及任何执行逻辑。

### 3.3 字体

| 用途 | 字体 | 字号 |
|------|------|------|
| 全局 UI | `Microsoft YaHei UI` | 9pt |
| 节点名（画布内） | NodeGraphQt 自绘 | 默认（随 QSS 无法改，接受） |
| 日志/等宽 | `Consolas, Cascadia Mono, Courier New` | 9pt |
| 状态栏 | 同全局 | 8.5pt，次要信息用 `text_2nd` |

全局字体通过 `QApplication.setFont()` 设置一次，不再各控件散设。

### 3.4 间距与圆角

- 间距基数 **4px**：控件内边距 4/8，组间距 8/12，面板外边距 8。
- 圆角：按钮/输入框 4px，卡片/菜单 6px，dock 标题不做大圆角。
- 交互热区：工具栏按钮 ≥ 28×28，节点库条目高 52px（图标 28px 圆角方块 + 名称 12px + 描述 11px）。

---

## 4. 布局总览

```
┌────────────────────────────────────────────────────────────────────┐
│ 菜单栏  文件 编辑 运行 视图 工具                        (bg_panel) │
├────────────────────────────────────────────────────────────────────┤
│ 工具栏  [新建|打开|保存] │ [▶启动] [⏸][⏯][⏹] │ [验证] │ [🔍 搜索] │
│         常规按钮描边灰   │ 启动=绿实心按钮组   │        │   主题切换 │
├──────────────┬──────────────────────────────────────────┬──────────┤
│ 节点库 (可折叠)│              画布 (bg_canvas)            │  属性面板  │
│ ┌──────────┐ │                                          │ (P2, 可选)│
│ │🔍 搜索节点│ │        深色底 + 点阵网格                  ├──────────┤
│ ├──────────┤ │        节点=深色底+分类色头               │          │
│ │▾ 流程     │ │                                          │          │
│ │  ● 开始   │ │   [开始]══▶[等待]══▶[循环判断]══▶[结束]   │          │
│ │  ● 结束   │ │        执行状态角标：✓绿/▶蓝闪/✗红        │          │
│ │▾ 控制流   │ │                                          │          │
│ │  ● 条件…  │ │                                          │          │
│ │  ● 循环…  │ │                                          │          │
│ │▾ 输入操作 │ │                                          │          │
│ │  …        │ │                                          │          │
│ └──────────┘ │                                          │          │
├──────────────┴──────────────────────────────────────────┴──────────┤
│ 日志  [级别▾][全部][DEBUG][INFO][WARN][ERROR]  [清空] [⤓导出]       │
│ 09:01:22 INFO  节点完成: 等待 (3.00s)                               │
│ 09:01:23 ERROR 执行节点失败: 点击                                    │
├────────────────────────────────────────────────────────────────────┤
│ ● 就绪   节点 5 · 连线 6   耗时 12.3s   未命名.json   缩放 100%     │
└────────────────────────────────────────────────────────────────────┘
```

要点：

1. **布局骨架不变**（菜单 + 工具栏 + 左节点库 + 中央画布 + 底部日志），但全部视觉重做；新增「视图」菜单（网格开关、缩放、面板显隐）。
2. **节点库改为 QTreeWidget/分节列表 + 顶部搜索框**，支持按名称/拼音首字母过滤；保留现有拖拽机制（`mousePressEvent/mouseMoveEvent` 逻辑平移到新控件）。
3. **状态栏重做**：取消蓝色整条；左侧状态点 + 消息，右侧常驻指标（节点数、连线数、执行耗时、当前文件、缩放比）。`get_zoom()` 已验证可取缩放。
4. **属性面板（右侧）为 P2 可选项**，本期不实施，布局先预留。

---

## 5. 组件级设计

### 5.1 菜单栏

- 背景 `bg_panel`，底部 1px `border`；菜单项 hover 用 `bg_elevated`（不再用 accent 蓝色块刷菜单项，选中才用 `selection` 半透明蓝）。
- QMenu 弹层背景 `bg_elevated` + 1px `border_strong` + 6px 圆角 + 阴影（`QGraphicsDropShadowEffect` 或 `setWindowFlags(Qt.Popup)` 系统阴影）。
- 新增「视图」菜单：网格线开关、重置缩放(Ctrl+0)、放大/缩小、日志面板显隐、节点库面板显隐。

### 5.2 工具栏（重做重点）

- 单行、`Qt.ToolButtonIconOnly`（图标 + tooltip + 状态栏提示），高 36px；按钮分组用 1px 竖分隔线（`border` 色），不用现在的 `addSeparator()` 默认样式。
- 图标全部 qtawesome，尺寸 18px，颜色 `text_2nd`，hover `text`。

| 组 | 按钮 | 图标 | 状态样式 |
|----|------|------|----------|
| 文件 | 新建/打开/保存 | `fa5s.file` / `fa5s.folder-open` / `fa5s.save` | 常规描边按钮 |
| 编辑 | 清空 | `fa5s.trash-alt` | hover 变 `error` 色 |
| 执行 | **启动** | `fa5s.play` | **绿色实心主按钮**（`success` 底 + 深色图标），运行中禁用并降透明度 |
| 执行 | 暂停 | `fa5s.pause` | 暂停可用时 `warning` 色 |
| 执行 | 恢复 | `fa5s.forward` | 可用时 `success` 色 |
| 执行 | 终止 | `fa5s.stop` | 可用时 `error` 色 |
| 校验 | 验证 | `fa5s.check-double` | 常规 |
| 杂项 | 搜索日志 | `fa5s.search` | 常规 |
| 杂项 | 主题切换（预留） | `fa5s.adjust` | 常规 |

> 执行按钮组的状态切换沿用现有 `ExecutionController` 状态机（`start_action/pause_action/resume_action/stop_action` 属性名不变），只改按钮渲染。启动/暂停/恢复/终止按钮的图标随启用态换色：`qtawesome.icon('fa5s.play', color=...)`。

### 5.3 节点库面板

- 顶部搜索框：圆角 4px，`bg_elevated` 底，占位文字「搜索节点…」(`text_dim`)，左侧 `fa5s.search` 小图标；输入即时过滤。
- 分组标题：12px `text_2nd` 大写风格 + 分类色小圆点 + 折叠箭头（`fa5s.chevron-right/down`）。
- 节点条目（重做 `DraggableNodeItem`）：

```
┌─[色条3px]────────────────────────────────┐
│ [icon 28px 圆角方块]  条件判断             │
│   (分类色 15% 透明底)  根据表达式走分支     │
└──────────────────────────────────────────┘
```

- 图标方块：分类色 15% 透明度底 + 分类色前景图标（替代现在的纯色底 + emoji）。
- hover：底色 `bg_hover` + 左色条加宽至 4px；pressed 更深。去掉 QSS `box-shadow`（Qt 不支持，现在是无效声明）。
- **修复映射 bug**：条目数据改用 `cls.NODE_CATEGORY` → 分类表查色/图标，不再用对不上的 `'Start'` 这类 key。
- 面板宽度 240px 固定，可通过工具栏/视图菜单整体隐藏。

### 5.4 画布与节点（视觉重灾区）

| 项 | 现状（重设计前） | 实际交付 | 落地方式 |
|----|------|--------|----------|
| 背景 | 浅色主题下 `#f5f5f5` | `bg_canvas #16181d` | `node_graph.set_background_color(*tokens.rgb(...))` |
| 网格 | 线状 `#3c3c3c` | **低对比线状** `#262a31` | `set_grid_mode(GRID_DISPLAY_LINES)` + `set_grid_color(...)` |
| 节点 | 全黑默认 | 深色节点底 + 分类色标题条 | `WorkflowNode.__init__` 中 `self.set_color(r,g,b)`（声明式、跟类走，反序列化旧文件同样生效） |
| 节点图标 | 无 | 分类矢量图标进节点头部 | `set_icon()` 只接受**图片路径**，故由 `ui/icons.node_icon_path()` 把 qtawesome 字形渲染成透明 PNG 落到系统临时目录（按 名称+颜色+尺寸 命名，存在即复用） |
| 执行状态 | 节点上方绿字 ✓成功/秒数 | 机制不变，颜色改取 `tokens` 的 success/error | `base_node.update_status()` 只换色值常量 |
| 连线 | 橙黄色 | **按来源节点分类色着色**（+ 曲线走向） | 见下方说明 |

**关于点阵网格（原计划 → 实际）**：原设计想用 `GRID_DISPLAY_DOTS`，实测该模式在 NodeGraphQt 0.6.44 上会让进程**直接 abort**（`NodeScene._draw_dots()` 里 `pen.setWidth(grid_size / 10)` 把 float 传给 int 参数，发生在绘制虚函数中，无 Python 异常、无 stderr）。因此改用线状网格 + 低对比网格色 `#262a31`（比画布底仅亮 10 左右），观感同样克制。

**关于连线着色（原列为风险项 → 已交付）**：NodeGraphQt 未提供 NodeGraph 级连线配色 API，但场景中的 `PipeItem` 有公开的 `output_port` / `color` / `style` 属性。`NodeGraphPanel.refresh_pipe_colors()` 遍历场景 `PipeItem`，取 `output_port.node.color`（来源节点的分类色）按 85% 不透明度写回并 `set_pipe_styling()`；由 `event_bus.graph_changed` 触发、60ms 去抖，整段包 try/except，失败只记调试日志，绝不影响连线功能。

### 5.5 日志面板

- 标题行内联到面板顶部（不再是居中粗体 dock 标题）：左侧 `fa5s.terminal` + 「日志」+ 级别过滤胶囊按钮组（全部/DEBUG/INFO/WARN/ERROR，点击切换激活态，激活=对应语义色描边）+ 右侧「清空」`fa5s.eraser`。
- 条目格式（重排 `TextEditHandler._insert_log`）：

```
09:01:22  INFO   节点完成: 等待 (3.00s)
└ 等宽 time   └ 徽章   └ 正文
```

- 时间戳 `text_dim`；级别徽章：固定 7 字符宽，DEBUG `text_dim`、INFO `info 蓝`、WARNING `warning` 加粗、ERROR/CRITICAL `error` 加粗；正文统一 `text` 色（**去掉 INFO 正文整行蓝色**，蓝色只留给级别徽章）。
- 正文颜色仅两处例外：`ERROR/CRITICAL` 正文用 `error` 色——保证报错扫一眼可见。
- 搜索栏（现有 `LogSearchBar`）：保留交互，样式并入统一 QSS，高亮色改 `#d29922`（warning 琥珀，深浅底都可读）。
- 日志行数上限：现有设置未接线，本期把「最大日志行数」接到 `TextEditHandler`（超出裁剪最旧行），「日志级别过滤」接 `handler.setLevel()`——属于表现层接线，不动执行逻辑。

### 5.6 状态栏（重做）

- 背景 `bg_panel`，顶部 1px `border`，高度 26px，文字 8.5pt。
- 左：状态圆点（10px）+ 消息。状态点颜色 = 空闲 `text_dim` / 运行中 `success`（闪烁可选，P2）/ 暂停 `warning` / 失败 `error`。
- 右（固定分栏，满足上下对齐偏好）：`节点 5 · 连线 6 | 耗时 12.3s | 未保存 * | 100%`，标签 `text_2nd`、数值 `text`；文件有未保存修改时文件名后加 `*`（订阅 `file_actions.current_file` 变更）。
- 节点/连线计数、缩放比通过 graph 信号（`node_created/nodes_deleted/port_connected/port_disconnected`，已存在于 `core/graph/signals.py`）与 `get_zoom()` 更新——替换现在「就绪 - 当前有 N 个节点」拼接字符串的模糊做法。

### 5.7 设置与关于对话框

**设置**：
- 精简为「外观」（主题：深色[唯一]｜网格线开关｜日志行数｜日志级别）四项，**移除未接线的「自动保存/执行超时」两组摆设**（未来接线时再加回，避免假 UI）。
- 布局改单列 QFormLayout，按钮区右对齐：`应用` 次级按钮 + `确定` 主按钮（accent 实心）+ `取消` 描边。

**关于**：
- 保留三 Tab 结构；图标位的 emoji 🚀 换 qtawesome `fa5s.project-diagram` + accent 色；技术信息 Tab 内容与 README 对齐（当前写的 pywinauto/Python 3.7+ 与实际依赖 uiautomation/3.11+ 不符，顺带修正文案）。

### 5.8 拖拽与右键菜单（画布）

- 右键菜单：现在是「平铺 11 个节点」的裸列表，重做为**两级菜单**（一级=分类 6 项，二级=该类节点），样式套统一 QMenu。
- `view_dragEnterEvent` 中遗留的 `self.logger.error(event.mimeData().hasText())` 调试语句移除（顺手清理，非行为变更）。

---

## 6. 主题架构（styles.py 重构）

```
ui/
  tokens.py        # §3.1 色板 + 字体 + 间距 + 节点分类表（唯一色值来源）
  qss.py           # build_qss() → 一整份全局样式字符串；set_kind() 打按钮语义标记
  icons.py         # qtawesome 封装：按状态着色 + 缓存 + 节点库色块 + 画布图标 PNG 落盘
  theme.py         # ThemeState：界面状态（主题/网格/日志捕获级别/显示过滤/最大行数）
  title_bar.py     # DockTitleBar：面板自定义标题栏（图标 + 标题 + 折叠按钮）
  status_bar.py    # StatusBarView：状态点 + 消息 + 定宽指标分栏
  log_filter_bar.py# LogFilterBar：级别过滤胶囊 + 清空 + 导出
  styles.py        # 已删除（其状态职责移交 theme.py，样式职责移交 qss.py）
```

关键决策：

1. **单一 QSS 入口**：`app/main.py` 里 `app.setStyleSheet(build_qss())` 一次性应用到全应用（菜单、工具栏、面板、对话框、滚动条、输入控件），**废除**「每组件一个 generator + 各处散 setStyleSheet」。组件特殊样式用 `objectName` / 动态属性选择器纳入同一份 QSS；`qss.set_kind(button, 'primary')` 负责 `[kind="..."]` 语义按钮。
2. **qtawesome 主题联动**：`icons.py` 统一从 tokens 取色生成 QIcon 并做缓存；`node_icon_path()` 解决 NodeGraphQt `set_icon()` 只吃文件路径的限制。
3. **NodeGraphQt 画布色不走 QSS**：由 `NodeGraphPanel.apply_canvas_theme()` 调 `set_background_color/set_grid_color/set_pipe_style`，与 QSS 共用同一份 tokens（画布 `#16181d` 与 `bg_canvas` 永远一致）。
4. **面板结构改为嵌套分割器**：原实现把 `QDockWidget` 塞进 `QSplitter`（既不是正常停靠、也不能浮动画布），本次统一改为「垂直分割器（上半＝水平分割器[节点库面板 | 画布] ／ 下半＝日志面板）」，配自定义标题栏。显隐由「视图」菜单控制，行为可预期。
5. **保留多主题能力但不做浅色**：tokens 是 dict，未来加浅色＝新增一份 dict + 一次刷新；QSS 字符串零改动。`ThemeState.set_theme('light')` 目前回落深色并打警告，不假装支持。

---

## 7. 实施阶段与完成情况

> 每阶段结束都做了实机启动 + 截图核对；验证脚本用离屏 `grab()` 与程序化断言，不靠肉眼猜。

**P0 — 基础设施（已完成）**
- 新增 `ui/tokens.py`、`ui/qss.py`、`ui/icons.py`；`requirements.txt` 加 `QtAwesome==1.4.2` 并装入 venv。
- `app/main.py` 接入全局字体 + 全局 QSS；`ui/styles.py` 先改为薄壳（`get_stylesheet()` 返回空串），避免新旧样式互相覆盖。
- 验证：应用正常启动，深色主题全局生效。

**P1 — 主框架视觉（已完成）**
- 工具栏改 qtawesome 图标 + 分组分隔线 + 执行按钮 `objectName` 语义色；新增「视图」菜单（网格线、缩放三件套、面板显隐）。
- 状态栏重做为 `StatusBarView`（状态点 + 消息 + 定宽指标）；面板改自定义标题栏 `DockTitleBar`。
- 顺带修正：`build_tool_bar` 必须先于 `build_menu_bar`（运行菜单复用工具栏 QAction，状态自动同步）。
- 验证：截图核对；执行状态机四个按钮可用态与改前一致。

**P2 — 画布与节点库（已完成）**
- 节点基类接分类色与图标；11 个节点类声明 `NODE_CATEGORY`/`NODE_ICON`；`get_available_nodes()` 输出 category/icon/description。
- 画布深色底 + 低对比线状网格 + 曲线连线 + **连线按来源节点分类色着色**；右键菜单两级化。
- 节点库重做：搜索框 + 3 个可折叠分组 + 分类色条/图标块；拖拽改为条目自持 `QDrag`；修复颜色/图标映射失效 bug。
- 验证（`p2_test.py`）：11 种节点分类色逐一对齐色板；连线取到起点绿色 `(63,185,80,217)`；分组 2/4/5 共 11 项；搜索「循环」命中 2 项；折叠生效。

**P3 — 日志、对话框、收尾（已完成）**
- 日志三段式格式（去掉双时间戳双级别）、级别徽章配色、级别过滤、行数上限、清空、导出；搜索高亮改 `ExtraSelections`。
- 设置对话框只留真正生效的四项并全部接线（主题/网格/捕获级别/最大行数）；移除未接线的「自动保存/执行超时」假控件。
- 关于对话框改矢量图标 + 技术栈文案与实际依赖对齐；删除 `ui/styles.py` 与旧键名映射；README 与本文件同步。
- 验证（`p3_test.py`、`smoke_test.py`）：见 §10。

---

## 8. 验收清单

- [x] 全应用单一深色主题，无灰阶撞色；画布为最深层级（P0 起截图核对）
- [x] 工具栏/菜单/节点库/对话框图标全部 qtawesome，无 emoji 图标（P1/P3 截图）
- [x] 11 种节点在画布上分类色正确，与节点库色条/图标一致（`p2_test.py` 逐类断言）
- [x] 执行状态在节点角标、工具栏按钮、状态栏状态点三处同步（`smoke_test.py`）
- [x] 节点库搜索过滤可用；拖拽创建行为与改前一致（`p2_test.py`）
- [x] 状态栏指标定宽分栏、上下对齐；缩放百分比实时刷新（`p3_test.py` + 案例图）
- [x] 设置对话框无假控件（未接线项已移除）
- [x] 日志级别过滤与行数上限实际生效（`p3_test.py`：200 条压测后缓存裁剪到上限）
- [x] 主题入口不假装支持浅色（回落深色 + 警告），组合控件配色随 tokens 统一
- [x] 零散 `setStyleSheet` 清零，样式全部收敛到 `qss.py` + tokens

## 9. 风险与注意事项（实施后的实际结论）

1. **必须用项目 venv 解释器运行**：在 Windows Store 版 Python 下 `NodeGraph()` 构造即让进程以 `0xC0000409` 退出（无任何 Python 异常）。排查时极易误判成本次改动的锅，务必先用 venv 复现。
2. **点阵网格不可用**：`GRID_DISPLAY_DOTS` 在 NodeGraphQt 0.6.44 会硬崩溃（`pen.setWidth(float)`），已改用低对比线状网格。
3. **只读 QTextEdit 不能用 `mergeCharFormat` 改文档**：日志搜索高亮的旧写法在空文档上会直接 abort；已改为 `setExtraSelections` 叠加层。
4. **高 DPI 下缩放读数需自定基准**：`NodeGraph.get_zoom()` 假设视图基准变换为 1.0，而 Windows 170% 缩放下 `QGraphicsView` 基础 m11≈0.586，会把「视觉 100%」报成 59%/00%。现以首次布局完成后的变换为基准算相对百分比。
5. **定宽列要按最宽形态取样**：按「位数 × '0' 宽度」预留时，`% . s` 比 `0` 宽，右对齐会裁掉最左字符（`100%` 显示成 `00%`）。
6. **`set_icon()` 只接受图片路径**：矢量图标需落盘为 PNG（已放系统临时目录并缓存），不要指望能传 QPixmap。
7. **节点色必须设在 `__init__`**：放在创建回调里会导致打开旧 `.json` 时节点失色。
8. **面板结构由 QDockWidget 改为嵌套分割器**：不再支持拖出浮动，换来可预期的显隐与折叠；若需要浮动画布/多面板，应作为独立需求重新设计。
9. **QSS 中不要写 `box-shadow`**：Qt 不支持，旧样式表里多处是无效声明，新 QSS 一律不写；弹层阴影如需，用 `QGraphicsDropShadowEffect`。
10. **节点内部字体不可控**：节点标题与端口文字由 NodeGraphQt 自绘，QSS 不生效，沿用其默认（深色节点底上自带浅色字，可读性可接受）。

---

## 10. 节点显示与属性页（节点体系二次设计）

节点属性全部移入属性对话框（双击 / 右键→属性）后，节点体只保留「标题 + 端口 + 摘要 + 执行状态」，
节点相关的 UI 在此基础上做了二次设计。

### 10.1 画布上的节点显示（`nodes/base_node.py`）

| 项 | 设计 | 落地 |
|----|------|------|
| 摘要胶囊 | 属性改动的即时反馈：条件表达式、循环次数等摘要以胶囊形式显示在节点体正下方（居中），`bg_elevated` 底 + `border` 描边 + **分类色文字**，替代原先 7pt 贴底暗字（几乎不可见） | `_SummaryItem(QGraphicsTextItem)` 重写 `paint()` 画圆角底；`set_summary()` 居中定位到节点高 + 2 |
| 端口语义色 | 输入端口 = `info` 蓝（数据进入）、输出端口 = `success` 绿（数据流出），一眼分清方向 | 覆写 `add_input/add_output`，走 NodeGraphQt 的 `color` 参数，调用方显式传色优先 |
| 宽度自适应 | 只放宽、不收窄（NGQ 默认宽度为下限）：按行计算 `6 + 输入文本宽 + 24 间距 + 输出文本宽 + 19 端口边距`，标题需求一并取 max | `_fit_width()`，`QTimer.singleShot(0)` 等子类加完端口后执行；端口文本项经 `view.get_*_text_item(port.view)` 获取（**按 PortItem 对象索引，不是端口名**） |
| hover 摘要 | 鼠标悬停节点即显示全部已配置属性，免开属性页 | `_tooltip_text()` 汇总 `_prop_defs`，`set_property()` 覆写中随改随刷 |
| 执行状态 | 机制沿用：成功/失败取 `tokens` 的 success/error 色 | `update_status()` |

注意：`BaseNode.__init__` 早期（`set_disabled`）内部就会走 `set_property`，
任何覆写都必须用 `hasattr(self, 'summary_text')` 之类的守卫，否则节点创建即崩。

### 10.2 属性面板（内嵌主窗口右侧，`ui/node_properties_panel.py`）

属性编辑从**独立 QDialog 弹窗**改为**主窗口右侧内嵌面板**（布局三栏：节点库 | 画布 | 属性面板，
面板宽 340px，可经「视图 → 属性面板」显隐）。独立窗口方案存在三个结构性问题——
点击主窗口即被切到后台、点多少个节点就堆积多少个窗口、多窗口「取消回滚快照」互相吞改动——
内嵌面板使其连根消失。

- **触发**：单击选中节点（`node_selected` 信号）、双击节点（`node_double_clicked`）、
  右键→属性，三者都会让面板显示该节点；标题栏同步显示「属性 · 节点名」；
  取消全部选中（`node_selection_changed` 空列表）面板回到空态引导文案。
- **结构**：分类色图标块 + 节点名 + 「还原」按钮 → 可滚动表单或专用编辑器
  （图片/OCR/鼠标，与原弹窗共用同一批编辑器类，编辑器依赖的
  `_secondary_button_style/_accent_button_style/window` 由面板提供）。
- **就地写回 + 可还原**：选中时刻快照全部表单属性值，「还原」一键回滚并刷新摘要/tooltip；
  编辑器接管节点（图片/OCR/鼠标）属性不在表单快照内，「还原」按钮隐藏（其内部状态由编辑器自管）。
- **窄版适配**：图片编辑器按 340px 重排——阈值独占一行、偏移 X/Y 一行均分、预处理独占一行、
  命中后自动点击独占一行，「后台离屏识别」文案缩短（细节说明保留在 tooltip）。
- **实现注意**：`QVBoxLayout(self)` 在控件已有布局时会被 Qt 静默拒绝——面板在
  `show_node/clear_node` 重建内容前必须先 `_clear_layout()`（旧布局挂到临时 QWidget 丢弃），
  否则新内容全部变成孤儿控件、面板停留在上一次状态。
- 修掉的既有 bug：属性表单行被重复 addRow（双入表导致布局错乱、大块空白）、
  check 类属性行从未加入布局（复选框不可见）。
- **标题栏箭头 = 折叠为贴边细条**（节点库/属性/日志三面板通用，与「视图菜单隐藏」是两种不同状态）：
  - 箭头折叠 → 面板收成 24px 细条：左右面板为竖条（文字旋转 90°，如「节点库 ▸」「◂ 属性」），
    日志为底部横条（「︿ 日志」），**点击细条即展开**并恢复展开前尺寸；
  - 视图菜单取消勾选 → 面板彻底隐藏（细条也不显示），重新勾选时恢复展开态；
  - 属性面板处于隐藏或细条状态时选中节点，会自动唤起并展开（`show_node_properties`）。
  - 实现要点：① 用「隐藏常规页 + 显示细条」而非 `QStackedLayout`——后者最小尺寸取所有页
    （含隐藏页）最大值，隐藏页继续占位会让分割器留下空白；② 只设 `maximumWidth/Height(24)`
    仅钳制控件本身，画布不会自动吃掉腾出的空间，必须再 `setSizes` 把差额补给最大格
    （`_rebalance_splitter`）。

---

## 11. 实施结果

**交付范围**：P0–P3 全部完成，UI 层从「按组件生成 QSS + 散落 setStyleSheet」重构为「tokens + 单一全局 QSS + 语义 objectName/属性选择器」，并落地深色专业工具风、qtawesome 矢量图标、节点分类色体系、状态栏指标、日志过滤与导出。执行/自动化逻辑（`core/executor.py`、`automation/*`、节点 `execute()`）未改动。

**验证证据**（脚本均为程序化断言 + 离屏截图，非肉眼判断）：

| 验证项 | 结果 |
|--------|------|
| 11 种节点分类色 | 逐类比对色板，`颜色不符: 无` |
| 连线着色 | 起点为「开始」的连线取到 `(63,185,80,217)` |
| 节点库分组 | 流程 2 / 控制流 4 / 自动化操作 5，合计 11 |
| 搜索过滤 | 「循环」命中 2 条、分组计数同步 |
| 分组折叠 | 折叠后内容隐藏 |
| 日志格式 | 单时间戳 + 级别徽章，无双时间戳 |
| 级别过滤 | 过滤到 ERROR 只剩 1 条，缓存仍保留全量 |
| 行数上限 | 200 条压测后缓存裁剪到上限 50 |
| 清空 / 导出 | 清空后计数归零；导出文件行数与缓存一致 |
| 搜索导航 | 5 条匹配，`1/5 → 2/5 → 5/5` 循环正常 |
| 设置接线 | 捕获级别写根记录器、最大行数写处理器、网格写画布 |
| 端到端执行 | 开始→等待(1s)→结束：`running → success`，耗时 `1.0s`，三节点均显示 `✓ 成功`，按钮可用态正确 |
| 空工作流校验 | 被拦下并提示「工作流为空，请添加节点」 |

**过程中修掉的既有缺陷**（非本次设计目标，但阻塞或影响观感）：

- 节点库颜色/图标映射失效（key 与实际节点类型串不匹配，全部落到默认值）
- 日志双时间戳 + 双级别（`[11:52] INFO | 2026-09-03 11:52 - INFO - 正文`）
- 日志搜索在空文档上高亮导致进程 abort（`mergeCharFormat` 改只读文档）
- 状态栏 `100%` 被裁成 `00%`（定宽取样未考虑 `% . s` 比 `0` 宽）
- 高 DPI 下缩放读数失真（`get_zoom()` 未考虑 `QGraphicsView` 基础变换）
- `QDockWidget` 被塞进 `QSplitter` 的结构误用（改为分割器 + 自定义标题栏）
- 设置对话框中未接线的「自动保存 / 执行超时」假控件（移除）
