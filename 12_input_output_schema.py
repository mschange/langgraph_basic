"""输入输出 Schema 隔离：input_schema / output_schema 保护内部状态。

- InputState：invoke() 接收的参数
- OutputState：invoke() 返回的结果
- OverAllState：图内部完整状态
- PrivateState：仅节点间传递的中间数据，外部不可见
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END


# ========== 定义四种状态类型 ==========
class InputState(TypedDict):
    username: str


class OutputState(TypedDict):
    graph_output: str


class OverAllState(TypedDict):
    nickname: str
    username: str
    graph_output: str


class PrivateState(TypedDict):
    greeting: str


# ========== 定义节点 ==========
def node_1(state: InputState) -> OverAllState:
    """读取 username，写入 nickname。"""
    return {
        "nickname": "Dear " + state["username"],
    }


def node_2(state: OverAllState) -> PrivateState:
    """读取 nickname，写入私有中间字段 greeting。"""
    return {
        "greeting": state["nickname"] + ", 早上好~",
    }


def node_3(state: PrivateState) -> OutputState:
    """读取 greeting，写入最终输出 graph_output。"""
    return {
        "graph_output": state["greeting"] + " 很高兴认识你！",
    }


# ========== 构建图：同时指定 input_schema 与 output_schema ==========
builder = StateGraph(
    OverAllState,
    input_schema=InputState,
    output_schema=OutputState,
)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", "node_3")
builder.add_edge("node_3", END)

graph = builder.compile()


if __name__ == "__main__":
    result = graph.invoke({"username": "小黄"})
    print(result)
    # 预期: {'graph_output': 'Dear 小黄, 早上好~ 很高兴认识你！'}
    # nickname、greeting 不会出现在返回值中
