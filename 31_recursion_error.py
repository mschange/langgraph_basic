"""被动捕获递归限制：没有通往 END 的循环，最终抛出 GraphRecursionError。

流程：START → loop_node → loop_node → ...
图内部不检查剩余步数。调用方用 try/except 接住超限异常。
"""

from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphRecursionError
from langgraph.graph import START, StateGraph
from loguru import logger


class EmptyState(TypedDict):
    pass


def loop_node(state: EmptyState, config: RunnableConfig) -> None:
    logger.info("当前执行步：{}", config["metadata"]["langgraph_step"])


builder = StateGraph(state_schema=EmptyState)
builder.add_node("loop_node", loop_node)
builder.add_edge(START, "loop_node")
builder.add_edge("loop_node", "loop_node")

graph = builder.compile()


if __name__ == "__main__":
    try:
        graph.invoke({}, config={"recursion_limit": 10})
    except GraphRecursionError as exc:
        logger.error("状态图超过递归限制：{}", exc)
    else:
        logger.info("状态图正常执行完成")
    finally:
        logger.info("本次状态图调用结束")
