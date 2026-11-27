"""多模式组合：把 (mode, data) 转成前端统一协议 {type, payload}。

流程：
START → node_a → node_b → END

custom → type=progress；updates → type=update + node 名。
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
    runtime.stream_writer("节点 A 开始")
    return {"node_a_output": "节点A的输出"}


async def node_b(state: OverAllState, runtime: Runtime) -> OverAllState:
    runtime.stream_writer("节点 B 开始")
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
        stream_mode=["updates", "custom"],
    ):
        if mode == "custom":
            event = {"type": "progress", "payload": data}
        else:
            node_name = next(iter(data))
            event = {
                "type": "update",
                "node": node_name,
                "payload": data[node_name],
            }
        print(event)


if __name__ == "__main__":
    asyncio.run(main())
