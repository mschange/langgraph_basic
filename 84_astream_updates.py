"""流式输出 updates（异步）：astream 产出结构与同步相同。

流程：
START → node_a → node_b → END

data 形态为 {节点名: 增量}，用 next(iter(data)) 取节点名。
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
    async for mode, data in graph.astream(
        {"initial_state": "初始状态"},
        stream_mode=["updates"],
    ):
        node_name = next(iter(data))
        print(f"[{mode}] 节点 {node_name} 更新：{data[node_name]}")


if __name__ == "__main__":
    asyncio.run(main())
