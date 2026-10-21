"""图的可视化：使用 draw_mermaid() 获取 Mermaid 文本描述。"""

from typing import TypedDict, Annotated
from operator import add
from langgraph.graph import StateGraph, START, END


# ========== 第 1 步：定义状态 ==========
class OverAllState(TypedDict):
    logs: Annotated[list[str], add]
    cur_id: str


# ========== 第 2 步：定义节点 ==========
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


# ========== 第 3 步：构建图 ==========
builder = StateGraph(OverAllState)
builder.add_node(node_1)
builder.add_node(node_2)
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", END)

# ========== 第 4 步：编译图 ==========
graph = builder.compile()

# ========== 第 5 步：运行图 ==========
if __name__ == "__main__":
    result = graph.invoke({"cur_id": "start"})
    print(result)

    # ========== 获取 Mermaid 文本 ==========
    # get_graph() 返回图的 Runnable 表示
    # draw_mermaid() 将图结构转为 Mermaid 语法的字符串
    raw_mermaid = graph.get_graph().draw_mermaid()
    print(raw_mermaid)
