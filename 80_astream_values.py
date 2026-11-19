"""流式输出 values（异步）：astream 与 stream 的产出结构相同。

流程：
START → node_a → node_b → END

async for 消费 astream；chunk 仍是 (mode, data)。
图与节点可为同步；高并发场景建议节点也写成 async def。
不需要模型或 API Key。
"""

import asyncio
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class OverAllState(TypedDict):
    initial_state: str
    node_a_output: str
    node_b_output: str


def node_a(state: OverAllState) -> OverAllState:
    return {"node_a_output": "节点A的输出"}


def node_b(state: OverAllState) -> OverAllState:
    return {"node_b_output": "节点B的输出"}


builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)
builder.add_edge(START, "node_a")
builder.add_edge("node_a", "node_b")
builder.add_edge("node_b", END)

graph = builder.compile()


async def main() -> None:
    async for chunk in graph.astream(
        {"initial_state": "初始状态"},
        stream_mode=["values"],
    ):
        print(chunk)


if __name__ == "__main__":
    asyncio.run(main())
