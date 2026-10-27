"""条件终止点：路由函数返回 END 或后续节点，决定结束还是继续。

流程：START → node_a → router
  is_finished=True  → END
  is_finished=False → node_b → END
"""

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class FinishState(TypedDict, total=False):
    is_finished: bool
    result: str


def node_a(state: FinishState) -> None:
    return None


def router(state: FinishState) -> Literal["node_b", END]:
    if state["is_finished"]:
        return END
    return "node_b"


def node_b(state: FinishState) -> dict[str, str]:
    return {"result": "继续执行 node_b 后结束"}


builder = StateGraph(state_schema=FinishState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)

builder.add_edge(START, "node_a")
builder.add_conditional_edges("node_a", router)
builder.add_edge("node_b", END)

graph = builder.compile()


if __name__ == "__main__":
    print(graph.invoke({"is_finished": True}))
    print(graph.invoke({"is_finished": False}))
