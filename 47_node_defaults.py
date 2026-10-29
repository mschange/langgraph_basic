"""全图默认配置：set_node_defaults 统一重试、缓存、超时和错误处理。

process_value 不单独配置，全部使用图级默认值。
build_summary 只把超时改成 0.05 秒，其余策略仍继承默认值。节点级配置优先。

四次调用：
  1. ConnectionError 重试后成功
  2. 相同输入，两个节点都命中缓存
  3. ValueError 不重试，错误处理器跳到 build_summary
  4. 等待超过默认 0.1 秒，超时后同样走错误处理器
"""

import asyncio
from typing import Literal, TypedDict

from langgraph.cache.memory import InMemoryCache
from langgraph.errors import NodeError
from langgraph.graph import END, START, StateGraph
from langgraph.types import CachePolicy, Command, RetryPolicy, TimeoutPolicy
from loguru import logger


class WorkflowState(TypedDict, total=False):
    value: int
    delay_seconds: float
    force_error: bool
    result: int
    status: str
    error_type: str
    summary: str


execution_count = {"process_value": 0, "build_summary": 0}


async def process_value(state: WorkflowState) -> dict:
    execution_count["process_value"] += 1
    current_attempt = execution_count["process_value"]
    logger.info("process_value 第 {} 次实际执行", current_attempt)

    await asyncio.sleep(state.get("delay_seconds", 0.01))

    if state.get("force_error", False):
        raise ValueError("输入要求模拟不可重试错误")

    if current_attempt == 1:
        raise ConnectionError("模拟临时网络故障")

    return {
        "result": state["value"] * 2,
        "status": "success",
    }


async def build_summary(state: WorkflowState) -> dict[str, str]:
    execution_count["build_summary"] += 1
    logger.info(
        "build_summary 第 {} 次实际执行",
        execution_count["build_summary"],
    )
    return {
        "summary": (
            f"status={state['status']}, "
            f"result={state.get('result', '无')}, "
            f"error={state.get('error_type', '无')}"
        )
    }


async def handle_node_error(
    state: WorkflowState,
    error: NodeError,
) -> Command[Literal["build_summary"]]:
    logger.info("默认错误处理器捕获到 {}", type(error.error).__name__)
    return Command(
        update={
            "status": "fallback",
            "error_type": type(error.error).__name__,
        },
        goto="build_summary",
    )


builder = StateGraph(state_schema=WorkflowState)
builder.set_node_defaults(
    retry_policy=RetryPolicy(
        max_attempts=2,
        initial_interval=0.05,
        jitter=False,
        retry_on=(ConnectionError,),
    ),
    cache_policy=CachePolicy(ttl=60),
    timeout=TimeoutPolicy(run_timeout=0.1),
    error_handler=handle_node_error,
)
builder.add_node("process_value", process_value)
builder.add_node(
    "build_summary",
    build_summary,
    timeout=TimeoutPolicy(run_timeout=0.05),
)
builder.add_edge(START, "process_value")
builder.add_edge("process_value", "build_summary")
builder.add_edge("build_summary", END)

graph = builder.compile(cache=InMemoryCache())


async def main() -> None:
    normal_input: WorkflowState = {
        "value": 5,
        "delay_seconds": 0.01,
        "force_error": False,
    }

    logger.info("第一次调用：先发生 ConnectionError，然后由默认策略重试成功")
    first_result = await graph.ainvoke(normal_input)

    logger.info("第二次调用：输入相同，两个普通节点直接读取缓存")
    second_result = await graph.ainvoke(normal_input)

    logger.info("第三次调用：ValueError 不重试，由默认错误处理器恢复")
    error_result = await graph.ainvoke(
        {
            "value": 5,
            "delay_seconds": 0.01,
            "force_error": True,
        }
    )

    logger.info("第四次调用：节点超过默认 0.1 秒限制，由默认错误处理器恢复")
    timeout_result = await graph.ainvoke(
        {
            "value": 8,
            "delay_seconds": 0.2,
            "force_error": False,
        }
    )

    print("首次成功结果：", first_result)
    print("缓存命中结果：", second_result)
    print("错误恢复结果：", error_result)
    print("超时恢复结果：", timeout_result)
    print("节点实际执行次数：", execution_count)

    assert first_result == second_result
    assert first_result["result"] == 10
    assert error_result["error_type"] == "ValueError"
    assert timeout_result["error_type"] == "NodeTimeoutError"
    assert execution_count == {"process_value": 4, "build_summary": 3}


if __name__ == "__main__":
    asyncio.run(main())
