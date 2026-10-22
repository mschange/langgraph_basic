"""MessagesState：内置 messages + add_messages，面向 LLM 对话。

前置：
  pip install langchain-deepseek python-dotenv rich
  项目根目录 .env 中配置 DEEPSEEK_API_KEY=...

流程：START → node_a（构造 HumanMessage）→ llm_node（调用模型）→ END
"""

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState
from rich import print as rprint

load_dotenv(override=True)

# ========== 初始化 LLM ==========
model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={
        "thinking": {
            "type": "disabled",
        }
    },
)


# ========== 定义状态：继承 MessagesState，扩展业务字段 ==========
class OverAllState(MessagesState):
    username: str
    output: str


# ========== 定义节点 ==========
def node_a(state: OverAllState) -> OverAllState:
    """预处理：根据 username 写入一条 HumanMessage（add_messages 追加）。"""
    return {
        "messages": [HumanMessage("你好，我是 " + state["username"])],
    }


def llm_node(state: OverAllState) -> OverAllState:
    """调用 LLM，将 AIMessage 追加到 messages，并把文本写入 output。"""
    res = model.invoke(state["messages"])
    return {
        "messages": [res],
        "output": res.content,
    }


# ========== 构建并编译图 ==========
builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_a", node_a)
builder.add_node("llm_node", llm_node)
builder.add_edge(START, "node_a")
builder.add_edge("node_a", "llm_node")
builder.add_edge("llm_node", END)

graph = builder.compile()


if __name__ == "__main__":
    response = graph.invoke({"username": "小黄"})
    rprint(response)
