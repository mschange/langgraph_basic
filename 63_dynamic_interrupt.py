"""动态中断：节点用 interrupt() 暂停，调用方再用 Command(resume=...) 交回姓名。

流程：START → request_username → END
首次调用在 interrupt() 处返回 __interrupt__，业务状态仍是空的。
恢复时节点会从头再执行一次，interrupt() 才拿到输入并写入 username。

input() 在调用方，不在节点里。InMemorySaver 只在当前进程有效。
"""

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt
from typing import TypedDict


class UsernameState(TypedDict):
    username: str


def request_username(state: UsernameState) -> dict[str, str]:
    """恢复时会从头执行，所以进入日志会出现两次。"""
    print("[节点] 进入姓名输入节点")
    username = interrupt("请输入您的姓名")
    return {"username": username}


def build_graph() -> CompiledStateGraph:
    builder = StateGraph(state_schema=UsernameState)
    builder.add_node("request_username", request_username)
    builder.add_edge(START, "request_username")
    builder.add_edge("request_username", END)
    return builder.compile(checkpointer=InMemorySaver())


def main() -> None:
    graph = build_graph()
    config: RunnableConfig = {"configurable": {"thread_id": "username-demo"}}

    print("\n1. 首次调用：执行到 interrupt() 后暂停")
    interrupted_result = graph.invoke({}, config=config)
    print("首次返回：", interrupted_result)

    pending_interrupt = interrupted_result["__interrupt__"][0]
    prompt = pending_interrupt.value
    print("中断提示：", prompt)

    paused_snapshot = graph.get_state(config)
    print("暂停时的状态：", paused_snapshot.values)
    print("等待恢复的节点：", paused_snapshot.next)

    username = input(f"{prompt}：")

    print("\n2. 恢复调用：把人工输入交给 interrupt()")
    resumed_result = graph.invoke(Command(resume=username), config=config)
    print("恢复后的状态：", resumed_result)
    print(f"您好，{resumed_result['username']}！")

    completed_snapshot = graph.get_state(config)
    print("完成后待执行的节点：", completed_snapshot.next)


if __name__ == "__main__":
    main()
