"""多轮对话：同一 thread_id 的多次调用共享消息历史。

流程：START → llm_node → output_node → END
InMemorySaver 只存在于当前进程，重新运行脚本会清空历史。

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
config = {"configurable": {"thread_id": "chapter_6_6-2-2"}}


if __name__ == "__main__":
    graph.invoke({"messages": [HumanMessage("你好，我是老王")]}, config=config)
    graph.invoke(
        {"messages": [HumanMessage("从现在开始，你是小王")]},
        config=config,
    )
    result = graph.invoke(
        {"messages": [HumanMessage("我是谁？你是谁？")]},
        config=config,
    )
    print(result["output"])
