"""流式输出 tasks（异步）：并行节点真实并发，按耗时先后结束。

流程：
START → parallel_node_a_1 (0.2s) ─┐
      → parallel_node_a_2 (0.4s) ─┴→ node_b → END

含 result/error/interrupts 为结束事件，否则为开始事件。
不需要模型或 API Key。
"""

import asyncio
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class OverAllState(TypedDict):
    initial_state: str
    parallel_node_a_1: str
    parallel_node_a_2: str
    node_b_output: str


async def parallel_node_a_1(state: OverAllState) -> OverAllState:
    await asyncio.sleep(0.2)
    return {"parallel_node_a_1": "并行节点A-1的输出"}


async def parallel_node_a_2(state: OverAllState) -> OverAllState:
    await asyncio.sleep(0.4)
    return {"parallel_node_a_2": "并行节点A-2的输出"}


async def node_b(state: OverAllState) -> OverAllState:
    return {"node_b_output": "节点B的输出"}


builder = StateGraph(state_schema=OverAllState)
builder.add_node("parallel_node_a_1", parallel_node_a_1)
builder.add_node("parallel_node_a_2", parallel_node_a_2)
builder.add_node("node_b", node_b)
builder.add_edge(START, "parallel_node_a_1")
builder.add_edge(START, "parallel_node_a_2")
builder.add_edge(["parallel_node_a_1", "parallel_node_a_2"], "node_b")
builder.add_edge("node_b", END)

graph = builder.compile()


async def main() -> None:
    async for mode, data in graph.astream(
        {"initial_state": "初始状态"},
        stream_mode=["tasks"],
    ):
        if "result" in data or "error" in data:
            print(f"[结束] {data['name']} -> {data['result']} error={data['error']}")
        else:
            print(f"[开始] {data['name']} triggers={data['triggers']}")


if __name__ == "__main__":
    asyncio.run(main())
