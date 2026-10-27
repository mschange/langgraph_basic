"""条件边：节点完成后由路由函数按状态选择一个后续节点。

流程：START → evaluate → router
  score >= 60 → passed_node → END
  否则        → failed_node → END

路由函数只选择路径，不更新状态。
"""

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class RouteState(TypedDict, total=False):
    score: int
    result: str


def evaluate(state: RouteState) -> None:
    return None


def router(state: RouteState) -> Literal["passed_node", "failed_node"]:
    if state["score"] >= 60:
        return "passed_node"
    return "failed_node"


def passed_node(state: RouteState) -> dict[str, str]:
    return {"result": "通过"}


def failed_node(state: RouteState) -> dict[str, str]:
    return {"result": "未通过"}


builder = StateGraph(state_schema=RouteState)
builder.add_node("evaluate", evaluate)
builder.add_node("passed_node", passed_node)
builder.add_node("failed_node", failed_node)

builder.add_edge(START, "evaluate")
builder.add_conditional_edges("evaluate", router)
builder.add_edge("passed_node", END)
builder.add_edge("failed_node", END)

graph = builder.compile()


if __name__ == "__main__":
    print(graph.invoke({"score": 80}))
    print(graph.invoke({"score": 50}))
