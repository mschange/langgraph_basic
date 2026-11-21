"""流式输出 messages（异步）：打字机效果打印 token。

流程：
START → llm_node → END

async def + await model.ainvoke；只打印非空 content。
metadata["langgraph_node"] 标明 token 来源节点。
前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

import asyncio

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, MessagesState, StateGraph

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)


async def llm_node(state: MessagesState) -> MessagesState:
    response = await model.ainvoke(state["messages"])
    return {"messages": [response]}


builder = StateGraph(state_schema=MessagesState)
builder.add_node("llm_node", llm_node)
builder.add_edge(START, "llm_node")
builder.add_edge("llm_node", END)

graph = builder.compile()


async def main() -> None:
    async for mode, data in graph.astream(
        {"messages": [HumanMessage(content="你好!")]},
        stream_mode=["messages"],
    ):
        chunk, metadata = data
        if chunk.content:
            print(chunk.content, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
