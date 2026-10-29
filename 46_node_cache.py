"""节点缓存：相同输入跳过节点函数，不同输入重新计算。

CachePolicy 只声明怎么缓存，compile(cache=InMemoryCache()) 才提供存储。
InMemoryCache 只活在当前进程里。ttl=60 表示结果保留 60 秒。

三次调用里前两次输入相同，normalize_text 实际只执行两次。
"""

from typing import TypedDict

from langgraph.cache.memory import InMemoryCache
from langgraph.graph import END, START, StateGraph
from langgraph.types import CachePolicy
from loguru import logger


class CacheState(TypedDict, total=False):
    text: str
    normalized_text: str


execution_count = 0


def normalize_text(state: CacheState) -> dict[str, str]:
    global execution_count
    execution_count += 1
    logger.info("normalize_text 第 {} 次实际执行", execution_count)
    return {"normalized_text": state["text"].strip().upper()}


builder = StateGraph(state_schema=CacheState)
builder.add_node(
    "normalize_text",
    normalize_text,
    cache_policy=CachePolicy(ttl=60),
)
builder.add_edge(START, "normalize_text")
builder.add_edge("normalize_text", END)

graph = builder.compile(cache=InMemoryCache())


def main() -> None:
    logger.info("第一次调用：输入尚未缓存，节点会实际执行")
    first_result = graph.invoke({"text": "  langgraph cache  "})

    logger.info("第二次调用：输入完全相同，直接复用第一次的节点结果")
    second_result = graph.invoke({"text": "  langgraph cache  "})

    logger.info("第三次调用：输入发生变化，因此需要重新执行节点")
    third_result = graph.invoke({"text": "  another input  "})

    print("第一次结果：", first_result)
    print("第二次结果：", second_result)
    print("第三次结果：", third_result)
    print("节点实际执行次数：", execution_count)

    assert first_result == second_result
    assert first_result["normalized_text"] == "LANGGRAPH CACHE"
    assert third_result["normalized_text"] == "ANOTHER INPUT"
    assert execution_count == 2


if __name__ == "__main__":
    main()
