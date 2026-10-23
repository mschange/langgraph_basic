"""条件路由 + path_map：路由返回别名，再映射到真实节点名。

好处：路由逻辑与节点命名解耦，修改节点名时只需改 path_map。

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

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
    poem: str
    joke: str


# ========== 定义节点 ==========
def node_a(state: OverAllState) -> OverAllState:
    poem = model.invoke(
        [HumanMessage(f"写一首关于 {state['topic']} 的七言绝句")]
    ).content
    return {"poem": poem}


def node_b(state: OverAllState) -> OverAllState:
    joke = model.invoke(
        [HumanMessage(f"写一个关于 {state['topic']} 的笑话")]
    ).content
    return {"joke": joke}


# 返回值是别名 "a" / "b"，不是真实节点名
def router(state: OverAllState) -> Literal["a", "b"]:
    if "诗" in state["content_type"]:
        return "a"
    return "b"


# ========== 构建并编译图 ==========
builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)

builder.add_conditional_edges(
    START,
    router,
    path_map={
        "a": "node_a",
        "b": "node_b",
    },
)
builder.add_edge("node_a", END)
builder.add_edge("node_b", END)

graph = builder.compile()


if __name__ == "__main__":
    poem_res = graph.invoke({"topic": "布偶狗", "content_type": "诗"})
    joke_res = graph.invoke({"topic": "布偶狗", "content_type": "笑话"})

    rprint("=" * 30, "-> poem_res <-", "=" * 30)
    rprint(poem_res)
    rprint("=" * 30, "-> joke_res <-", "=" * 30)
    rprint(joke_res)
