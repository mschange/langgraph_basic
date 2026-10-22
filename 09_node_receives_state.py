"""节点如何接收状态：第一个参数是当前全局状态快照。

注意：state 是快照，节点内直接改 state 不会影响图状态，必须通过返回值更新。
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
    """打印 invoke 传入的初始状态快照中的所有字段。"""
    for k, v in state.items():
        print(f"k: {k}, v: {v}")


# ========== 第 3–4 步：构建并编译图 ==========
builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_a", node_a)
builder.add_edge(START, "node_a")
builder.add_edge("node_a", END)

graph = builder.compile()


# ========== 第 5 步：运行 ==========
if __name__ == "__main__":
    result = graph.invoke({"logs": ["START"], "id": "start"})
    # 预期输出:
    # k: logs, v: ['START']
    # k: id, v: start
    print("=" * 30, "-> result <-", "=" * 30)
    print(result)
