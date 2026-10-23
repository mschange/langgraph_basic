"""END 可省略，START 不能省略。

最后一个节点执行完后若无后续节点被触发，图会自然结束；
没有 START 边，运行时不知道入口，会报错。
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START


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
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)

builder.add_edge(START, "node_a")      # START 不能省略
builder.add_edge("node_a", "node_b")
# 注意：没有 add_edge("node_b", END)
# node_b 执行完后没有后续节点被触发，图自然结束

graph = builder.compile()


if __name__ == "__main__":
    res = graph.invoke({"username": "小黄"})
    print(res)
    # 预期: {'username': '小黄', 'greeting': 'Dear 小黄', 'output': 'Dear 小黄，你好！'}
