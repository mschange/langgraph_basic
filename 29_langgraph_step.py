"""执行步编号：线性图里通过 RunnableConfig 读取 langgraph_step。

流程：START → node_a → node_b → node_c → END
预期日志：1、2、3。节点不更新业务状态，返回 None。
"""

from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from loguru import logger


class EmptyState(TypedDict):
    """没有需要在节点之间传递的业务字段。"""

    pass


def node_a(state: EmptyState, config: RunnableConfig) -> None:
    logger.info(config["metadata"]["langgraph_step"])


def node_b(state: EmptyState, config: RunnableConfig) -> None:
    logger.info(config["metadata"]["langgraph_step"])


def node_c(state: EmptyState, config: RunnableConfig) -> None:
    logger.info(config["metadata"]["langgraph_step"])


builder = StateGraph(state_schema=EmptyState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)
builder.add_node("node_c", node_c)

builder.add_edge(START, "node_a")
builder.add_edge("node_a", "node_b")
builder.add_edge("node_b", "node_c")
builder.add_edge("node_c", END)

graph = builder.compile()


if __name__ == "__main__":
    graph.invoke({})
