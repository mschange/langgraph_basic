"""工具调用失败重试：ToolNode.wrap_tool_call + context 配置上限。

流程：
START → llm_node ⇄ tool_node(ToolNode) → END

get_weather 约 70% 抛 ConnectionError。wrap_tool_call 按 context.max_attempts 重试。
重试耗尽仍返回 ToolMessage，保证消息历史完整。
invoke(context=UserContext(max_attempts=3)) 由调用方传入上限。

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

import random
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv
from langchain.messages import HumanMessage, ToolMessage
from langchain.tools import tool
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState
from langgraph.prebuilt.tool_node import ToolNode
from loguru import logger

load_dotenv(override=True)


# ---------------------------------------------------------------------------
# 1. 不稳定工具：约 70% 概率失败
# ---------------------------------------------------------------------------
@tool(parse_docstring=True)
def get_weather(city: str) -> str:
    """
    查询指定城市的当日天气

    Args:
        city: 城市名称
    """
    if random.randint(1, 10) < 8:
        raise ConnectionError("网络波动失败")
    return f"{city} 今天天气不错"


tools = [get_weather]


# ---------------------------------------------------------------------------
# 2. 运行时上下文：把可配置参数放在 context 中，而不是写死在代码里
# ---------------------------------------------------------------------------
@dataclass
class UserContext:
    max_attempts: int


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
def llm_node(state: MessagesState) -> MessagesState:
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def router(state: MessagesState) -> Literal["tool_node", "__end__"]:
    if state["messages"][-1].tool_calls:
        return "tool_node"
    return END


# ---------------------------------------------------------------------------
# 5. 重试包装器
# ---------------------------------------------------------------------------
def wrap_tool_call(request, execute):
    """
    对单次工具调用做「失败重试」。

    request: ToolCallRequest
    execute: 可调用对象，执行真正的工具逻辑，返回 ToolMessage
    """
    # 重试上限来自运行时 context，由调用方决定
    max_attempts = request.runtime.context.max_attempts
    # 工具调用 ID 取自 runtime，用于兜底构造 ToolMessage
    tool_call_id = request.runtime.tool_call_id

    tool_msg = None
    for i in range(max_attempts):
        try:
            tool_msg = execute(request)
            break
        except ConnectionError as e:
            logger.info(
                "工具调用失败，当前第 {} 次，上限 {} 次，异常: {}",
                i + 1,
                max_attempts,
                e,
            )

    # 所有重试都失败：也必须返回 ToolMessage，保证消息历史完整
    if tool_msg is None:
        tool_msg = ToolMessage(
            tool_call_id=tool_call_id,
            content="调用次数到达上限，调用失败",
        )

    return tool_msg


# ---------------------------------------------------------------------------
# 6. 组装图：通过 context_schema 声明上下文类型
# ---------------------------------------------------------------------------
builder = StateGraph(state_schema=MessagesState, context_schema=UserContext)
builder.add_node("llm_node", llm_node)
builder.add_node("tool_node", ToolNode(tools=tools, wrap_tool_call=wrap_tool_call))
builder.add_edge(START, "llm_node")
builder.add_conditional_edges("llm_node", router, path_map=["tool_node", END])
builder.add_edge("tool_node", "llm_node")

graph = builder.compile()


# ---------------------------------------------------------------------------
# 7. 运行
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    res = graph.invoke(
        {"messages": [HumanMessage("今天北京天气如何？")]},
        context=UserContext(max_attempts=3),
    )

    for msg in res["messages"]:
        msg.pretty_print()
