"""流式输出 debug（同步）：checkpoint / task / task_result 统一事件流。

流程：
START → parallel_node_a_1 ─┐
      → parallel_node_a_2 ─┴→ node_b (interrupt) → END

需要 checkpointer + thread_id。中断签名：error=None + result={} + interrupts 非空。
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

graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "123"}}


def show(mode: str, event: dict) -> None:
    payload = event["payload"]
    if event["type"] == "checkpoint":
        print(f"[step={event['step']}] checkpoint next={payload['next']}")
    elif event["type"] == "task_result" and payload.get("interrupts"):
        print(
            f"[step={event['step']}] task_result  name={payload['name']}"
            f" interrupts={payload['interrupts'][0]['value']!r}"
        )
    else:
        print(f"[step={event['step']}] {event['type']:<12} name={payload['name']}")


if __name__ == "__main__":
    print("========== 第一次执行（会停在中途） ==========")
    for mode, event in graph.stream(
        {"initial_state": "初始状态"},
        stream_mode=["debug"],
        config=config,
    ):
        show(mode, event)

    print("========== 恢复执行 ==========")
    for mode, event in graph.stream(
        Command(resume=""),
        stream_mode=["debug"],
        config=config,
    ):
        show(mode, event)
