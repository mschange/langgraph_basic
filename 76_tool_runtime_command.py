"""ToolRuntime + Command：工具里读写状态，把结果写入业务字段。

流程：
START → llm_node ⇄ tool_node(ToolNode) → END

工具声明 runtime: ToolRuntime 后由运行时注入，可读 tool_call_id。
返回 Command(update=...) 时必须自己补上匹配的 ToolMessage。
本例分别写入 weather_res / news_res，互不冲突，无需 reducer。

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from typing import Literal

from dotenv import load_dotenv
from langchain.messages import HumanMessage, ToolMessage
from langchain.tools import tool
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState
from langgraph.prebuilt.tool_node import ToolNode, ToolRuntime
from langgraph.types import Command

load_dotenv(override=True)


# ---------------------------------------------------------------------------
# 1. 扩展状态：在 MessagesState 基础上增加两个业务字段
# ---------------------------------------------------------------------------
class OverAllState(MessagesState):
    weather_res: str
    news_res: str


# ---------------------------------------------------------------------------
# 2. 工具：通过 ToolRuntime 拿 tool_call_id，返回 Command 更新状态
# ---------------------------------------------------------------------------
# 注意：runtime 参数不需要写进 docstring，模型也不会看到它。
# 只要名称是 runtime 且类型标注为 ToolRuntime，运行时就会自动注入。

@tool(parse_docstring=True)
def get_weather(city: str, runtime: ToolRuntime) -> Command:
    """
    查询指定城市的当日天气

    Args:
        city: 城市名称
    """
    res = f"{city} 今天天气不错"

    # ToolRuntime 提供当前这次工具调用的 ID
    tool_call_id = runtime.tool_call_id

    # ToolNode 只在工具返回普通结果时自动构造 ToolMessage；
    # 返回 Command 时必须自己构造，并写入 messages 字段，
    # 否则 AIMessage.tool_calls 找不到对应的 ToolMessage，消息历史不合法
    tool_msg = ToolMessage(tool_call_id=tool_call_id, content=res)

    return Command(
        update={
            "weather_res": res,
            "messages": [tool_msg],
        }
    )


@tool(parse_docstring=True)
def get_news(home_or_abroad: bool, runtime: ToolRuntime) -> Command:
    """
    查询国内外新闻

    Args:
        home_or_abroad: 查询国内还是国外新闻，True: 国内新闻，False：国外新闻
    """
    if home_or_abroad:
        res = "Kimi 新模型发布"
    else:
        res = "Anthropic 暂停新模型访问"

    tool_call_id = runtime.tool_call_id
    tool_msg = ToolMessage(tool_call_id=tool_call_id, content=res)

    return Command(
        update={
            "news_res": res,
            "messages": [tool_msg],
        }
    )


tools = [get_weather, get_news]


# ---------------------------------------------------------------------------
# 3. 模型
# ---------------------------------------------------------------------------
model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)
model_with_tools = model.bind_tools(tools=tools)


# ---------------------------------------------------------------------------
# 4. 节点与路由
# ---------------------------------------------------------------------------
def llm_node(state: OverAllState) -> OverAllState:
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def router(state: OverAllState) -> Literal["tool_node", "__end__"]:
    if state["messages"][-1].tool_calls:
        return "tool_node"
    return END


# ---------------------------------------------------------------------------
# 5. 组装图
# ---------------------------------------------------------------------------
builder = StateGraph(state_schema=OverAllState)
builder.add_node("llm_node", llm_node)
builder.add_node("tool_node", ToolNode(tools=tools))
builder.add_edge(START, "llm_node")
builder.add_conditional_edges("llm_node", router, path_map=["tool_node", END])
builder.add_edge("tool_node", "llm_node")

graph = builder.compile()


# ---------------------------------------------------------------------------
# 6. 运行
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    res = graph.invoke(
        {"messages": [HumanMessage("今天北京天气如何？国内有哪些新闻？")]}
    )

    print("=" * 30, "-> messages <-", "=" * 30)
    # pop 掉 messages，剩下的就是自定义业务字段
    for msg in res.pop("messages"):
        msg.pretty_print()

    print("=" * 30, "-> 除 messages 外的业务状态 <-", "=" * 30)
    print(res)
