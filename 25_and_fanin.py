"""“与”触发的扇入：下游节点等所有上游分支都完成后才执行。

流程图：
START → node_a → node_b → node_d ┐
              └→ node_c ─────────┴→ node_e

关键写法：add_edge(["node_c", "node_d"], "node_e")
预期超步：1 node_a → 2 node_b、node_c → 3 node_d → 4 node_e
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
    """由 node_a 触发，与 node_b 并行，是 node_e 的上游之一。"""
    cur_step = config["metadata"]["langgraph_step"]
    logger.info("cur_step: {}, node_c 被触发", cur_step)
    return {}


def node_d(state: EmptyState, config: RunnableConfig) -> EmptyState:
    """由 node_b 触发，是 node_e 的另一个上游。"""
    cur_step = config["metadata"]["langgraph_step"]
    logger.info("cur_step: {}, node_d 被触发", cur_step)
    return {}


def node_e(state: EmptyState, config: RunnableConfig) -> EmptyState:
    """汇聚节点：node_c 和 node_d 都完成后才触发。"""
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
# 列表表示“与”：必须全部到达后才触发下游
builder.add_edge(["node_c", "node_d"], "node_e")

graph = builder.compile()


if __name__ == "__main__":
    graph.invoke({})
