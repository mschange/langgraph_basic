"""astream_events 对照：同一张图分别用 stream(updates) 与 astream_events。

流程：
START → node_a → node_b → END

stream 产出 (mode, data)；astream_events(version="v2") 产出含 run_id 的事件字典。
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


def run_stream() -> None:
    print("========== stream(updates) ==========")
    for chunk in graph.stream(
        {"initial_state": "初始状态"},
        stream_mode=["updates"],
    ):
        print(chunk)


async def run_astream_events() -> None:
    print("========== astream_events(v2) ==========")
    async for event in graph.astream_events(
        {"initial_state": "初始状态"},
        version="v2",
    ):
        print(f"{event['event']:<18} name={event['name']}")


if __name__ == "__main__":
    run_stream()
    print()
    asyncio.run(run_astream_events())
