"""流式输出 tasks（同步）：任务开始/结束各一条事件。

流程：
START → parallel_node_a_1 ─┐
      → parallel_node_a_2 ─┴→ node_b → END

开始事件含 id/name/input/triggers；结束事件含 id/name/error/result/interrupts。
用同一 id 配对。不需要模型或 API Key。
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class OverAllState(TypedDict):
    initial_state: str
    parallel_node_a_1: str
    parallel_node_a_2: str
    node_b_output: str


def parallel_node_a_1(state: OverAllState) -> OverAllState:
    return {"parallel_node_a_1": "并行节点A-1的输出"}


def parallel_node_a_2(state: OverAllState) -> OverAllState:
    return {"parallel_node_a_2": "并行节点A-2的输出"}


def node_b(state: OverAllState) -> OverAllState:
    return {"node_b_output": "节点B的输出"}


builder = StateGraph(state_schema=OverAllState)
builder.add_node("parallel_node_a_1", parallel_node_a_1)
builder.add_node("parallel_node_a_2", parallel_node_a_2)
builder.add_node("node_b", node_b)
builder.add_edge(START, "parallel_node_a_1")
builder.add_edge(START, "parallel_node_a_2")
builder.add_edge(["parallel_node_a_1", "parallel_node_a_2"], "node_b")
builder.add_edge("node_b", END)

graph = builder.compile()


if __name__ == "__main__":
    for chunk in graph.stream(
        {"initial_state": "初始状态"},
        stream_mode=["tasks"],
    ):
        print(chunk)
