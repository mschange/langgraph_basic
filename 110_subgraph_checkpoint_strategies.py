"""子图检查点策略：挂载子图 + interrupt，对比三种 compile 方式。

流程：
父图 START → subgraph_node → END
子图 START → strip → punctuate(两次 interrupt) → END

策略：
  per_invocation = compile()              # 默认可恢复，不跨调用
  per_thread     = compile(checkpointer=True)
  stateless      = compile(checkpointer=False)  # interrupt 不可恢复

用法：python 110_subgraph_checkpoint_strategies.py [per_invocation|per_thread|stateless]
不需要模型或 API Key。
"""

import sys
from typing import TypedDict

from loguru import logger

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

logger.remove()
logger.add(sys.stdout, colorize=True)


class OverAllState(TypedDict):
    raw_text: str
    cleaned_text: str


def subgraph_strip_node(state: OverAllState) -> OverAllState:
    logger.info("[子图] subgraph_strip_node 执行")
    return {"cleaned_text": state["raw_text"].strip()}


def subgraph_punctuate_node(state: OverAllState) -> OverAllState:
    logger.info("[子图] subgraph_punctuate_node 执行")

    punctuation = interrupt("您希望在句尾添加的第一个标点符号是？[。/，/！/？/；]")
    punctuation_2 = interrupt("您希望在句尾添加的第二个标点符号是？[。/，/！/？/；]")

    return {"cleaned_text": state["cleaned_text"] + punctuation + punctuation_2}


def build_parent(strategy: str):
    sub_builder = StateGraph(state_schema=OverAllState)
    sub_builder.add_node("subgraph_strip_node", subgraph_strip_node)
    sub_builder.add_node("subgraph_punctuate_node", subgraph_punctuate_node)
    sub_builder.add_edge(START, "subgraph_strip_node")
    sub_builder.add_edge("subgraph_strip_node", "subgraph_punctuate_node")
    sub_builder.add_edge("subgraph_punctuate_node", END)

    if strategy == "per_invocation":
        subgraph = sub_builder.compile()
    elif strategy == "per_thread":
        subgraph = sub_builder.compile(checkpointer=True)
    elif strategy == "stateless":
        subgraph = sub_builder.compile(checkpointer=False)
    else:
        raise ValueError(f"未知策略：{strategy}")

    parent_builder = StateGraph(state_schema=OverAllState)
    parent_builder.add_node("subgraph_node", subgraph)
    parent_builder.add_edge(START, "subgraph_node")
    parent_builder.add_edge("subgraph_node", END)

    return parent_builder.compile(checkpointer=InMemorySaver())


if __name__ == "__main__":
    STRATEGY = sys.argv[1] if len(sys.argv) > 1 else "per_invocation"
    parent_graph = build_parent(STRATEGY)
    config = {"configurable": {"thread_id": f"strategy-{STRATEGY}"}}

    print(f"========== 策略：{STRATEGY} ==========")
    first_result = parent_graph.invoke(
        {"raw_text": "   LangGraph 真有意思        "},
        config=config,
    )
    print("首次调用返回：", first_result)

    second_result = parent_graph.invoke(Command(resume="！"), config=config)
    print("第一次恢复返回：", second_result)

    final_result = parent_graph.invoke(Command(resume="。"), config=config)
    print("第二次恢复返回：", final_result)
    print("最终 cleaned_text：", final_result.get("cleaned_text"))
