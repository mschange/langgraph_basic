"""普通边：当前节点完成后固定进入下一个节点。

流程：START → node_a → node_b → END
trace 使用 add，节点返回的列表会追加而不是覆盖。
"""

from operator import add
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


class FlowState(TypedDict):
    trace: Annotated[list[str], add]


def node_a(state: FlowState) -> dict[str, list[str]]:
    return {"trace": ["node_a"]}


def node_b(state: FlowState) -> dict[str, list[str]]:
    return {"trace": ["node_b"]}


builder = StateGraph(state_schema=FlowState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)

builder.add_edge(START, "node_a")
builder.add_edge("node_a", "node_b")
builder.add_edge("node_b", END)

graph = builder.compile()


if __name__ == "__main__":
    print(graph.invoke({"trace": []}))
    # {'trace': ['node_a', 'node_b']}
