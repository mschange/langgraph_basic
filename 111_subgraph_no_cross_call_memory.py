"""子图检查点：父图有记忆 ≠ 子图有记忆。

流程：
父图 START → call_subgraph → END
子图 START → llm_node → END

父图 checkpointer 只保存 user_input / assistant_response；
子图默认 compile() 不跨调用保留 messages，第二轮看不到“我是老王”。
前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

import sys
from typing import TypedDict

from dotenv import load_dotenv
from loguru import logger

from langchain.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

logger.remove()
logger.add(sys.stdout, colorize=True)

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)


def llm_node(state: MessagesState) -> MessagesState:
    messages = state["messages"]

    logger.info("子图 llm_node 收到的消息：")
    for index, message in enumerate(messages, start=1):
        logger.opt(colors=True).info(
            "<cyan>[消息 {}]</cyan> 类型=<magenta>{}</magenta> 内容=<green>{}</green>",
            index,
            message.type,
            message.content,
        )

    response = model.invoke(input=messages)
    return {"messages": [response]}


sub_builder = StateGraph(state_schema=MessagesState)
sub_builder.add_node("llm_node", llm_node)
sub_builder.add_edge(START, "llm_node")
sub_builder.add_edge("llm_node", END)

subgraph = sub_builder.compile()


class ParentState(TypedDict):
    user_input: str
    assistant_response: str


def call_subgraph(state: ParentState) -> ParentState:
    messages = [
        SystemMessage(content="尽可能用简短的语言回答"),
        HumanMessage(content=state["user_input"]),
    ]
    subgraph_result = subgraph.invoke({"messages": messages})
    return {"assistant_response": subgraph_result["messages"][-1].content}


parent_builder = StateGraph(state_schema=ParentState)
parent_builder.add_node("call_subgraph", call_subgraph)
parent_builder.add_edge(START, "call_subgraph")
parent_builder.add_edge("call_subgraph", END)

parent_graph = parent_builder.compile(checkpointer=InMemorySaver())


if __name__ == "__main__":
    config = {"configurable": {"thread_id": "multi-turn-demo"}}

    first = parent_graph.invoke(
        {"user_input": "我是老王，从现在开始，你是小王"},
        config=config,
    )
    print("第一次调用：", first)

    second = parent_graph.invoke(
        {"user_input": "我是谁？你是谁？"},
        config=config,
    )
    print("第二次调用：", second)
