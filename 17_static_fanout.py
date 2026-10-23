"""静态并行分支：从 START 扇出到多个下游节点，并行执行。

流程图：
         ┌──→ node_a（写诗）──→ END
START ───┤
         └──→ node_b（写笑话）──→ END

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from typing import TypedDict

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, START, END
from rich import print as rprint

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)


# ========== 定义状态 ==========
class OverAllState(TypedDict):
    topic: str    # 主题
    poem: str     # 诗
    joke: str     # 笑话


# ========== 定义节点 ==========
def node_a(state: OverAllState) -> OverAllState:
    """调用 LLM 写一首七言绝句。"""
    poem = model.invoke(
        [HumanMessage(f"写一首关于 {state['topic']} 的七言绝句")]
    ).content
    return {"poem": poem}


def node_b(state: OverAllState) -> OverAllState:
    """调用 LLM 写一个笑话。"""
    joke = model.invoke(
        [HumanMessage(f"写一个关于 {state['topic']} 的笑话")]
    ).content
    return {"joke": joke}


# ========== 构建并编译图 ==========
builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)

# 从 START 分别连到两个节点 → 并行执行
builder.add_edge(START, "node_a")
builder.add_edge(START, "node_b")
builder.add_edge("node_a", END)
builder.add_edge("node_b", END)

graph = builder.compile()


if __name__ == "__main__":
    res = graph.invoke({"topic": "猫咪"})
    rprint(res)
