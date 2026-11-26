"""流式输出 custom（异步）：stream_writer 写字典，适合进度条。

流程：
START → node_a → node_b → END

stream_writer 本身是同步方法，async 节点里直接调用即可。
不需要模型或 API Key。
"""

import asyncio
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime


class OverAllState(TypedDict):
    initial_state: str
    node_a_output: str
    node_b_output: str


async def node_a(state: OverAllState, runtime: Runtime) -> OverAllState:
    runtime.stream_writer({"stage": "A", "status": "running"})
    await asyncio.sleep(0.1)
    runtime.stream_writer({"stage": "A", "status": "done"})
    return {"node_a_output": "节点A的输出"}


async def node_b(state: OverAllState, runtime: Runtime) -> OverAllState:
    runtime.stream_writer({"stage": "B", "status": "running"})
    await asyncio.sleep(0.1)
    runtime.stream_writer({"stage": "B", "status": "done"})
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
        stream_mode=["custom"],
    ):
        print(f"[{data['stage']}] {data['status']}")


if __name__ == "__main__":
    asyncio.run(main())
