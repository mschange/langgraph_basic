"""主动终止循环：用 RemainingSteps 在撞上递归上限之前结束。

流程：START → loop_node → router
  remaining_steps < 3 → END
  否则回到 loop_node

remaining_steps 由框架根据 recursion_limit 注入，调用时不用传入。
"""

from typing import Literal, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.managed import RemainingSteps
from loguru import logger


class OverAllState(TypedDict):
    remaining_steps: RemainingSteps


def loop_node(state: OverAllState, config: RunnableConfig) -> None:
    logger.info(
        "loop_node, current_step: {}, remaining_steps: {}",
        config["metadata"]["langgraph_step"],
        state["remaining_steps"],
    )


def router(state: OverAllState) -> Literal["loop_node", END]:
    remaining_steps = state["remaining_steps"]
    if remaining_steps < 3:
        logger.info(
            "当前剩余步数为 {}，不足 3 步，主动终止运行图",
            remaining_steps,
        )
        return END
    return "loop_node"


builder = StateGraph(state_schema=OverAllState)
builder.add_node("loop_node", loop_node)
builder.add_edge(START, "loop_node")
builder.add_conditional_edges("loop_node", router)

graph = builder.compile()


if __name__ == "__main__":
    graph.invoke({}, config={"recursion_limit": 10})
