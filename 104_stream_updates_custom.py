"""多模式组合（同步）：updates + custom。

流程：
START → node_a → node_b → END

custom 播报进度，updates 消费节点增量；靠 (mode, data) 分发。
不需要模型或 API Key。
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime


class OverAllState(TypedDict):
    initial_state: str
    node_a_output: str
    node_b_output: str


def node_a(state: OverAllState, runtime: Runtime) -> OverAllState:
    runtime.stream_writer("节点 A 开始")
    return {"node_a_output": "节点A的输出"}


def node_b(state: OverAllState, runtime: Runtime) -> OverAllState:
    runtime.stream_writer("节点 B 开始")
    return {"node_b_output": "节点B的输出"}


builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)
builder.add_edge(START, "node_a")
builder.add_edge("node_a", "node_b")
builder.add_edge("node_b", END)

graph = builder.compile()


if __name__ == "__main__":
    for mode, data in graph.stream(
        {"initial_state": "初始状态"},
        stream_mode=["updates", "custom"],
    ):
        if mode == "custom":
            print(f"[进度] {data}")
        elif mode == "updates":
            print(f"[更新] {data}")
