"""条件路由基础用法：add_conditional_edges 根据状态动态选择分支。

路由函数返回真实节点名时可不传 path_map。

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
    topic: str          # 主题
    content_type: str   # 内容类型："诗" 或 "笑话"
    poem: str
    joke: str


# ========== 定义节点 ==========
def node_a(state: OverAllState) -> OverAllState:
    """写诗节点。"""
    poem = model.invoke(
        [HumanMessage(f"写一首关于 {state['topic']} 的七言绝句")]
    ).content
    return {"poem": poem}


def node_b(state: OverAllState) -> OverAllState:
    """写笑话节点。"""
    joke = model.invoke(
        [HumanMessage(f"写一个关于 {state['topic']} 的笑话")]
    ).content
    return {"joke": joke}


def router(state: OverAllState) -> Literal["node_a", "node_b"]:
    """根据 content_type 决定走哪条分支；返回值必须是已注册节点名或 END。"""
    if "诗" in state["content_type"]:
        return "node_a"
    return "node_b"


# ========== 构建并编译图 ==========
builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)

# router 返回值直接就是节点名，不需要 path_map
builder.add_conditional_edges(START, router)
builder.add_edge("node_a", END)
builder.add_edge("node_b", END)

graph = builder.compile()


if __name__ == "__main__":
    poem_res = graph.invoke({"topic": "布偶狗", "content_type": "诗"})
    rprint("=" * 30, "-> poem_res <-", "=" * 30)
    rprint(poem_res)

    joke_res = graph.invoke({"topic": "布偶狗", "content_type": "笑话"})
    rprint("=" * 30, "-> joke_res <-", "=" * 30)
    rprint(joke_res)
