"""短期记忆配置：节点通过 config 读取 thread_id、递归限制和自定义元数据。

编译时传入 checkpointer，调用时传入 config。
config 由运行时按参数名注入，不需要放进图状态。
"""

from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from loguru import logger


class OverAllState(TypedDict):
    user_input: str
    output: str


def process_node(state: OverAllState, config: RunnableConfig) -> dict[str, str]:
    thread_id = config["configurable"]["thread_id"]
    recursion_limit = config.get("recursion_limit", "未设置")
    metadata = config.get("metadata", {})

    logger.info("thread_id: {}", thread_id)
    logger.info("recursion_limit: {}", recursion_limit)
    logger.info("metadata: {}", metadata)
    return {"output": f"[thread={thread_id}] 处理了: {state['user_input']}"}


builder = StateGraph(state_schema=OverAllState)
builder.add_node("process_node", process_node)
builder.add_edge(START, "process_node")
builder.add_edge("process_node", END)

graph = builder.compile(checkpointer=InMemorySaver())
config = {
    "configurable": {"thread_id": "config-demo-001"},
    "metadata": {"source": "unit_test", "version": "1.0"},
}


if __name__ == "__main__":
    result = graph.invoke({"user_input": "你好世界"}, config=config)
    print(result["output"])
