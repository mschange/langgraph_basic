"""部分更新：节点只返回需要修改的字段，未返回的字段保持不变。

- 有归约器的字段：按归约器合并（如 add 追加）
- 无归约器的字段：直接覆盖
- 未返回的字段：保持原值
"""

from typing import TypedDict, Annotated
from operator import add
from langgraph.graph import StateGraph, START, END


# ========== 第 1 步：定义状态 ==========
class OverAllState(TypedDict):
    logs: Annotated[list[str], add]
    id: str


# ========== 第 2 步：定义节点 ==========
def node_a(state: OverAllState):
    """只更新 logs，不返回 id → id 保持 "start"。"""
    for k, v in state.items():
        print(f"k: {k}, v: {v}")

    return {
        "logs": ["node_a 更新状态"],
    }


# ========== 第 3–4 步：构建并编译图 ==========
builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_a", node_a)
builder.add_edge(START, "node_a")
builder.add_edge("node_a", END)

graph = builder.compile()


# ========== 第 5 步：运行 ==========
if __name__ == "__main__":
    result = graph.invoke({"logs": ["START"], "id": "start"})
    print("=" * 30, "-> result <-", "=" * 30)
    print(result)
    # 预期: {'logs': ['START', 'node_a 更新状态'], 'id': 'start'}
