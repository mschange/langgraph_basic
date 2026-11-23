"""流式输出 checkpoints（异步）：打印 step / next / interrupts。

流程：
START → parallel_node_a_1 ─┐
      → parallel_node_a_2 ─┴→ node_b (interrupt) → END

恢复时会先重放中断点快照（interrupts 非空），再跑到 next=[]。
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


def show(snapshot: dict) -> None:
    interrupts = [
        i["value"]
        for task in snapshot["tasks"]
        for i in task["interrupts"]
    ]
    print(
        f"step={snapshot['metadata']['step']:<3}"
        f"next={snapshot['next']!s:<45}"
        f"interrupts={interrupts}"
    )


async def main() -> None:
    print("========== 第一次执行（会停在中途） ==========")
    async for mode, snapshot in graph.astream(
        {"initial_state": "初始状态"},
        stream_mode=["checkpoints"],
        config=config,
    ):
        show(snapshot)

    print("========== 恢复执行 ==========")
    async for mode, snapshot in graph.astream(
        Command(resume=""),
        stream_mode=["checkpoints"],
        config=config,
    ):
        show(snapshot)


if __name__ == "__main__":
    asyncio.run(main())
