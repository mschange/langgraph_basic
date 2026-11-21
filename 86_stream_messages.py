"""流式输出 messages（同步）：LLM token 级流，产出 (chunk, metadata)。

流程：
START → llm_node → END

节点内写 model.invoke 即可，LangGraph 会接管为流式。
stream_mode=["values", "messages"]：token 流 + 节点结束后的完整状态。
空 content 帧应跳过。前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, MessagesState, StateGraph

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)


def llm_node(state: MessagesState) -> MessagesState:
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


builder = StateGraph(state_schema=MessagesState)
builder.add_node("llm_node", llm_node)
builder.add_edge(START, "llm_node")
builder.add_edge("llm_node", END)

graph = builder.compile()


if __name__ == "__main__":
    for chunk in graph.stream(
        {"messages": [HumanMessage(content="你好!")]},
        stream_mode=["values", "messages"],
    ):
        print(chunk)
