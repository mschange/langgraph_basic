"""流式输出 messages（多节点）：用 metadata.langgraph_node 区分来源。

流程：
START → writer_node → reviewer_node → END

按节点缓冲拼接 token，适合前端分区展示。
前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

import asyncio
from typing import TypedDict

from dotenv import load_dotenv
from langchain.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)


class WriterState(TypedDict):
    topic: str
    draft: str
    review: str


async def writer_node(state: WriterState) -> WriterState:
    msg = await model.ainvoke([
        SystemMessage("你是文案，用一句话介绍主题。"),
        HumanMessage(state["topic"]),
    ])
    return {"draft": msg.content}


async def reviewer_node(state: WriterState) -> WriterState:
    msg = await model.ainvoke([
        SystemMessage("你是审核员，用一句话评价这段文案。"),
        HumanMessage(state["draft"]),
    ])
    return {"review": msg.content}


builder = StateGraph(state_schema=WriterState)
builder.add_node("writer_node", writer_node)
builder.add_node("reviewer_node", reviewer_node)
builder.add_edge(START, "writer_node")
builder.add_edge("writer_node", "reviewer_node")
builder.add_edge("reviewer_node", END)

graph = builder.compile()


async def main() -> None:
    buffers: dict[str, list[str]] = {}
    async for mode, data in graph.astream(
        {"topic": "LangGraph"},
        stream_mode=["messages"],
    ):
        chunk, metadata = data
        if not chunk.content:
            continue
        node = metadata["langgraph_node"]
        buffers.setdefault(node, [])
        buffers[node].append(chunk.content)

    for node, parts in buffers.items():
        print(f"== {node} ==\n{''.join(parts)}\n")


if __name__ == "__main__":
    asyncio.run(main())
