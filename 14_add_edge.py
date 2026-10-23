"""基础边连接：add_edge 在两个节点之间建立有向边，定义执行先后顺序。

流程图：START → node_a → node_b → END
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END


# ========== 定义状态 ==========
class OverAllState(TypedDict):
    username: str
    greeting: str
    output: str


# ========== 定义节点 ==========
def node_a(state: OverAllState) -> OverAllState:
    """读取 username，生成 greeting。"""
    return {
        "greeting": "Dear " + state["username"]
    }


def node_b(state: OverAllState) -> OverAllState:
    """读取 greeting，拼接最终输出。"""
    return {
        "output": state["greeting"] + "，你好！"
    }


# ========== 构建并编译图 ==========
builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)

# 用 add_edge 定义执行顺序
builder.add_edge(START, "node_a")      # 入口 → node_a
builder.add_edge("node_a", "node_b")   # node_a → node_b
builder.add_edge("node_b", END)        # node_b → 出口

graph = builder.compile()


if __name__ == "__main__":
    res = graph.invoke({"username": "小黄"})
    print(res)
    # 预期: {'username': '小黄', 'greeting': 'Dear 小黄', 'output': 'Dear 小黄，你好！'}
