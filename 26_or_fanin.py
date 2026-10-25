"""“或”触发的扇入：任意一个上游分支到达即可触发下游节点。

图的形状与“与”触发相同，区别在边的写法：
分别 add_edge("node_c", "node_e") 和 add_edge("node_d", "node_e")。

每条边都会独立触发一次 node_e：
  1 node_a
  2 node_b、node_c
  3 node_d、node_e（node_c 完成后立即触发，不必等 node_d）
  4 node_e（node_d 完成后再次触发）
"""

from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, StateGraph
from loguru import logger


class EmptyState(TypedDict):
    """本例只观察执行顺序，不传递数据。"""

    pass


def node_a(state: EmptyState, config: RunnableConfig) -> EmptyState:
    """入口节点，从 START 进入。"""
    cur_step = config["metadata"]["langgraph_step"]
    logger.info("cur_step: {}, node_a 被触发", cur_step)
    return {}


def node_b(state: EmptyState, config: RunnableConfig) -> EmptyState:
    """由 node_a 触发，与 node_c 并行。"""
    cur_step = config["metadata"]["langgraph_step"]
    logger.info("cur_step: {}, node_b 被触发", cur_step)
    return {}


def node_c(state: EmptyState, config: RunnableConfig) -> EmptyState:
    """由 node_a 触发，与 node_b 并行，完成后可单独触发 node_e。"""
    cur_step = config["metadata"]["langgraph_step"]
    logger.info("cur_step: {}, node_c 被触发", cur_step)
    return {}


def node_d(state: EmptyState, config: RunnableConfig) -> EmptyState:
    """由 node_b 触发，完成后也可单独触发 node_e。"""
    cur_step = config["metadata"]["langgraph_step"]
    logger.info("cur_step: {}, node_d 被触发", cur_step)
    return {}


def node_e(state: EmptyState, config: RunnableConfig) -> EmptyState:
    """汇聚节点：node_c 或 node_d 任一完成即可触发。"""
    cur_step = config["metadata"]["langgraph_step"]
    logger.info("cur_step: {}, node_e 被触发", cur_step)
    return {}


builder = StateGraph(state_schema=EmptyState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)
builder.add_node("node_c", node_c)
builder.add_node("node_d", node_d)
builder.add_node("node_e", node_e)

builder.add_edge(START, "node_a")
builder.add_edge("node_a", "node_b")
builder.add_edge("node_a", "node_c")
builder.add_edge("node_b", "node_d")
# 两条独立的边：每条都可以单独触发 node_e
builder.add_edge("node_c", "node_e")
builder.add_edge("node_d", "node_e")

graph = builder.compile()


if __name__ == "__main__":
    graph.invoke({})
