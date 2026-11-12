"""LangGraph 开发服务器图定义：动态中断收集信息 + 静态断点确认。

流程：
START → get_info_node → confirm_node → END

get_info_node 内三次 interrupt() 按顺序收集用户名、年龄、性别。
confirm_node 仅打印完整状态，不修改字段。
compile 只设置 interrupt_before=["confirm_node"]，不传 checkpointer。

交给 langgraph dev 时，持久化由服务器提供；
若在 compile() 里自带 InMemorySaver，服务器会加载失败。
"""

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt


class OverAllState(TypedDict, total=False):
    """total=False 允许初次输入为空字典；三个字段在节点完成后才写入。"""

    username: str
    age: int
    gender: Literal["male", "female"]


def get_info_node(state: OverAllState) -> OverAllState:
    """同一个节点内按代码顺序发起三次动态中断。"""
    # 每次 interrupt() 都把问题交给调用方，并暂停这个节点。
    username = interrupt("请输入您的用户名：")
    print(f"[get_info_node] 已取得用户名：{username!r}")

    age = interrupt("请输入您的年龄：")
    print(f"[get_info_node] 已取得年龄：{age!r}")

    gender = interrupt("请输入您的性别：(male/female)")
    print(f"[get_info_node] 已取得性别：{gender!r}")

    # 只有三个问题都回答完，节点才返回状态更新。
    return {"username": username, "age": age, "gender": gender}


def confirm_node(state: OverAllState) -> OverAllState:
    """用于演示静态断点：这个节点在被暂停时还没有执行过。"""
    print(f"[confirm_node] 收到完整状态：{state}")
    # 返回空字典表示本节点不修改任何字段，不是把状态清空。
    return {}


builder = StateGraph(state_schema=OverAllState)
builder.add_node("get_info_node", get_info_node)
builder.add_node("confirm_node", confirm_node)
builder.add_edge(START, "get_info_node")
builder.add_edge("get_info_node", "confirm_node")
builder.add_edge("confirm_node", END)

# 关键：交给开发服务器运行时，compile() 不要传 checkpointer。
# 持久化由服务器提供；这里只设置静态断点，在 confirm_node 执行前暂停。
graph = builder.compile(interrupt_before=["confirm_node"])
