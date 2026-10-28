"""TimeoutPolicy：限制异步节点单次尝试的最长耗时。

run_timeout=0.5 秒，节点 sleep 2 秒，因此抛出 NodeTimeoutError。
这里没有重试和错误处理器，异常直接抛到图外。
同步 time.sleep 不能被这种超时可靠取消。
"""

import asyncio
from typing import TypedDict

from langgraph.errors import NodeTimeoutError
from langgraph.graph import END, START, StateGraph
from langgraph.types import TimeoutPolicy


class OverallState(TypedDict, total=False):
    result: str


async def call_model(state: OverallState) -> dict[str, str]:
    print("开始调用模型")
    await asyncio.sleep(2)
    return {"result": "模型调用成功"}


builder = StateGraph(state_schema=OverallState)
builder.add_node(
    "call_model",
    call_model,
    timeout=TimeoutPolicy(run_timeout=0.5),
)
builder.add_edge(START, "call_model")
builder.add_edge("call_model", END)

graph = builder.compile()


async def main() -> None:
    try:
        await graph.ainvoke({})
    except NodeTimeoutError as error:
        print("节点执行超时：", error)


if __name__ == "__main__":
    asyncio.run(main())
