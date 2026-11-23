"""流式输出 checkpoints（同步）：中断后用 Command(resume=...) 恢复。

流程：
START → parallel_node_a_1 ─┐
      → parallel_node_a_2 ─┴→ node_b (interrupt) → END

需要 checkpointer + thread_id。首次跑到 node_b 暂停，再 resume 跑完。
不需要模型或 API Key。
"""

from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class OverAllState(TypedDict):
    initial_state: str
    parallel_node_a_1: str
    parallel_node_a_2: str
    node_b_output: str


def parallel_node_a_1(state: OverAllState) -> OverAllState:
    return {"parallel_node_a_1": "并行节点A-1的输出"}


def parallel_node_a_2(state: OverAllState) -> OverAllState:
    return {"parallel_node_a_2": "并行节点A-2的输出"}


def node_b(state: OverAllState) -> OverAllState:
    interrupt("hello")
    return {"node_b_output": "节点B的输出"}


builder = StateGraph(state_schema=OverAllState)
builder.add_node("parallel_node_a_1", parallel_node_a_1)
builder.add_node("parallel_node_a_2", parallel_node_a_2)
builder.add_node("node_b", node_b)
builder.add_edge(START, "parallel_node_a_1")
builder.add_edge(START, "parallel_node_a_2")
builder.add_edge(["parallel_node_a_1", "parallel_node_a_2"], "node_b")
builder.add_edge("node_b", END)

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
config = {"configurable": {"thread_id": "123"}}


if __name__ == "__main__":
    print("========== 第一次执行（会停在中途） ==========")
    for mode, snapshot in graph.stream(
        {"initial_state": "初始状态"},
        stream_mode=["checkpoints"],
        config=config,
    ):
        print(
            f"step={snapshot['metadata']['step']:<3}"
            f"source={snapshot['metadata']['source']:<6}"
            f"next={snapshot['next']}"
        )
        for task in snapshot["tasks"]:
            if task["interrupts"]:
                print("中断内容:", task["interrupts"][0]["value"])
                print("中断 ID:", task["interrupts"][0]["id"])

    print("========== 恢复执行 ==========")
    for mode, snapshot in graph.stream(
        Command(resume=""),
        stream_mode=["checkpoints"],
        config=config,
    ):
        print(
            f"step={snapshot['metadata']['step']:<3}"
            f"source={snapshot['metadata']['source']:<6}"
            f"next={snapshot['next']}"
        )
        for task in snapshot["tasks"]:
            if task["interrupts"]:
                print("中断内容:", task["interrupts"][0]["value"])
                print("中断 ID:", task["interrupts"][0]["id"])

    snapshot = graph.get_state(config)
    print("最终 next:", snapshot.next)
    print("最终 node_b_output:", snapshot.values.get("node_b_output"))
