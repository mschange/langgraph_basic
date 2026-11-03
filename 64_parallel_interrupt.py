"""并行中断：姓名和年龄同时暂停，再按中断 ID 一次性交回人工输入。

流程：
START → request_username → END
      → request_age      → END

两个节点在同一个超步里各自 interrupt()。恢复映射的键是中断 ID，不是字段名。
恢复后对应节点会从头再执行一次。终端里逐条 input() 只是收集反馈的方式。

InMemorySaver 只在当前进程有效。
"""

from collections.abc import Sequence
from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, Interrupt, interrupt


class ProfileState(TypedDict, total=False):
    username: str
    age: int


def request_username(state: ProfileState) -> dict[str, str]:
    """恢复时会从头执行，所以进入日志会出现两次。"""
    print("[姓名节点] 开始执行")
    username = interrupt({"field": "username", "prompt": "请输入您的姓名"})
    return {"username": username}


def request_age(state: ProfileState) -> dict[str, int]:
    """恢复时仍然必须用中断 ID 交回年龄，field 只用来选择输入校验。"""
    print("[年龄节点] 开始执行")
    age = interrupt({"field": "age", "prompt": "请输入您的年龄"})
    return {"age": age}


def build_graph() -> CompiledStateGraph:
    builder = StateGraph(state_schema=ProfileState)
    builder.add_node("request_username", request_username)
    builder.add_node("request_age", request_age)
    builder.add_edge(START, "request_username")
    builder.add_edge(START, "request_age")
    builder.add_edge("request_username", END)
    builder.add_edge("request_age", END)
    return builder.compile(checkpointer=InMemorySaver())


def collect_resume_map(pending_interrupts: Sequence[Interrupt]) -> dict[str, str | int]:
    """按中断载荷选择校验方式。非法年龄在这里重问，不把图恢复后再中断。"""
    resume_map: dict[str, str | int] = {}
    for pending in pending_interrupts:
        payload = pending.value
        prompt = payload["prompt"]
        if payload["field"] == "age":
            while True:
                raw_age = input(f"{prompt}：")
                try:
                    age = int(raw_age)
                except ValueError:
                    print("年龄必须是整数，请重新输入。")
                    continue
                if age < 0:
                    print("年龄不能为负数，请重新输入。")
                    continue
                resume_map[pending.id] = age
                break
        else:
            resume_map[pending.id] = input(f"{prompt}：")
    return resume_map


def main() -> None:
    graph = build_graph()
    config: RunnableConfig = {"configurable": {"thread_id": "parallel-profile-demo"}}

    print("\n1. 首次执行：收集两个并行节点的中断")
    interrupted_result = graph.invoke({}, config=config)
    print("首次返回：", interrupted_result)
    pending_interrupts = interrupted_result["__interrupt__"]
    for pending in pending_interrupts:
        print(f"中断 ID：{pending.id}，载荷：{pending.value}")

    paused_snapshot = graph.get_state(config)
    print("暂停时的业务状态：", paused_snapshot.values)
    print("等待恢复的节点：", paused_snapshot.next)

    resume_map = collect_resume_map(pending_interrupts)
    print("\n2. 按中断 ID 一次性提交全部人工反馈")
    print("恢复映射：", resume_map)
    resumed_result = graph.invoke(Command(resume=resume_map), config=config)
    print("恢复后的业务状态：", resumed_result)
    print(f"您好，{resumed_result['username']}，您的年龄是 {resumed_result['age']} 岁。")
    print("完成后待执行的节点：", graph.get_state(config).next)


if __name__ == "__main__":
    main()
