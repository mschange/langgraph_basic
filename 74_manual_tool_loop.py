"""手写工具调用循环（ReAct）：llm_node 与 tool_node 条件回环。

流程：
START → llm_node ⇄ tool_node → END

有 tool_calls 时进入 tool_node，执行白名单内工具并写回 ToolMessage。
无 tool_calls 时路由到 END。tool_call_id 必须原样带回。

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from typing import Literal

from dotenv import load_dotenv
from langchain.messages import HumanMessage, ToolMessage
from langchain.tools import tool
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState
from loguru import logger

load_dotenv(override=True)


@tool(parse_docstring=True)
def get_weather(city: str) -> str:
    """
    查询指定城市的当日天气

    Args:
        city: 城市名称
    """
    return f"{city} 今天天气不错"


@tool(parse_docstring=True)
def get_news(home_or_abroad: bool) -> str:
    """
    查询国内外新闻

    Args:
        home_or_abroad: 查询国内还是国外新闻，True: 国内新闻，False：国外新闻
    """
    if home_or_abroad:
        return "Kimi 新模型发布"
    return "Anthropic 暂停新模型访问"


tools_by_name = {
    "get_weather": get_weather,
    "get_news": get_news,
}
tools = [get_weather, get_news]

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={
        "thinking": {"type": "disabled"}
    },
)
model_with_tools = model.bind_tools(tools=tools)


def llm_node(state: MessagesState) -> MessagesState:
    messages = state["messages"]
    response = model_with_tools.invoke(messages)

    return {"messages": [response]}


def tool_node(state: MessagesState) -> MessagesState:
    last_msg = state["messages"][-1]

    if not last_msg.tool_calls:
        return {}

    tool_msgs = []
    for tool_call in last_msg.tool_calls:
        tool = tools_by_name[tool_call["name"]]
        logger.info("工具 {} 被调用, 对应的 tool_call: {}", tool_call["name"], tool_call)

        tool_res = tool.invoke(tool_call["args"])

        tool_msg = ToolMessage(
            name=tool_call["name"],
            content=tool_res,
            tool_call_id=tool_call["id"],
        )
        tool_msgs.append(tool_msg)

    return {"messages": tool_msgs}


def router(state: MessagesState) -> Literal["tool_node", "__end__"]:
    if state["messages"][-1].tool_calls:
        return "tool_node"
    return END


builder = StateGraph(state_schema=MessagesState)
builder.add_node("llm_node", llm_node)
builder.add_node("tool_node", tool_node)

builder.add_edge(START, "llm_node")
builder.add_conditional_edges("llm_node", router, path_map=["tool_node", END])
builder.add_edge("tool_node", "llm_node")

graph = builder.compile()


if __name__ == "__main__":
    res = graph.invoke(
        {"messages": [HumanMessage("今天北京天气如何？国内有哪些新闻")]}
    )

    for msg in res["messages"]:
        msg.pretty_print()
