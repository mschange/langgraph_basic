"""运行时上下文：context 不写入检查点，每次调用单独传入。

VIP 用户使用尊称和专属结尾。不传 context 时 runtime.context 为空，走默认客服语气。
上下文适合放当前用户、请求来源这类只在本次调用有效的信息。

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from dataclasses import dataclass

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState
from langgraph.runtime import Runtime
from loguru import logger

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)


@dataclass
class UserContext:
    username: str
    membership_level: str


class OverAllState(MessagesState):
    user_input: str
    output: str


def llm_node(state: OverAllState, runtime: Runtime[UserContext]) -> dict:
    context = runtime.context
    if context:
        logger.info("当前用户: {}, 会员等级: {}", context.username, context.membership_level)
        if context.membership_level == "VIP":
            system_prompt = (
                f"你是高级客服助理。当前VIP用户是{context.username}，"
                "请使用尊称'您'，语气热情周到，回复末尾加上'VIP专属服务'。"
            )
        else:
            system_prompt = (
                f"你是普通客服助理。当前用户是{context.username}，请友好简洁地回复。"
            )
    else:
        logger.warning("运行时上下文为空，使用默认风格")
        system_prompt = "你是客服助理，请友好简洁地回复。"

    response = model.invoke(
        [HumanMessage(content=system_prompt)]
        + state.get("messages", [])
        + [HumanMessage(content=state["user_input"])]
    )
    return {"messages": [response], "output": response.content}


builder = StateGraph(state_schema=OverAllState, context_schema=UserContext)
builder.add_node("llm_node", llm_node)
builder.add_edge(START, "llm_node")
builder.add_edge("llm_node", END)
graph = builder.compile()


if __name__ == "__main__":
    config = {"configurable": {"thread_id": "context-demo"}}
    vip = graph.invoke(
        {"user_input": "你好，帮我查一下最近有什么优惠活动"},
        config=config,
        context=UserContext(username="Alice", membership_level="VIP"),
    )
    print("VIP 用户输出:", vip["output"])

    plain = graph.invoke(
        {"user_input": "再帮我看看有没有新品"},
        config=config,
    )
    print("无上下文输出:", plain["output"])
