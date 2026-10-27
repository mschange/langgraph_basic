# LangGraph Basic

LangGraph 入门示例：从图构建到状态、消息、控制流与动态分支。

## 环境要求

- Python 3.10 – 3.12（暂不建议 3.14）
- 依赖见 `requirements.txt`

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

涉及 LLM 的示例还需在项目根目录配置 `.env`：

```
DEEPSEEK_API_KEY=your_api_key_here
```

## 示例一览

### 第一章：构建图

| 文件 | 内容 |
|------|------|
| `01_first_graph.py` | 五步构建流程：State → Node → Edge → compile → invoke |
| `02_mermaid_viz.py` | 用 `draw_mermaid()` 导出 Mermaid 文本 |
| `03_png_export.py` | 用 `draw_mermaid_png()` 导出 PNG（需 `grandalf`） |
| `04_explicit_naming.py` | `add_node(name, func)` 显式命名注册节点 |
| `05_dataclass_state.py` | 用 `dataclass` 定义状态 |
| `06_pydantic_state.py` | 用 Pydantic `BaseModel` 定义状态（生产推荐） |

### 第二章：状态与消息（对应 `02.md`）

| 文件 | 内容 |
|------|------|
| `07_add_messages.py` | `add_messages` 按 id 智能合并消息 |
| `08_default_overwrite.py` | 无归约器时的默认覆盖行为 |
| `09_node_receives_state.py` | 节点如何接收状态快照 |
| `10_partial_update.py` | 部分更新：只返回需要修改的字段 |
| `11_overwrite_reducer.py` | `Overwrite` 临时绕过归约器 |
| `12_input_output_schema.py` | `input_schema` / `output_schema` 隔离 |
| `13_messages_state.py` | `MessagesState` + DeepSeek 对话 |

### 第三章：控制流（对应 `03.md`）

| 文件 | 内容 |
|------|------|
| `14_add_edge.py` | `add_edge` 基础有向边 |
| `15_add_sequence.py` | `add_sequence` 批量顺序连接 |
| `16_omit_end.py` | END 可省略，START 不能省略 |
| `17_static_fanout.py` | 从 START 扇出的静态并行分支 |
| `18_conditional_edges.py` | `add_conditional_edges` 条件路由 |
| `19_path_map.py` | `path_map` 将别名映射到节点 |
| `20_multi_target_router.py` | 路由返回序列 → 多目标并行 |
| `21_multi_path_map.py` | 多目标路由的显式 `path_map` |
| `22_defer_node.py` | `defer=True` 延迟收尾节点 |

### 第四章：动态分支（对应 `04.md`）

| 文件 | 内容 |
|------|------|
| `23_send_fanout.py` | `Send` 动态扇出：多任务并行 + 私有状态 |
| `24_command_goto.py` | `Command(goto=...)` 节点内运行时路由 |

### 第五章：扇入与 MapReduce（对应 `05.md`）

| 文件 | 内容 |
|------|------|
| `25_and_fanin.py` | “与”触发：`add_edge([上游...], 下游)` 等待全部分支 |
| `26_or_fanin.py` | “或”触发：多条独立边，任一上游到达即可触发 |
| `27_mapreduce.py` | `Send` 动态扇出 + reducer 归约（单词计数） |

### 第六章：工具调用与递归控制（对应 `06.md`）

| 文件 | 内容 |
|------|------|
| `28_tool_agent.py` | 工具绑定、`Command` 路由、工具失败重试 |
| `29_langgraph_step.py` | 线性图读取 `langgraph_step` |
| `30_remaining_steps.py` | `RemainingSteps` 在上限前主动结束循环 |
| `31_recursion_error.py` | 图外捕获 `GraphRecursionError` |

### 第七章：边（对应 `07.md`）

| 文件 | 内容 |
|------|------|
| `32_normal_edge.py` | 普通边：固定进入下一个节点 |
| `33_parallel_edges.py` | 多条普通出边：目标节点全部并行激活 |
| `34_conditional_edge.py` | 条件边：路由函数选择一个后续节点 |
| `35_multi_target_edge.py` | 条件边返回节点列表，多目标并行 |
| `36_entry_point.py` | `set_entry_point` 固定入口 |
| `37_conditional_entry.py` | 从 `START` 按状态选择入口 |
| `38_command_route.py` | `Command` 同时更新状态并跳转 |
| `39_finish_point.py` | `set_finish_point` 固定终止 |
| `40_conditional_finish.py` | 路由返回 `END` 或继续执行 |
| `41_order_flow.py` | 订单图：条件入口 + 普通边 + 条件终止 |

## 运行

```bash
# 第一章
python 01_first_graph.py
python 02_mermaid_viz.py
python 03_png_export.py
python 04_explicit_naming.py
python 05_dataclass_state.py
python 06_pydantic_state.py

# 第二章
python 07_add_messages.py
python 08_default_overwrite.py
python 09_node_receives_state.py
python 10_partial_update.py
python 11_overwrite_reducer.py
python 12_input_output_schema.py
python 13_messages_state.py   # 需要 DEEPSEEK_API_KEY

# 第三章
python 14_add_edge.py
python 15_add_sequence.py
python 16_omit_end.py
python 17_static_fanout.py        # 需要 DEEPSEEK_API_KEY
python 18_conditional_edges.py    # 需要 DEEPSEEK_API_KEY
python 19_path_map.py             # 需要 DEEPSEEK_API_KEY
python 20_multi_target_router.py  # 需要 DEEPSEEK_API_KEY
python 21_multi_path_map.py       # 需要 DEEPSEEK_API_KEY
python 22_defer_node.py           # 需要 DEEPSEEK_API_KEY

# 第四章
python 23_send_fanout.py          # 需要 DEEPSEEK_API_KEY
python 24_command_goto.py         # 需要 DEEPSEEK_API_KEY

# 第五章
python 25_and_fanin.py
python 26_or_fanin.py
python 27_mapreduce.py

# 第六章
python 28_tool_agent.py          # 需要 DEEPSEEK_API_KEY
python 29_langgraph_step.py
python 30_remaining_steps.py
python 31_recursion_error.py

# 第七章
python 32_normal_edge.py
python 33_parallel_edges.py
python 34_conditional_edge.py
python 35_multi_target_edge.py
python 36_entry_point.py
python 37_conditional_entry.py
python 38_command_route.py
python 39_finish_point.py
python 40_conditional_finish.py
python 41_order_flow.py
```

## 核心概念

构建 LangGraph 应用固定为五步：

1. 定义状态 Schema（TypedDict / dataclass / Pydantic）
2. 定义节点函数
3. 创建 `StateGraph`，添加节点与边
4. `compile()` 得到可执行图
5. `invoke()` 运行

状态字段可用归约器控制合并方式，例如：

```python
logs: Annotated[list[str], add]  # 追加，而非覆盖
messages: Annotated[list, add_messages]  # 按 id 合并消息
```

控制流常用 API：

```python
builder.add_edge(A, B)                       # 固定边
builder.set_entry_point(A)                   # 等价于 add_edge(START, A)
builder.set_finish_point(A)                  # 等价于 add_edge(A, END)
builder.add_edge([A, B], C)                  # “与”扇入：A、B 都完成后才到 C
builder.add_sequence([A, B, C])              # 批量顺序连接
builder.add_conditional_edges(src, router)   # 条件路由
builder.add_node("audit", fn, defer=True)    # 延迟收尾
Send("worker", private_state)                # 动态扇出任务
return Command(goto="next", update={...})    # 节点内跳转（可同时更新状态）
graph.invoke({}, config={"recursion_limit": 10})  # 单次调用的执行步上限
remaining_steps: RemainingSteps               # 框架注入的剩余步数
```

## 状态定义怎么选

| 方式 | 适用场景 |
|------|----------|
| TypedDict | 学习 / 快速原型 |
| dataclass | 简单脚本，需要默认值 |
| Pydantic | 生产环境（类型校验 + 序列化） |
| MessagesState | LLM 对话（内置 messages + add_messages） |
