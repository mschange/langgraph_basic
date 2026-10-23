"""多目标条件路由：路由函数返回节点名序列，并行执行多个分支。

请求"诗" → node_a + node_c；请求"笑话" → node_b + node_c。

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from collections.abc import Sequence
from typing import TypedDict, Literal

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
    topic: str
    content_type: str
    poem: str       # 七言绝句
    ci_poem: str    # 词
    joke: str       # 笑话


# ========== 定义节点 ==========
def node_a(state: OverAllState) -> OverAllState:
    """写七言绝句。"""
    poem = model.invoke(
        [HumanMessage(f"写一首关于 {state['topic']} 的七言绝句")]
    ).content
    return {"poem": poem}


def node_b(state: OverAllState) -> OverAllState:
    """写笑话。"""
    joke = model.invoke(
        [HumanMessage(f"写一个关于 {state['topic']} 的笑话")]
    ).content
    return {"joke": joke}


def node_c(state: OverAllState) -> OverAllState:
    """写词。"""
    ci_poem = model.invoke(
        [HumanMessage(f"写一首关于 {state['topic']} 的词")]
    ).content
    return {"ci_poem": ci_poem}


def router(
    state: OverAllState,
) -> Sequence[Literal["node_a", "node_b", "node_c"]]:
    """返回序列 → 多个节点并行执行。"""
    if "诗" in state["content_type"]:
        return ["node_a", "node_c"]
    return ["node_b", "node_c"]


# ========== 构建并编译图 ==========
builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)
builder.add_node("node_c", node_c)

builder.add_conditional_edges(START, router)
builder.add_edge("node_a", END)
builder.add_edge("node_b", END)
builder.add_edge("node_c", END)

graph = builder.compile()


if __name__ == "__main__":
    poem_res = graph.invoke({"topic": "布偶狗", "content_type": "诗"})
    rprint("=" * 30, "-> poem_res <-", "=" * 30)
    rprint(poem_res)

    joke_res = graph.invoke({"topic": "布偶狗", "content_type": "笑话"})
    rprint("=" * 30, "-> joke_res <-", "=" * 30)
    rprint(joke_res)
