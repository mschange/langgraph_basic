"""MapReduce：Send 动态扇出（Map）+ 扇入归约（Reduce）。

流程：
START --router_map--> 多个 mapper_node 并行 --> reducer_node --> END

每个输入字符串创建一个 mapper，拆成 (单词, 1)。
entries 使用 Annotated[list, add]，多个 mapper 的列表会拼接而不是覆盖。
reducer 再按单词分组求和，得到 word_counts。
"""

from collections.abc import Sequence
from operator import add
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from loguru import logger
from rich import print as rprint


class OverAllState(TypedDict):
    """MapReduce 的整体状态。"""

    input_values: list[str]
    entries: Annotated[list[tuple[str, int]], add]
    word_counts: dict[str, int]


class MapperInputState(TypedDict):
    """mapper 的私有状态，由 Send 注入，只对 mapper_node 可见。"""

    input_value: str


def router_map(state: OverAllState) -> Sequence[Send]:
    """为每个输入字符串创建一个 mapper 任务。"""
    return [
        Send("mapper_node", {"input_value": input_value})
        for input_value in state["input_values"]
    ]


def mapper_node(state: MapperInputState) -> dict:
    """把一个字符串拆成 (单词, 1) 列表，写入 entries。"""
    entries = [(word, 1) for word in state["input_value"].split(" ")]
    return {"entries": entries}


def reducer_node(state: OverAllState) -> dict:
    """汇总全部 mapper 的 entries，统计每个单词的出现次数。"""
    entries = state["entries"]
    logger.info("reducer entries: {}", entries)

    shuffle_dict: dict[str, list[int]] = {}
    for word, count in entries:
        shuffle_dict.setdefault(word, []).append(count)
    logger.info("reducer shuffle entries: {}", shuffle_dict)

    word_counts = {word: sum(counts) for word, counts in shuffle_dict.items()}
    return {"word_counts": word_counts}


builder = StateGraph(state_schema=OverAllState)
builder.add_node("mapper_node", mapper_node)
builder.add_node("reducer_node", reducer_node)

builder.add_conditional_edges(START, router_map, path_map=["mapper_node"])
builder.add_edge("mapper_node", "reducer_node")
builder.add_edge("reducer_node", END)

graph = builder.compile()


if __name__ == "__main__":
    word_counts = graph.invoke(
        {
            "input_values": [
                "hello world",
                "hello Atguigu",
                "hello LLM",
            ]
        }
    )
    rprint(word_counts)
