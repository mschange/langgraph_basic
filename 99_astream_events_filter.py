"""astream_events 过滤：include_names 只取图根，效果等同 updates。

流程：
START → node_a → node_b → END

include_names=["LangGraph"] 后，on_chain_stream 的 chunk 与 stream_mode=["updates"] 一致。
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
    async for event in graph.astream_events(
        {"initial_state": "初始状态"},
        version="v2",
        include_names=["LangGraph"],
    ):
        if event["event"] == "on_chain_stream":
            print(event["data"]["chunk"])


if __name__ == "__main__":
    asyncio.run(main())
