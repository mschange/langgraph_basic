"""astream_events 实战：同一次循环处理模型 token 与工具事件。

流程：
START → agent_node ─┬─(有 tool_calls)→ tool_node → agent_node ...
                    └─(无 tool_calls)→ END

on_chat_model_stream 打字；on_tool_start / on_tool_end 打印工具入参与输出。
前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

import asyncio
from typing import TypedDict

from dotenv import load_dotenv
from langchain.messages import HumanMessage, ToolMessage
from langchain.tools import tool
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)


@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气"""
    return f"{city} 今天天气不错"


model_with_tools = model.bind_tools([get_weather])


class AgentState(TypedDict):
    messages: list


async def agent_node(state: AgentState) -> AgentState:
    response = await model_with_tools.ainvoke(state["messages"])
    return {"messages": state["messages"] + [response]}


async def tool_node(state: AgentState) -> AgentState:
    last = state["messages"][-1]
    results = []
    for call in last.tool_calls:
        result = get_weather.invoke(call["args"])
        results.append(
            ToolMessage(tool_call_id=call["id"], content=result)
        )
    return {"messages": state["messages"] + results}


def should_continue(state: AgentState) -> str:
    return "tool_node" if getattr(state["messages"][-1], "tool_calls", None) else END


builder = StateGraph(state_schema=AgentState)
builder.add_node("agent_node", agent_node)
builder.add_node("tool_node", tool_node)
builder.add_edge(START, "agent_node")
builder.add_conditional_edges("agent_node", should_continue)
builder.add_edge("tool_node", "agent_node")

graph = builder.compile()


async def main() -> None:
    async for event in graph.astream_events(
        {"messages": [HumanMessage(content="北京今天天气怎么样？")]},
        version="v2",
    ):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                print(content, end="", flush=True)
        elif kind == "on_tool_start":
            print(f"\n[工具开始] {event['name']} 入参={event['data'].get('input')}")
        elif kind == "on_tool_end":
            print(f"[工具结束] {event['name']} 输出={event['data'].get('output')}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
