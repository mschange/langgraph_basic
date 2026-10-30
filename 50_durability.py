"""持久化模式：invoke 的 durability 决定检查点何时写入。

exit：图结束或异常退出时写入，开销最小。
async：每个超步结束后异步写入，默认模式。
sync：每个超步结束后等待写入完成，一致性最强。

本例使用 InMemorySaver，并显式指定 async。

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)


class OverAllState(MessagesState):
    output: str


def llm_node(state: OverAllState) -> dict:
    return {"messages": [model.invoke(state["messages"])]}


def output_node(state: OverAllState) -> dict:
    return {"output": state["messages"][-1].content}


builder = StateGraph(state_schema=OverAllState)
builder.add_node("llm_node", llm_node)
builder.add_node("output_node", output_node)
builder.add_edge(START, "llm_node")
builder.add_edge("llm_node", "output_node")
builder.add_edge("output_node", END)

graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "chapter_tmp"}}


if __name__ == "__main__":
    result = graph.invoke(
        {"messages": [HumanMessage("你好")]},
        config=config,
        durability="async",
    )
    print(result["output"])

    print("=" * 30, "-> 完整消息列表 <-", "=" * 30)
    for message in result["messages"]:
        message.pretty_print()
