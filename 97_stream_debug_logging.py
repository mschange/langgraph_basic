"""流式输出 debug（结构化日志）：裁剪字段后 JSON 落盘式打印。

流程：
START → node_a → node_b → END

只保留 step / ts / type 及关键字段，避免完整快照撑爆日志。
需要 checkpointer + thread_id。不需要模型或 API Key。
"""

import json
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph


class SimpleState(TypedDict):
    initial_state: str
    node_a_output: str
    node_b_output: str


def node_a(state: SimpleState) -> SimpleState:
    return {"node_a_output": "节点A的输出"}


def node_b(state: SimpleState) -> SimpleState:
    return {"node_b_output": "节点B的输出"}


builder = StateGraph(state_schema=SimpleState)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)
builder.add_edge(START, "node_a")
builder.add_edge("node_a", "node_b")
builder.add_edge("node_b", END)

graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "log-1"}}


if __name__ == "__main__":
    for mode, event in graph.stream(
        {"initial_state": "初始状态"},
        stream_mode=["debug"],
        config=config,
    ):
        payload = event["payload"]
        log = {
            "step": event["step"],
            "ts": event["timestamp"],
            "type": event["type"],
        }
        if event["type"] == "task":
            log |= {"node": payload["name"], "triggers": payload["triggers"]}
        elif event["type"] == "task_result":
            log |= {
                "node": payload["name"],
                "error": payload["error"],
                "interrupted": bool(payload["interrupts"]),
            }
        elif event["type"] == "checkpoint":
            log |= {"next": payload["next"]}
        print(json.dumps(log, ensure_ascii=False, default=str))
