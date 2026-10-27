"""条件边返回多个目标：路由函数返回节点名列表时，这些节点同时激活。

流程：START → dispatch → router 按 targets 选择
  含 left  → left_node  → END
  含 right → right_node → END

results 使用 add，两个分支写入的列表会合并。
"""

from operator import add
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class BranchState(TypedDict):
    targets: list[str]
    results: Annotated[list[str], add]


def dispatch(state: BranchState) -> None:
    return None


def router(state: BranchState) -> list[Literal["left_node", "right_node"]]:
    targets = []
    if "left" in state["targets"]:
        targets.append("left_node")
    if "right" in state["targets"]:
        targets.append("right_node")
    return targets


def left_node(state: BranchState) -> dict[str, list[str]]:
    return {"results": ["left"]}


def right_node(state: BranchState) -> dict[str, list[str]]:
    return {"results": ["right"]}


builder = StateGraph(state_schema=BranchState)
builder.add_node("dispatch", dispatch)
builder.add_node("left_node", left_node)
builder.add_node("right_node", right_node)

builder.add_edge(START, "dispatch")
builder.add_conditional_edges("dispatch", router)
builder.add_edge("left_node", END)
builder.add_edge("right_node", END)

graph = builder.compile()


if __name__ == "__main__":
    print(graph.invoke({"targets": ["left", "right"], "results": []}))
