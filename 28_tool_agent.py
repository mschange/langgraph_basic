"""工具型智能体：绑定工具、Command 动态路由、工具失败后重试。

流程：
START → input_node → llm_node
  tool_calls 非空 → tool_node（60% 概率模拟失败）→ llm_node
  tool_calls 为空 → output_node → END

工具没有请求真实接口。失败时仍返回 ToolMessage，模型据此决定是否重试。

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from random import randint
from typing import Literal

from dotenv import load_dotenv
from langchain.messages import HumanMessage, SystemMessage, ToolMessage
from langchain.tools import tool
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState
from langgraph.types import Command

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)

FAIL_PROB = 6  # randint(0, 9) < 6，失败概率 60%


@tool(parse_docstring=True)
def get_weather(city: str = "北京") -> str:
    """查询指定城市当日天气。

    Args:
        city: 城市名称
    """
    return f"{city} 今天天气晴朗，东南风三级，气温 25~30 ℃"


@tool(parse_docstring=True)
def get_news(domain: Literal["AI", "食品安全"]) -> str:
    """查询特定领域的当日热点。

    Args:
        domain: 特定领域
    """
    if domain == "AI":
        return (
            "Anthropic 发布了 Claude Opus-4.8，但通过 API 用中文向它发送“你是谁？”时，"
            "大多数情况下返回的却是“Qwen”或“Deepseek”。"
        )
    return "双汇发展子公司猪肉产品被抽检出抗生素超标37.5倍"


tools = [get_weather, get_news]
model_with_tools = model.bind_tools(tools=tools)


class OverAllState(MessagesState):
    user_input: str
    final_answer: str


def input_node(state: OverAllState) -> dict:
    """把用户输入追加为 HumanMessage。"""
    return {"messages": [HumanMessage(state["user_input"])]}


def llm_node(
    state: OverAllState,
) -> Command[Literal["tool_node", "output_node"]]:
    """调用已绑定工具的模型，并按是否有 tool_calls 选择下一节点。"""
    ai_msg = model_with_tools.invoke(state["messages"])
    goto = "tool_node" if ai_msg.tool_calls else "output_node"
    return Command(goto=goto, update={"messages": [ai_msg]})


def _run_tool(tool_call: dict):
    """按名称执行工具；60% 概率模拟网络失败。未知工具名也返回 ToolMessage。"""
    name = tool_call["name"]
    if name == "get_weather":
        selected = get_weather
    elif name == "get_news":
        selected = get_news
    else:
        return ToolMessage(
            content="工具名称错误，调用失败，请重试",
            tool_call_id=tool_call["id"],
        )

    if randint(0, 9) < FAIL_PROB:
        return ToolMessage(
            content="网络波动，调用失败，请重试",
            tool_call_id=tool_call["id"],
        )
    return selected.invoke(tool_call)


def tool_node(state: OverAllState) -> dict:
    """执行上一条 AI 消息里的全部工具调用，只返回新的 ToolMessage。"""
    tool_calls = state["messages"][-1].tool_calls
    return {"messages": [_run_tool(tool_call) for tool_call in tool_calls]}


def output_node(state: OverAllState) -> dict:
    """保存最后一条模型文本作为最终回答。"""
    return {"final_answer": state["messages"][-1].content}


builder = StateGraph(state_schema=OverAllState)
builder.add_node("input_node", input_node)
builder.add_node("llm_node", llm_node)
builder.add_node("tool_node", tool_node)
builder.add_node("output_node", output_node)

builder.add_edge(START, "input_node")
builder.add_edge("input_node", "llm_node")
builder.add_edge("tool_node", "llm_node")
builder.add_edge("output_node", END)
# llm_node → tool_node / output_node 由 Command(goto=...) 决定

graph = builder.compile()


def run(user_input: str) -> dict:
    return graph.invoke(
        {
            "user_input": user_input,
            "messages": [
                SystemMessage("如果工具调用失败，必须重新调用直至成功")
            ],
        }
    )


def show(title: str, result: dict) -> None:
    print("=" * 30, f"-> {title} <-", "=" * 30)
    print("user_input: ", result["user_input"])
    print("final_answer: ", result["final_answer"])
    for msg in result["messages"]:
        msg.pretty_print()


if __name__ == "__main__":
    show("ai_res", run("帮我查询杭州当日天气和AI热点"))
    show("food_safety_res", run("帮我查询当日天气和食品安全相关的热点"))
