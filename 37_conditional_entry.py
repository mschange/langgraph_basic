"""条件入口点：从 START 按初始状态选择第一个业务节点。

流程：
  mode=fast → START → fast_node → END
  其他       → START → safe_node → END

等价于 add_conditional_edges(START, entry_router)。
"""

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class EntryState(TypedDict, total=False):
    mode: str
    result: str


def entry_router(state: EntryState) -> Literal["fast_node", "safe_node"]:
    if state["mode"] == "fast":
        return "fast_node"
    return "safe_node"


def fast_node(state: EntryState) -> dict[str, str]:
    return {"result": "执行快速流程"}


def safe_node(state: EntryState) -> dict[str, str]:
    return {"result": "执行完整校验流程"}


builder = StateGraph(state_schema=EntryState)
builder.add_node("fast_node", fast_node)
builder.add_node("safe_node", safe_node)

builder.add_conditional_edges(START, entry_router)
builder.add_edge("fast_node", END)
builder.add_edge("safe_node", END)

graph = builder.compile()


if __name__ == "__main__":
    print(graph.invoke({"mode": "fast"}))
    print(graph.invoke({"mode": "safe"}))
