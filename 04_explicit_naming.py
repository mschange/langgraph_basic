"""节点的显式命名注册：掌握 add_node(name, func)，理解节点名与函数名解耦。"""

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from operator import add


class OverAllState(TypedDict):
    logs: Annotated[list[str], add]
    cur_id: str


def node_1(state: OverAllState) -> OverAllState:
    pre_id = state["cur_id"]
    return {
        "logs": ["node_1 运行完毕"],
        "cur_id": pre_id + ", node_1"
    }


def node_2(state: OverAllState) -> OverAllState:
    pre_id = state["cur_id"]
    return {
        "logs": ["node_2 运行完毕"],
        "cur_id": pre_id + ", node_2"
    }


# 使用 state_schema 关键字参数（等价于 StateGraph(OverAllState)）
builder = StateGraph(state_schema=OverAllState)

# 显式命名：第一个参数是节点名，第二个参数是函数
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)

builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", END)

graph = builder.compile()

if __name__ == "__main__":
    result = graph.invoke({"cur_id": "start"})
    print(result)
