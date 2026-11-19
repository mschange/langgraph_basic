"""流式输出 values（并行）：同一超步内并行节点只产出一次合并状态。

流程：
START → parallel_node_a_1 ─┐
      → parallel_node_a_2 ─┴→ node_b → END

values 按超步产出；两个并行节点的结果出现在同一次 chunk 中。
这是 values 与 updates（并行时分别产出）的主要区别。
不需要模型或 API Key。
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
        stream_mode=["values"],
    ):
        print(chunk)
