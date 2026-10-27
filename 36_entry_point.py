"""入口点：set_entry_point 等价于 add_edge(START, 节点)，两种写法选一种。

流程：START → node_a → END
"""

from typing import TypedDict

from langgraph.graph import END, StateGraph


class EntryState(TypedDict, total=False):
    message: str


def node_a(state: EntryState) -> dict[str, str]:
    return {"message": "图从 node_a 开始执行"}


builder = StateGraph(state_schema=EntryState)
builder.add_node("node_a", node_a)
builder.set_entry_point("node_a")
builder.add_edge("node_a", END)

graph = builder.compile()


if __name__ == "__main__":
    print(graph.invoke({}))
