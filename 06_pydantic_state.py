"""使用 Pydantic BaseModel 定义状态：生产环境推荐方案。"""

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from typing import Annotated
from operator import add


# ========== 第 1 步：使用 Pydantic 定义状态 ==========
class OverAllState(BaseModel):
    """
    使用 Pydantic BaseModel 定义状态。
    - Annotated[list[str], add] 归约器语义与之前完全一致
    - Field(default_factory=list) 设置默认空列表
    - Pydantic 会在运行时自动验证字段类型
    """
    logs: Annotated[list[str], add] = Field(default_factory=list)
    cur_id: str = ""


# ========== 第 2 步：定义节点 ==========
def node_1(state: OverAllState) -> dict:
    """
    注意：使用 Pydantic 时，节点函数返回 dict 而非 Pydantic 实例。
    LangGraph 会自动将 dict 合并到状态中（经过归约器处理）。
    - 读取属性仍然用 state.cur_id（点号语法）
    """
    pre_id = state.cur_id
    return {
        "logs": ["node_1 运行完毕"],
        "cur_id": pre_id + ", node_1"
    }


def node_2(state: OverAllState) -> dict:
    pre_id = state.cur_id
    return {
        "logs": ["node_2 运行完毕"],
        "cur_id": pre_id + ", node_2"
    }


# ========== 第 3 步：构建图 ==========
builder = StateGraph(OverAllState)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", END)

# ========== 第 4 步：编译图 ==========
graph = builder.compile()

# ========== 第 5 步：运行图 ==========
if __name__ == "__main__":
    result = graph.invoke({"cur_id": "start"})
    print(result)
    # 预期输出:
    # {'logs': ['node_1 运行完毕', 'node_2 运行完毕'], 'cur_id': 'start, node_1, node_2'}
