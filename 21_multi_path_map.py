"""多目标路由 + 显式 path_map：声明下游节点集合，辅助可视化渲染。

path_map 可用字典或列表；返回值即节点名时二者等价。

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from collections.abc import Sequence
from typing import TypedDict, Literal

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, START, END

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
    ci_poem: str
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


def node_c(state: OverAllState) -> OverAllState:
    ci_poem = model.invoke(
        [HumanMessage(f"写一首关于 {state['topic']} 的词")]
    ).content
    return {"ci_poem": ci_poem}


def router(
    state: OverAllState,
) -> Sequence[Literal["node_a", "node_b", "node_c"]]:
    if "诗" in state["content_type"]:
        return ["node_a", "node_c"]
    return ["node_b", "node_c"]


# ========== 构建并编译图 ==========
builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)
builder.add_node("node_c", node_c)

builder.add_conditional_edges(
    START,
    router,
    # 字典形式；也可写成 path_map=["node_a", "node_b", "node_c"]
    path_map={
        "node_a": "node_a",
        "node_b": "node_b",
        "node_c": "node_c",
    },
)
builder.add_edge("node_a", END)
builder.add_edge("node_b", END)
builder.add_edge("node_c", END)

graph = builder.compile()


if __name__ == "__main__":
    poem_res = graph.invoke({"topic": "布偶狗", "content_type": "诗"})
    joke_res = graph.invoke({"topic": "布偶狗", "content_type": "笑话"})

    print("=" * 30, "-> poem_res <-", "=" * 30)
    print(poem_res)
    print("=" * 30, "-> joke_res <-", "=" * 30)
    print(joke_res)
