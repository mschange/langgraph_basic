"""Command 动态路由：节点同时更新状态并指定下一节点。

流程：START → decide
  score >= 60 → success_node → END
  否则        → failure_node → END

decide 不再另加普通边或条件边，避免和 Command 形成两条并行路径。
"""

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command


class CommandState(TypedDict, total=False):
    score: int
    route_message: str
    result: str


def decide(
    state: CommandState,
) -> Command[Literal["success_node", "failure_node"]]:
    if state["score"] >= 60:
        return Command(
            goto="success_node",
            update={"route_message": "分数达标"},
        )
    return Command(
        goto="failure_node",
        update={"route_message": "分数未达标"},
    )


def success_node(state: CommandState) -> dict[str, str]:
    return {"result": "通过"}


def failure_node(state: CommandState) -> dict[str, str]:
    return {"result": "未通过"}


builder = StateGraph(state_schema=CommandState)
builder.add_node("decide", decide)
builder.add_node("success_node", success_node)
builder.add_node("failure_node", failure_node)

builder.add_edge(START, "decide")
builder.add_edge("success_node", END)
builder.add_edge("failure_node", END)

graph = builder.compile()


if __name__ == "__main__":
    print(graph.invoke({"score": 85}))
    print(graph.invoke({"score": 40}))
