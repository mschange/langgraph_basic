"""流式输出 values（同步）：每个超步结束后产出合并后的完整状态。

流程：
START → node_a → node_b → END

stream_mode=["values"] 时产出 (mode, data) 二元组。
第一次产出是输入本身；最后一次等价于 invoke 的返回值。
不需要模型或 API Key。
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class OverAllState(TypedDict):
    initial_state: str
    node_a_output: str
    node_b_output: str


def node_a(state: OverAllState) -> OverAllState:
    return {"node_a_output": "节点A的输出"}


def node_b(state: OverAllState) -> OverAllState:
    return {"node_b_output": "节点B的输出"}


builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)
builder.add_edge(START, "node_a")
builder.add_edge("node_a", "node_b")
builder.add_edge("node_b", END)

graph = builder.compile()


if __name__ == "__main__":
    for chunk in graph.stream(
        {"initial_state": "初始状态"},
        stream_mode=["values"],
    ):
        print(chunk)
