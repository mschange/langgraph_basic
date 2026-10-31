"""检查点分叉：在 router_node 执行前改写输入，从那一点开一条新分支。

update_state(..., as_node=START) 不重跑 START。
新的 user_input 会留给后继节点，因此 router_node 会按笑话请求重新路由。
原来的历史检查点保持不变。

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from typing import Literal, NotRequired, TypedDict

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from loguru import logger
from pydantic import BaseModel, Field

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)


class RouteDecision(BaseModel):
    """根据用户输入判断应该路由到哪个任务。"""

    mode: Literal["poem", "joke", "default"] = Field(
        description="任务类型：poem=写诗，joke=笑话，default=其他"
    )
    topic: str = Field(description="提取的主题关键词")


model_with_structure = model.with_structured_output(RouteDecision)


class OverAllState(TypedDict):
    username: str
    user_input: str
    mode: NotRequired[str]
    topic: NotRequired[str]
    output: NotRequired[str]


def router_node(state: OverAllState) -> dict[str, str]:
    """把用户输入解析成 mode 和 topic。这两个字段必须写回图状态。"""
    logger.info("路由节点已执行")
    decision = model_with_structure.invoke([HumanMessage(state["user_input"])])
    logger.info("路由结果-res: {}", decision)
    return {"mode": decision.mode, "topic": decision.topic}


def router(state: OverAllState) -> Literal["node_poem", "node_joke", "node_default"]:
    logger.info("路由函数已执行")
    if state["mode"] == "poem":
        logger.info("路由至 node_poem 节点")
        return "node_poem"
    if state["mode"] == "joke":
        logger.info("路由至 node_joke 节点")
        return "node_joke"
    logger.info("路由至兜底节点")
    return "node_default"


def node_poem(state: OverAllState) -> dict[str, str]:
    logger.info("node_poem 已执行")
    poem = model.invoke(
        [HumanMessage(f"写一首关于 {state['topic']} 的七言绝句，不要赏析，只给诗句即可")]
    ).content
    return {"output": str(poem)}


def node_joke(state: OverAllState) -> dict[str, str]:
    logger.info("node_joke 已执行")
    joke = model.invoke(
        [HumanMessage(f"写一个关于 {state['topic']} 的笑话，尽可能简单，不超过一百字")]
    ).content
    return {"output": str(joke)}


def node_default(state: OverAllState) -> dict[str, str]:
    logger.info("node_default 已执行")
    return {"output": "无法处理的任务类型"}


builder = StateGraph(state_schema=OverAllState)
builder.add_node("router_node", router_node)
builder.add_node("node_poem", node_poem)
builder.add_node("node_joke", node_joke)
builder.add_node("node_default", node_default)
builder.add_edge(START, "router_node")
builder.add_conditional_edges(
    "router_node",
    router,
    path_map=["node_poem", "node_joke", "node_default"],
)
builder.add_edge("node_poem", END)
builder.add_edge("node_joke", END)
builder.add_edge("node_default", END)

graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "123"}}


if __name__ == "__main__":
    result = graph.invoke(
        {
            "username": "小黄",
            "user_input": "帮我写一首关于布偶猫的七言绝句",
        },
        config=config,
    )
    print("首次运行结果:", result)

    history = list(graph.get_state_history(config))
    before_router = next(
        (item for item in history if item.next == ("router_node",)),
        None,
    )
    if before_router is None:
        logger.error("没有找到 router_node 执行前的检查点")
    else:
        logger.info("找到 router_node 执行前的检查点，开始 Fork")
        forked_config = graph.update_state(
            config=before_router.config,
            values={"user_input": "帮我写一个关于布偶猫的笑话"},
            as_node=START,
        )
        forked = graph.invoke(None, forked_config)
        print("Fork 运行结果:", forked)
