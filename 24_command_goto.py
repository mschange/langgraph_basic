"""Command(goto=...)：节点内部决定下一步跳转目标（运行时路由）。

与 add_conditional_edges 的区别：路由逻辑写在节点返回值里，还可同时 update 状态。

流程：
  content_type=poem → START → router → poem_node → END
  content_type=joke → START → router → joke_node → END
  其他值          → START → router → END（兜底）

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from typing import Literal, NotRequired, TypedDict

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)


# ========== 状态 ==========
class OverAllState(TypedDict):
    topic: str
    content_type: Literal["poem", "joke"]
    poem: NotRequired[str]
    joke: NotRequired[str]


# ========== 节点 ==========
def router(
    state: OverAllState,
) -> Command[Literal["poem_node", "joke_node", END]]:
    """根据 content_type 返回 Command(goto=...)；Literal 只做静态检查，需兜底。"""
    content_type = state["content_type"]
    if content_type == "poem":
        return Command(goto="poem_node")
    if content_type == "joke":
        return Command(goto="joke_node")
    # 非法值：Literal 不拦运行时，直接结束
    return Command(goto=END)


def poem_node(state: OverAllState) -> dict[str, str]:
    """根据 topic 生成七言绝句。"""
    topic = state["topic"]
    content = model.invoke(
        [HumanMessage(content=f"请生成一首关于 {topic} 的七言绝句")]
    ).content
    return {"poem": str(content)}


def joke_node(state: OverAllState) -> dict[str, str]:
    """根据 topic 生成冷笑话。"""
    topic = state["topic"]
    content = model.invoke(
        [HumanMessage(content=f"请生成一个关于 {topic} 的冷笑话")]
    ).content
    return {"joke": str(content)}


# ========== 构建并编译 ==========
builder = StateGraph(state_schema=OverAllState)
builder.add_node("router", router)
builder.add_node("poem_node", poem_node)
builder.add_node("joke_node", joke_node)

builder.add_edge(START, "router")
builder.add_edge("poem_node", END)
builder.add_edge("joke_node", END)
# router → poem_node / joke_node / END 由 Command(goto=...) 在运行时决定，无需 add_edge

graph = builder.compile()


if __name__ == "__main__":
    poem_result = graph.invoke({"topic": "布偶猫", "content_type": "poem"})
    print("诗歌分支：", poem_result)

    joke_result = graph.invoke({"topic": "布偶猫", "content_type": "joke"})
    print("笑话分支：", joke_result)

    # Literal 不拦运行时非法值 → 走兜底 END
    illegal_result = graph.invoke({"topic": "布偶猫", "content_type": "illegal"})
    print("兜底分支：", illegal_result)
