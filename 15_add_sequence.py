"""批量顺序连接：add_sequence 自动注册节点并在相邻节点之间连边。

等价于：
  add_node("node_a", node_a)
  add_node("node_b", node_b)
  add_edge("node_a", "node_b")
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
    return {
        "greeting": "Dear " + state["username"]
    }


def node_b(state: OverAllState) -> OverAllState:
    return {
        "output": state["greeting"] + "，你好！"
    }


# ========== 构建并编译图 ==========
builder = StateGraph(state_schema=OverAllState)

builder.add_edge(START, "node_a")
# 自动注册 node_a、node_b，并在它们之间添加边（默认用函数名作节点名）
builder.add_sequence([node_a, node_b])
builder.add_edge("node_b", END)

graph = builder.compile()


if __name__ == "__main__":
    res = graph.invoke({"username": "小黄"})
    print(res)
    # 预期: {'username': '小黄', 'greeting': 'Dear 小黄', 'output': 'Dear 小黄，你好！'}
