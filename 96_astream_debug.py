"""流式输出 debug（异步）：task_result 标注完成 / 中断 / 失败。

流程：
START → parallel_node_a_1 ─┐
      → parallel_node_a_2 ─┴→ node_b (interrupt) → END

恢复后 node_b 的 task_result 从「中断」变为「完成」。
不需要模型或 API Key。
"""

import asyncio
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class OverAllState(TypedDict):
    initial_state: str
    parallel_node_a_1: str
    parallel_node_a_2: str
    node_b_output: str


async def parallel_node_a_1(state: OverAllState) -> OverAllState:
    return {"parallel_node_a_1": "并行节点A-1的输出"}


async def parallel_node_a_2(state: OverAllState) -> OverAllState:
    return {"parallel_node_a_2": "并行节点A-2的输出"}


async def node_b(state: OverAllState) -> OverAllState:
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


def show(event: dict) -> None:
    payload = event["payload"]
    if event["type"] == "checkpoint":
        print(f"[step={event['step']}] checkpoint next={payload['next']}")
    elif event["type"] == "task_result":
        if payload["interrupts"]:
            status = "中断"
        elif payload["error"]:
            status = "失败"
        else:
            status = "完成"
        print(f"[step={event['step']}] task_result {payload['name']} -> {status}")
    else:
        print(f"[step={event['step']}] {event['type']:<11} {payload['name']}")


async def main() -> None:
    print("========== 第一次执行（会停在中途） ==========")
    async for mode, event in graph.astream(
        {"initial_state": "初始状态"},
        stream_mode=["debug"],
        config=config,
    ):
        show(event)

    print("========== 恢复执行 ==========")
    async for mode, event in graph.astream(
        Command(resume=""),
        stream_mode=["debug"],
        config=config,
    ):
        show(event)


if __name__ == "__main__":
    asyncio.run(main())
