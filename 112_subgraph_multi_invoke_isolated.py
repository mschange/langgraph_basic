"""子图检查点：同一 thread 内多次 invoke 子图，彼此隔离。

流程：
父图 START → call_subgraph（循环多次 subgraph.invoke）→ END
子图 START → llm_node → END

同一 thread_id 只影响父图状态，不会把上下文注入每次子图调用。
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
    user_inputs: list[str]
    assistant_responses: list[str]


def call_subgraph(state: ParentState) -> ParentState:
    responses = []
    for user_input in state["user_inputs"]:
        messages = [
            SystemMessage(content="用最简短的话回答用户的提问"),
            HumanMessage(content=user_input),
        ]
        subgraph_result = subgraph.invoke({"messages": messages})
        responses.append(subgraph_result["messages"][-1].content)
    return {"assistant_responses": responses}


parent_builder = StateGraph(state_schema=ParentState)
parent_builder.add_node("call_subgraph", call_subgraph)
parent_builder.add_edge(START, "call_subgraph")
parent_builder.add_edge("call_subgraph", END)

parent_graph = parent_builder.compile(checkpointer=InMemorySaver())


if __name__ == "__main__":
    config = {"configurable": {"thread_id": "multi-call-same-demo"}}

    first = parent_graph.invoke(
        {"user_inputs": ["5*5等于几", "10*10等于几"]},
        config=config,
    )
    print("第一次运行结果：", first)

    second = parent_graph.invoke(
        {"user_inputs": ["再+1呢?", "再+10000呢?"]},
        config=config,
    )
    print("第二次运行结果：", second)
