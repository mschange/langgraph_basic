"""流式输出 custom（工具）：ToolRuntime.stream_writer + messages 组合。

流程：
START → llm_node ⇄ tool_node(ToolNode) → END

节点用 Runtime，工具用 ToolRuntime；均可 stream_writer。
默认同时订阅 messages + custom：进度提示 + token 流。
前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from typing import Literal

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain.tools import tool
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt.tool_node import ToolNode, ToolRuntime
from langgraph.runtime import Runtime

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)


@tool(parse_docstring=True)
def get_weather(city: str, runtime: ToolRuntime) -> str:
    """根据城市查询当日天气

    Args:
        city: 城市名称
    """
    runtime.stream_writer(f"正在查询 {city} 今天的天气...")
    return f"{city} 今天天气不错"


tools = [get_weather]
model_with_tools = model.bind_tools(tools=tools)


def llm_node(state: MessagesState, runtime: Runtime) -> MessagesState:
    response = model_with_tools.invoke(state["messages"])
    runtime.stream_writer("正在执行 llm_node...")
    return {"messages": [response]}


def router(state: MessagesState) -> Literal["tool_node", END]:
    if state["messages"][-1].tool_calls:
        return "tool_node"
    return END


builder = StateGraph(state_schema=MessagesState)
builder.add_node("llm_node", llm_node)
builder.add_node("tool_node", ToolNode(tools=tools))
builder.add_edge(START, "llm_node")
builder.add_conditional_edges("llm_node", router, path_map=["tool_node", END])
builder.add_edge("tool_node", "llm_node")

graph = builder.compile()


if __name__ == "__main__":
    for mode, data in graph.stream(
        {"messages": [HumanMessage(content="今天北京天气如何？")]},
        stream_mode=["messages", "custom"],
    ):
        if mode == "custom":
            print(f"\n[进度] {data}", flush=True)
        else:
            chunk, metadata = data
            if getattr(chunk, "content", ""):
                print(chunk.content, end="", flush=True)
    print()
