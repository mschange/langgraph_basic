"""重试、超时和错误处理一起用：每次尝试单独计时，耗尽后走兜底。

call_api 会睡 2 秒，但单次尝试最多 0.2 秒。
超时产生 NodeTimeoutError，RetryPolicy 允许重试，最多 3 次。
第 3 次仍超时后，error_handler 写入兜底状态并跳到 build_response。
"""

import asyncio
from typing import Literal, TypedDict

from langgraph.errors import NodeError, NodeTimeoutError
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, RetryPolicy, TimeoutPolicy


class TemporaryServiceError(Exception):
    """与超时一起列入可重试异常。本例实际触发的是超时。"""


class OverallState(TypedDict, total=False):
    status: str
    error_type: str
    final_answer: str


attempt_counter = {"count": 0}


async def call_api(state: OverallState) -> dict[str, str]:
    attempt_counter["count"] += 1
    print(f"第 {attempt_counter['count']} 次调用外部 API")
    await asyncio.sleep(2)
    return {"status": "success"}


def handle_api_error(
    state: OverallState,
    error: NodeError,
) -> Command[Literal["build_response"]]:
    error_type = type(error.error).__name__
    print(f"{error.node} 最终失败：{error_type}")
    return Command(
        update={
            "status": "fallback",
            "error_type": error_type,
        },
        goto="build_response",
    )


def build_response(state: OverallState) -> dict[str, str]:
    if state["status"] == "success":
        answer = "外部 API 调用成功。"
    else:
        answer = "外部 API 暂时不可用，已使用兜底结果。"
    return {"final_answer": answer}


builder = StateGraph(state_schema=OverallState)
builder.add_node(
    "call_api",
    call_api,
    retry_policy=RetryPolicy(
        max_attempts=3,
        initial_interval=0.1,
        backoff_factor=2.0,
        max_interval=1.0,
        jitter=False,
        retry_on=(TemporaryServiceError, NodeTimeoutError),
    ),
    timeout=TimeoutPolicy(run_timeout=0.2),
    error_handler=handle_api_error,
)
builder.add_node("build_response", build_response)

builder.add_edge(START, "call_api")
builder.add_edge("call_api", "build_response")
builder.add_edge("build_response", END)

graph = builder.compile()


async def main() -> None:
    print(await graph.ainvoke({}))


if __name__ == "__main__":
    asyncio.run(main())
