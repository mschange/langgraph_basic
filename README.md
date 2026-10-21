# LangGraph Basic

LangGraph 入门示例：从第一个图程序到状态定义与可视化。

## 环境要求

- Python 3.10 – 3.12（暂不建议 3.14）
- 依赖见 `requirements.txt`

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 示例一览

| 文件 | 内容 |
|------|------|
| `01_first_graph.py` | 五步构建流程：State → Node → Edge → compile → invoke |
| `02_mermaid_viz.py` | 用 `draw_mermaid()` 导出 Mermaid 文本 |
| `03_png_export.py` | 用 `draw_mermaid_png()` 导出 PNG（需 `grandalf`） |
| `04_explicit_naming.py` | `add_node(name, func)` 显式命名注册节点 |
| `05_dataclass_state.py` | 用 `dataclass` 定义状态 |
| `06_pydantic_state.py` | 用 Pydantic `BaseModel` 定义状态（生产推荐） |

## 运行

```bash
python 01_first_graph.py
python 02_mermaid_viz.py
python 03_png_export.py
python 04_explicit_naming.py
python 05_dataclass_state.py
python 06_pydantic_state.py
```

预期结果（以 `01` 为例）：

```text
{'logs': ['node_1 运行完毕', 'node_2 运行完毕'], 'cur_id': 'start, node_1, node_2'}
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
```

## 状态定义怎么选

| 方式 | 适用场景 |
|------|----------|
| TypedDict | 学习 / 快速原型 |
| dataclass | 简单脚本，需要默认值 |
| Pydantic | 生产环境（类型校验 + 序列化） |
