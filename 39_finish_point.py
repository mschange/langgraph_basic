"""终止点：set_finish_point 等价于 add_edge(节点, END)，两种写法选一种。

流程：START → node_a → END
"""

from typing import TypedDict

from langgraph.graph import StateGraph


class FinishState(TypedDict, total=False):
    result: str


def node_a(state: FinishState) -> dict[str, str]:
    return {"result": "处理完成"}


builder = StateGraph(state_schema=FinishState)
builder.add_node("node_a", node_a)
builder.set_entry_point("node_a")
builder.set_finish_point("node_a")

graph = builder.compile()


if __name__ == "__main__":
    print(graph.invoke({}))
