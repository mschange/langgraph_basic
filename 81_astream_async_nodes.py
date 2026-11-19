"""流式输出 values + 异步节点：astream 下用 async def 模拟异步 IO。

流程：
START → node_a → node_b → END

async for mode, data in astream(...) 直接解包二元组。
节点内 await asyncio.sleep 模拟异步等待。
不需要模型或 API Key。
"""

import asyncio
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class OverAllState(TypedDict):
    initial_state: str
    node_a_output: str
    node_b_output: str


async def node_a(state: OverAllState) -> OverAllState:
    await asyncio.sleep(0.1)  # 模拟异步 IO
    return {"node_a_output": "节点A的输出"}


async def node_b(state: OverAllState) -> OverAllState:
    await asyncio.sleep(0.1)
    return {"node_b_output": "节点B的输出"}


builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)
builder.add_edge(START, "node_a")
builder.add_edge("node_a", "node_b")
builder.add_edge("node_b", END)

graph = builder.compile()


async def main() -> None:
    async for mode, data in graph.astream(
        {"initial_state": "初始状态"},
        stream_mode=["values"],
    ):
        print(f"[{mode}] {data}")


if __name__ == "__main__":
    asyncio.run(main())
