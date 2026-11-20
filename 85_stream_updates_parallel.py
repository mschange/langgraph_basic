"""流式输出 updates（并行）：每个并行节点各产出一条增量。

流程：
START → parallel_node_a_1 ─┐
      → parallel_node_a_2 ─┴→ node_b → END

与 values 不同：并行分支分别产出，顺序不保证固定。
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
        stream_mode=["updates"],
    ):
        print(chunk)
