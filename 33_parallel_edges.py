"""多条普通出边：同一节点连向多个目标时，这些目标都会被激活。

流程：
START → source_node → left_node  → END
                     → right_node → END

left_node 与 right_node 在同一个超步并行执行。这不是二选一。
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class ParallelState(TypedDict, total=False):
    source_finished: bool
    left_result: str
    right_result: str


def source_node(state: ParallelState) -> dict[str, bool]:
    return {"source_finished": True}


def left_node(state: ParallelState) -> dict[str, str]:
    return {"left_result": "左侧分支执行完成"}


def right_node(state: ParallelState) -> dict[str, str]:
    return {"right_result": "右侧分支执行完成"}


builder = StateGraph(state_schema=ParallelState)
builder.add_node("source_node", source_node)
builder.add_node("left_node", left_node)
builder.add_node("right_node", right_node)

builder.add_edge(START, "source_node")
builder.add_edge("source_node", "left_node")
builder.add_edge("source_node", "right_node")
builder.add_edge("left_node", END)
builder.add_edge("right_node", END)

graph = builder.compile()


if __name__ == "__main__":
    print(graph.invoke({}))
