"""错误处理器：重试耗尽后用 NodeError 读取失败信息，再 Command 恢复流程。

call_api 每次都失败。max_attempts=3 用完后进入 handle_api_error。
错误处理器不会自动沿 call_api 的出边继续，所以用 Command(goto=...) 跳到 build_response。
"""

from typing import Literal, TypedDict

from langgraph.errors import NodeError
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, RetryPolicy


class TemporaryServiceError(Exception):
    """模拟可重试、但本次始终无法恢复的外部错误。"""


class OverallState(TypedDict, total=False):
    status: str
    error_message: str
    final_answer: str


attempt_counter = {"count": 0}


def call_api(state: OverallState) -> dict[str, str]:
    attempt_counter["count"] += 1
    print(f"第 {attempt_counter['count']} 次调用 API")
    raise TemporaryServiceError("API 暂时不可用")


def handle_api_error(
    state: OverallState,
    error: NodeError,
) -> Command[Literal["build_response"]]:
    print(f"失败节点：{error.node}")
    print(f"异常类型：{type(error.error).__name__}")
    return Command(
        update={
            "status": "fallback",
            "error_message": str(error.error),
        },
        goto="build_response",
    )


def build_response(state: OverallState) -> dict[str, str]:
    return {"final_answer": "外部服务暂时不可用，已返回本地兜底结果。"}


builder = StateGraph(state_schema=OverallState)
builder.add_node(
    "call_api",
    call_api,
    retry_policy=RetryPolicy(
        max_attempts=3,
        initial_interval=0.2,
        jitter=False,
        retry_on=TemporaryServiceError,
    ),
    error_handler=handle_api_error,
)
builder.add_node("build_response", build_response)
builder.add_edge(START, "call_api")
builder.add_edge("call_api", "build_response")
builder.add_edge("build_response", END)

graph = builder.compile()


if __name__ == "__main__":
    print(graph.invoke({}))
