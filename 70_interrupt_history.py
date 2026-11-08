"""串行中断的检查点历史：固定恢复值，观察当前快照与历史条目。

流程：
START → collect_profile → END

节点内两次 interrupt：姓名 → 年龄。
反馈固定为“小黄”和 123，运行时不需要终端输入。
每次 invoke 后打印最新快照、固定检查点视图，以及从新到旧的历史。

局部变量取得值不等于业务状态已更新；节点 return 后才写入 values。
不需要模型或 API Key。InMemorySaver 只在当前进程有效。
"""

from typing import TypedDict
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, StateSnapshot, interrupt


class ProfileState(TypedDict, total=False):
    username: str
    age: int


def collect_profile(state: ProfileState) -> ProfileState:
    print("[节点] 进入资料收集节点")
    username = interrupt("请输入您的姓名")
    print(f"[节点] 取得姓名：{username}")
    age = interrupt("请输入您的年龄")
    print(f"[节点] 取得年龄：{age}")
    return {"username": username, "age": age}


def build_graph() -> CompiledStateGraph:
    builder = StateGraph(state_schema=ProfileState)
    builder.add_node("collect_profile", collect_profile)
    builder.add_edge(START, "collect_profile")
    builder.add_edge("collect_profile", END)
    return builder.compile(checkpointer=InMemorySaver())


def print_snapshot(snapshot: StateSnapshot) -> None:
    print("  检查点 ID：", snapshot.config["configurable"]["checkpoint_id"])
    parent = snapshot.parent_config
    parent_id = parent["configurable"]["checkpoint_id"] if parent else None
    print("  父检查点 ID：", parent_id)
    print("  创建时间：", snapshot.created_at)
    print("  元信息：", snapshot.metadata)
    print("  values：", snapshot.values)
    print("  next：", snapshot.next)
    for task in snapshot.tasks:
        print("  任务：", task.name, "任务 ID：", task.id)
        print("  任务错误：", task.error)
        print("  任务结果视图：", task.result)
        for pending in task.interrupts:
            print("    中断 ID：", pending.id, "载荷：", pending.value)


def show_state_and_history(
    graph: CompiledStateGraph, config: RunnableConfig
) -> None:
    print("\n[当前快照：仅用会话 ID 读取最新视图]")
    latest = graph.get_state(config)
    print_snapshot(latest)
    print("\n[固定检查点视图：使用当前快照携带的检查点 ID]")
    print_snapshot(graph.get_state(latest.config))
    print("\n[历史快照：较新到较旧]")
    for index, snapshot in enumerate(graph.get_state_history(config), start=1):
        print(f"历史条目 {index}")
        print_snapshot(snapshot)


def main() -> None:
    graph = build_graph()
    config: RunnableConfig = {
        "configurable": {"thread_id": uuid4().hex}
    }

    print("\n=== 第一次：启动，等待姓名 ===")
    result = graph.invoke({}, config=config)
    print("本次返回：", result)
    show_state_and_history(graph, config)

    print("\n=== 第二次：恢复姓名，等待年龄 ===")
    result = graph.invoke(Command(resume="小黄"), config=config)
    print("本次返回：", result)
    show_state_and_history(graph, config)

    print("\n=== 第三次：恢复年龄，完成节点 ===")
    result = graph.invoke(Command(resume=123), config=config)
    print("本次返回：", result)
    show_state_and_history(graph, config)


if __name__ == "__main__":
    main()
