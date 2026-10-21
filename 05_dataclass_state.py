"""使用 dataclass 定义状态：用标准库 dataclass 替代 TypedDict。"""

from langgraph.graph import StateGraph, START, END
from dataclasses import dataclass, field
from typing import Annotated
from operator import add


# ========== 第 1 步：使用 dataclass 定义状态 ==========
@dataclass
class OverAllState:
    """
    使用 dataclass 定义状态。
    - logs: Annotated[list[str], add] 仍然实现追加语义
    - field(default_factory=list) 确保默认值是新的空列表
    - cur_id 默认为空字符串，invoke 时传入的值会覆盖它
    """
    logs: Annotated[list[str], add] = field(default_factory=list)
    cur_id: str = ""


# ========== 第 2 步：定义节点 ==========
def node_1(state: OverAllState) -> OverAllState:
    """
    注意与 TypedDict 版本的区别：
    - 读取属性用 state.cur_id（点号），而非 state["cur_id"]
    - 返回的是 OverAllState 实例，而非字典
    """
    pre_id = state.cur_id
    return OverAllState(
        logs=["node_1 运行完毕"],
        cur_id=pre_id + ", node_1"
    )


def node_2(state: OverAllState) -> OverAllState:
    pre_id = state.cur_id
    return OverAllState(
        logs=["node_2 运行完毕"],
        cur_id=pre_id + ", node_2"
    )


# ========== 第 3 步：构建图 ==========
builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", END)

# ========== 第 4 步：编译图 ==========
graph = builder.compile()

# ========== 第 5 步：运行图 ==========
if __name__ == "__main__":
    # 注意：invoke 仍然传入字典，LangGraph 会自动映射到 dataclass 字段
    result = graph.invoke({"cur_id": "start"})
    print(result)
    # 预期输出:
    # OverAllState(logs=['node_1 运行完毕', 'node_2 运行完毕'], cur_id='start, node_1, node_2')
