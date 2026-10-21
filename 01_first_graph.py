"""第一个 LangGraph 程序：掌握五步构建流程，理解状态在节点之间如何流转。

流程图：START → node_1 → node_2 → END
"""

from typing import TypedDict, Annotated
from operator import add
from langgraph.graph import StateGraph, START, END


# ========== 第 1 步：定义状态 ==========
class OverAllState(TypedDict):
    """
    使用 TypedDict 定义状态 Schema。
    - logs: 使用 Annotated[list[str], add] 声明为"追加"模式
            每次节点返回的 logs 列表会与原列表拼接，而不是覆盖
    - cur_id: 普通字符串字段，节点返回时会直接覆盖原值
    """
    logs: Annotated[list[str], add]
    cur_id: str


# ========== 第 2 步：定义节点 ==========
def node_1(state: OverAllState) -> OverAllState:
    """
    节点 1：从状态中读取 cur_id，追加自己的标记后返回。
    - 读取: state["cur_id"]（TypedDict 使用字典语法访问）
    - 返回: 增量更新字典
      - logs 会被追加（归约器 add 生效）
      - cur_id 会被覆盖为新值
    """
    pre_id = state["cur_id"]
    return {
        "logs": ["node_1 运行完毕"],
        "cur_id": pre_id + ", node_1"
    }


def node_2(state: OverAllState) -> OverAllState:
    """
    节点 2：逻辑同 node_1，在 cur_id 后追加 ", node_2"。
    """
    pre_id = state["cur_id"]
    return {
        "logs": ["node_2 运行完毕"],
        "cur_id": pre_id + ", node_2"
    }


# ========== 第 3 步：构建图 ==========
# 3.1 创建 StateGraph 建造者，传入状态 Schema
builder = StateGraph(OverAllState)

# 3.2 添加节点（直接传函数，节点名默认使用函数名）
builder.add_node(node_1)
builder.add_node(node_2)

# 3.3 添加边，定义执行顺序
builder.add_edge(START, "node_1")      # 入口 → node_1
builder.add_edge("node_1", "node_2")   # node_1 → node_2
builder.add_edge("node_2", END)        # node_2 → 出口

# ========== 第 4 步：编译图 ==========
graph = builder.compile()

# ========== 第 5 步：运行图 ==========
if __name__ == "__main__":
    result = graph.invoke({"cur_id": "start"})
    print(result)
    # 预期输出:
    # {'logs': ['node_1 运行完毕', 'node_2 运行完毕'], 'cur_id': 'start, node_1, node_2'}
