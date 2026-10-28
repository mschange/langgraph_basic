"""RetryPolicy：临时异常按次数重试，第三次调用成功。

max_attempts=3 表示总共最多执行 3 次，包含第一次。
jitter=False 时退避是确定的：失败后先等 0.2 秒，再等 0.4 秒。
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy


class TemporaryServiceError(Exception):
    """模拟可自行恢复的外部服务错误。"""


class OverallState(TypedDict, total=False):
    result: str


attempt_counter = {"count": 0}


def call_api(state: OverallState) -> dict[str, str]:
    attempt_counter["count"] += 1
    current_attempt = attempt_counter["count"]
    print(f"第 {current_attempt} 次调用")

    if current_attempt < 3:
        raise TemporaryServiceError("外部服务暂时不可用")
    return {"result": "调用成功"}


builder = StateGraph(state_schema=OverallState)
builder.add_node(
    "call_api",
    call_api,
    retry_policy=RetryPolicy(
        max_attempts=3,
        initial_interval=0.2,
        backoff_factor=2.0,
        max_interval=1.0,
        jitter=False,
        retry_on=TemporaryServiceError,
    ),
)
builder.add_edge(START, "call_api")
builder.add_edge("call_api", END)

graph = builder.compile()


if __name__ == "__main__":
    print(graph.invoke({}))
