"""工具结果缓存：ToolNode.wrap_tool_call 按 (工具名, 参数JSON) 命中跳过执行。

流程：
START → llm_node ⇄ tool_node(ToolNode) → END

缓存键不含 tool_call_id。命中时仍用当前 tool_call_id 新建 ToolMessage。
进程内字典适合单实例示例；多实例可换 Redis，包装器结构不变。

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

import json
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
# 1. 工具
# ---------------------------------------------------------------------------
@tool(parse_docstring=True)
def get_weather(city: str) -> str:
    """
    查询指定城市的当日天气

    Args:
        city: 城市名称
    """
    # 这行日志用于验证「命中缓存时工具没有被真正执行」
    logger.info("真正执行 get_weather(city={})", city)
    return f"{city} 今天天气不错"


tools = [get_weather]


# ---------------------------------------------------------------------------
# 2. 模型
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
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def router(state: MessagesState) -> Literal["tool_node", "__end__"]:
    if state["messages"][-1].tool_calls:
        return "tool_node"
    return END


# ---------------------------------------------------------------------------
# 4. 缓存包装器
# ---------------------------------------------------------------------------
# 进程内简单缓存：key = (工具名, 参数JSON)，value = 工具返回的字符串内容
cache_store: dict[tuple[str, str], str] = {}


def wrap_tool_call(request, execute):
    """工具结果缓存：命中则跳过执行，未命中则执行并写回缓存"""
    tool_name = request.tool_call["name"]
    # 参数要序列化成字符串才能作为字典 key；排序保证相同参数得到相同键
    tool_args = json.dumps(
        request.tool_call["args"], sort_keys=True, ensure_ascii=False
    )
    tool_call_id = request.runtime.tool_call_id

    cache_key = (tool_name, tool_args)
    cached = cache_store.get(cache_key)

    if cached is not None:
        logger.info("{} 调用命中缓存，参数: {}", tool_name, tool_args)
        # 命中缓存也要重新构造 ToolMessage：tool_call_id 每次调用都不同
        return ToolMessage(tool_call_id=tool_call_id, content=cached)

    tool_msg = execute(request)
    logger.info("{} 调用未命中缓存，结果已写入缓存，参数: {}", tool_name, tool_args)
    cache_store[cache_key] = tool_msg.content
    return tool_msg


# ---------------------------------------------------------------------------
# 5. 组装图
# ---------------------------------------------------------------------------
builder = StateGraph(state_schema=MessagesState)
builder.add_node("llm_node", llm_node)
builder.add_node("tool_node", ToolNode(tools=tools, wrap_tool_call=wrap_tool_call))
builder.add_edge(START, "llm_node")
builder.add_conditional_edges("llm_node", router, path_map=["tool_node", END])
builder.add_edge("tool_node", "llm_node")

graph = builder.compile()


# ---------------------------------------------------------------------------
# 6. 运行
# ---------------------------------------------------------------------------
def ask(question: str) -> None:
    print("=" * 30, f"-> {question} <-", "=" * 30)
    res = graph.invoke({"messages": [HumanMessage(question)]})
    for msg in res["messages"]:
        msg.pretty_print()


if __name__ == "__main__":
    ask("今天北京天气如何？")   # 第一次：未命中，执行工具
    ask("今天北京天气如何？")   # 第二次：命中缓存，不执行工具
    ask("今天杭州天气如何？")   # 第三次：参数不同，未命中，执行工具
