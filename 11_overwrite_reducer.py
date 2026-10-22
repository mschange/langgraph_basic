"""强制覆盖：Overwrite 临时绕过归约器，直接用新值覆盖旧值。

Overwrite 只影响当次更新；后续节点正常返回该字段时，仍按原 Reducer 处理。
"""

from typing import TypedDict, Annotated
from operator import add
from langgraph.graph import StateGraph, START, END
from langgraph.types import Overwrite


# ========== 第 1 步：定义状态 ==========
class OverAllState(TypedDict):
    logs: Annotated[list[str], add]  # 默认追加
    id: str


# ========== 第 2 步：定义节点 ==========
def node_a(state: OverAllState):
    # 正常返回 → logs 按 add 追加
    return {
        "logs": ["node_a"],
        "id": "node_a",
    }


def node_b(state: OverAllState):
    # Overwrite → 强制覆盖 logs，不走 add
    return {
        "logs": Overwrite(["node_b"]),
        "id": "node_b",
    }


def node_c(state: OverAllState):
    # 正常返回 → 基于覆盖后的 ["node_b"] 再追加
    return {
        "logs": ["node_c"],
        "id": "node_c",
    }


# ========== 第 3–4 步：构建并编译图 ==========
builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)
builder.add_node("node_c", node_c)
builder.add_edge(START, "node_a")
builder.add_edge("node_a", "node_b")
builder.add_edge("node_b", "node_c")
builder.add_edge("node_c", END)

graph = builder.compile()


# ========== 第 5 步：运行 ==========
if __name__ == "__main__":
    result = graph.invoke({"logs": ["START"], "id": "start"})
    print("=" * 30, "-> result <-", "=" * 30)
    print(result)
    # 预期: {'logs': ['node_b', 'node_c'], 'id': 'node_c'}
    # START、node_a 在 node_b 被 Overwrite 清空
