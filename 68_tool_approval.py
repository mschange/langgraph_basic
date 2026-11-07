"""工具内部审批：get_weather 内 interrupt，批准后才执行模拟查询。

流程：
START → llm_node ⇄ tool_node → END

llm_node 先产生带 tool_calls 的 AIMessage。
tool_node 手工遍历工具调用；审批暂停发生在 get_weather 内部。
外部用 Command(resume=True/False) 交回布尔值。
批准后调用 simulate_weather；拒绝返回固定文案，不执行查询。
工具结果写回 ToolMessage 后再次进入 llm_node 总结。

默认 create_demo_model 为确定性离线模拟器，不调用真实 LLM。
--live-model 才导入 DeepSeek；天气工具始终只返回模拟数据。
InMemorySaver 只在当前进程有效。
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from typing import Literal, cast
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt


def simulate_weather(city: str) -> str:
    """返回固定模拟天气；不联网，也不提供实时天气信息。"""
    print("[工具] 执行模拟天气查询")
    return f"{city}今天天气不错（模拟数据，非实时天气）"


@tool
def get_weather(city: str) -> str:
    """在人工批准后查询指定城市的模拟天气，拒绝则不执行查询。"""
    # 这里只做最低限度的业务参数校验，不代表完整的生产权限校验。
    if not city.strip():
        raise ValueError("city 必须是非空城市名称")

    # 暂停发生在工具内部；载荷必须让审批人看清实际操作及其参数。
    approval = interrupt(
        {
            "action": "get_weather",
            "question": "是否同意查询天气？",
            "args": {"city": city},
        }
    )
    # 恢复值必须是布尔值：不能用 bool('false')，它实际上为 True。
    if not isinstance(approval, bool):
        raise TypeError("审批恢复值必须是 bool（True 或 False），不能使用字符串或整数")
    if not approval:
        return "用户拒绝查询天气"

    # 独立执行函数便于检查：拒绝路径绝不能调用它。
    return simulate_weather(city)


# 显式工具白名单：模型给出的名称不是可以任意执行函数的授权。
tools_by_name = {"get_weather": get_weather}


def create_demo_model(city: str) -> Callable[[list[BaseMessage]], AIMessage]:
    """创建确定性离线对话模拟器；它不调用真实 LLM，也不联网。"""

    def demo_model(messages: list[BaseMessage]) -> AIMessage:
        if not messages:
            raise ValueError("离线对话模拟器需要至少一条消息")
        last = messages[-1]
        if isinstance(last, HumanMessage):
            # 城市取自显式 city 参数，不通过自然语言识别或真实模型推断。
            return AIMessage(
                content=f"我将申请查询{city}的模拟天气。",
                tool_calls=[
                    {
                        "name": "get_weather",
                        "args": {"city": city},
                        "id": "demo-weather-call-001",
                        "type": "tool_call",
                    }
                ],
            )
        if isinstance(last, ToolMessage):
            # 无论批准还是拒绝，都总结工具返回值；不再请求工具，因此能结束。
            return AIMessage(
                content=(
                    f"工具处理结果：{last.content}"
                    "（确定性离线对话模拟，非真实 LLM 回答）"
                )
            )
        raise ValueError("离线对话模拟器只支持 HumanMessage 或 ToolMessage 作为末条消息")

    return demo_model


def create_live_model() -> Callable[[list[BaseMessage]], AIMessage]:
    """显式创建真实 DeepSeek 模型；此模式的天气工具仍然只返回模拟数据。"""
    # 惰性导入：默认离线运行无需安装这两个额外依赖，也无需 API Key。
    from dotenv import load_dotenv
    from langchain_deepseek import ChatDeepSeek

    # 仅读取已有环境文件，不创建或写入文件，不覆盖已有环境变量。
    load_dotenv(override=False)
    bound_model = ChatDeepSeek(
        model="deepseek-v4-flash",
        extra_body={"thinking": {"type": "disabled"}},
    ).bind_tools([get_weather])

    def live_model(messages: list[BaseMessage]) -> AIMessage:
        response = bound_model.invoke(messages)
        if not isinstance(response, AIMessage):
            raise TypeError("真实模型必须返回 AIMessage")
        return response

    return live_model


def build_graph(
    model: Callable[[list[BaseMessage]], AIMessage] | None = None,
    city: str = "北京",
) -> CompiledStateGraph:
    """构建带内存检查点的审批图；可注入模型，默认使用离线模拟器。"""
    active_model = model if model is not None else create_demo_model(city)

    def llm_node(state: MessagesState) -> dict[str, list[AIMessage]]:
        response = active_model(state["messages"])
        if not isinstance(response, AIMessage):
            raise TypeError("注入的模型必须返回 AIMessage")
        # 只返回新增消息；MessagesState 的 add_messages 会合并历史。
        return {"messages": [response]}

    def tool_node(state: MessagesState) -> dict[str, list[ToolMessage]]:
        # 此节点只由带工具调用的 AIMessage 路由进入；cast 不执行运行时转换。
        last = cast(AIMessage, state["messages"][-1])
        results: list[ToolMessage] = []
        for tool_call in last.tool_calls:
            name = tool_call["name"]
            selected_tool = tools_by_name.get(name)
            if selected_tool is None:
                raise ValueError(f"未知工具：{name!r}，不在 tools_by_name 白名单中")
            # 保留手工循环；不要用宽泛 except 吞掉用于暂停图的 GraphInterrupt。
            content = selected_tool.invoke(tool_call["args"])
            results.append(
                ToolMessage(
                    name=name,
                    content=content,
                    tool_call_id=tool_call["id"],
                )
            )
        # 中断时本次局部 results 尚未作为节点更新提交；恢复会重执行节点。
        return {"messages": results}

    def router(state: MessagesState) -> Literal["tool_node", "__end__"]:
        last = cast(AIMessage, state["messages"][-1])
        return "tool_node" if last.tool_calls else END

    builder = StateGraph(state_schema=MessagesState)
    builder.add_node("llm_node", llm_node)
    builder.add_node("tool_node", tool_node)
    builder.add_edge(START, "llm_node")
    builder.add_conditional_edges("llm_node", router)
    builder.add_edge("tool_node", "llm_node")
    # 内存检查点只属于当前图实例/进程，不具备跨进程持久化能力。
    return builder.compile(checkpointer=InMemorySaver())


def read_approval(question: str) -> bool:
    """只接受 y/n；其他输入必须重问，不能隐式当作批准。"""
    while True:
        answer = input(f"{question} (y/n)：").strip().lower()
        if answer == "y":
            return True
        if answer == "n":
            return False
        print("输入无效，请只输入 y 或 n。")


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="LangGraph 工具内部人工审批演示")
    parser.add_argument("--city", default="北京", help="查询目标城市，默认北京")
    parser.add_argument(
        "--live-model", action="store_true", help="显式使用真实 DeepSeek 模型；天气仍为模拟"
    )
    options = parser.parse_args(args)
    if not options.city.strip():
        parser.error("--city 必须是非空城市名称")

    print("天气工具始终返回模拟数据，不提供实时天气。")
    print(
        "对话模式："
        + ("真实 DeepSeek 模型" if options.live_model else "确定性离线模拟，非真实 LLM")
    )
    model = create_live_model() if options.live_model else None
    graph = build_graph(model=model, city=options.city)
    # 同一次对话始终复用这份配置；新进程/新图不能凭相同 ID 找回内存状态。
    config = {"configurable": {"thread_id": uuid4().hex}, "recursion_limit": 50}
    result = graph.invoke(
        {"messages": [HumanMessage(content=f"今天{options.city}天气如何？")]},
        config=config,
    )
    print("\n=== 首次调用：当前消息与中断 ===")
    for message in result["messages"]:
        message.pretty_print()
    print("__interrupt__：", result.get("__interrupt__", ()))

    # 真实模型可能在恢复后继续请求工具，不能假设一次恢复就结束。
    while "__interrupt__" in result:
        pending = result["__interrupt__"]
        if len(pending) != 1:
            raise RuntimeError("本串行演示每次只处理一个当前中断，不支持并行中断批量审批")
        payload = pending[0].value
        print("\n=== 当前工具审批 ===")
        print("操作：", payload["action"])
        print("参数：", json.dumps(payload["args"], ensure_ascii=False))
        approval = read_approval(payload["question"])
        result = graph.invoke(Command(resume=approval), config=config)
        print("恢复后的 __interrupt__：", result.get("__interrupt__", ()))

    print("\n=== 最终全部消息 ===")
    for message in result["messages"]:
        message.pretty_print()
    print("next：", graph.get_state(config).next)


if __name__ == "__main__":
    main()
