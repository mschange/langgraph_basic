"""预构建 ToolNode：把工具查找、校验、异常包装与并行执行交给框架。

流程：
START → llm_node ⇄ tool_node(ToolNode) → END

与手写 tool_node 不同：这里 add_node 直接传入 ToolNode(tools=tools)。
无效工具名、参数校验失败或工具异常会包装成错误 ToolMessage，而不是整图崩溃。

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from typing import Literal

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain.tools import tool
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState
from langgraph.prebuilt.tool_node import ToolNode

load_dotenv(override=True)


# ---------------------------------------------------------------------------
# 1. 定义工具
# ---------------------------------------------------------------------------
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


tools = [get_weather, get_news]


# ---------------------------------------------------------------------------
# 2. 模型绑定工具
# ---------------------------------------------------------------------------
model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)
model_with_tools = model.bind_tools(tools=tools)


# ---------------------------------------------------------------------------
# 3. 节点与路由
# ---------------------------------------------------------------------------
def llm_node(state: MessagesState) -> MessagesState:
    """模型推理，可能返回纯文本，也可能返回 tool_calls"""
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def router(state: MessagesState) -> Literal["tool_node", "__end__"]:
    """有工具调用请求就去 ToolNode，否则结束"""
    if state["messages"][-1].tool_calls:
        return "tool_node"
    return END


# ---------------------------------------------------------------------------
# 4. 组装图：tool_node 直接使用预构建的 ToolNode
# ---------------------------------------------------------------------------
builder = StateGraph(state_schema=MessagesState)
builder.add_node("llm_node", llm_node)

# 只需要传入工具列表，其余全部由 ToolNode 处理：
#   - 按 tool_call["name"] 查找工具（无效名称会产生错误 ToolMessage，而不是崩溃）
#   - 校验 args 是否符合 Schema
#   - 捕获工具异常并包装成 ToolMessage
#   - 自动构造带 tool_call_id 的 ToolMessage
#   - 多个 tool_calls 并行执行
builder.add_node("tool_node", ToolNode(tools=tools))

builder.add_edge(START, "llm_node")
builder.add_conditional_edges("llm_node", router, path_map=["tool_node", END])
builder.add_edge("tool_node", "llm_node")

graph = builder.compile()


# ---------------------------------------------------------------------------
# 5. 运行
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    res = graph.invoke(
        {"messages": [HumanMessage("今天北京天气如何？国内有哪些新闻？")]}
    )

    for msg in res["messages"]:
        msg.pretty_print()

    # 也可以打印图结构，确认 ToolNode 已被当作普通节点接入
    # print(graph.get_graph().draw_mermaid())
