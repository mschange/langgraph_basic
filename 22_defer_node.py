"""延迟节点：defer=True 让节点在常规流程全部结束后再执行。

适用：日志、审计、汇总、清理等收尾工作。
不设 defer 时 audit_node 会与业务节点并行，读不到 poem/joke。

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from typing import TypedDict

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, START, END
from loguru import logger
from rich import print as rprint

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)


# ========== 定义状态 ==========
class OverAllState(TypedDict):
    topic: str
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


def audit_node(state: OverAllState) -> OverAllState:
    """审计节点：defer=True 后在 node_a、node_b 都完成后才执行。"""
    logger.info(
        f"任务节点全部执行完毕，"
        f"诗 {'已生成' if state.get('poem') else '未生成'}，"
        f"笑话 {'已生成' if state.get('joke') else '未生成'}"
    )


# ========== 构建并编译图 ==========
builder = StateGraph(state_schema=OverAllState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)
# defer=True：被触发后不立即执行，等常规流程结束后再跑
builder.add_node("audit_node", audit_node, defer=True)

builder.add_edge(START, "node_a")
builder.add_edge(START, "node_b")
builder.add_edge(START, "audit_node")

builder.add_edge("node_a", END)
builder.add_edge("node_b", END)
builder.add_edge("audit_node", END)

graph = builder.compile()


if __name__ == "__main__":
    res = graph.invoke({"topic": "布偶狗"})
    rprint(res)
