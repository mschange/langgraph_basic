"""无归约器时的默认覆盖行为：后一次更新直接替换字段原值。

对比：若使用 Annotated[list[str], add]，logs 会追加而非覆盖。
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END


# ========== 第 1 步：定义状态（无归约器 → 覆盖模式）==========
class OverAllState(TypedDict):
    logs: list[str]
    id: str


# ========== 第 2 步：定义节点 ==========
def node_a(state: OverAllState):
    return {
        "logs": ["node_a"],
        "id": "node_a",
    }


def node_b(state: OverAllState):
    return {
        "logs": ["node_b"],
        "id": "node_b",
    }


# ========== 第 3–4 步：构建并编译图 ==========
builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)
builder.add_edge(START, "node_a")
builder.add_edge("node_a", "node_b")
builder.add_edge("node_b", END)

graph = builder.compile()


# ========== 第 5 步：运行 ==========
if __name__ == "__main__":
    result = graph.invoke({"logs": ["START"], "id": "start"})
    print("=" * 30, "-> result <-", "=" * 30)
    print(result)
    # 预期: {'logs': ['node_b'], 'id': 'node_b'}
    # "START" 和 "node_a" 均被覆盖丢失
