"""流式输出 checkpoints（审批流）：updates 取中断内容，checkpoints 看 next。

流程：
START → prepare (interrupt 审批) → execute → END

中断通知在 updates 的 __interrupt__；审批结果经 Command(resume=bool) 交回。
不需要模型或 API Key。
"""

from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class ApprovalState(TypedDict, total=False):
    action: str
    approved: bool
    result: str


def prepare(state: ApprovalState) -> ApprovalState:
    decision = interrupt(
        {"question": "是否执行该操作？", "action": state["action"]}
    )
    return {"approved": bool(decision)}


def execute(state: ApprovalState) -> ApprovalState:
    if not state.get("approved"):
        return {"result": "已拒绝，未执行"}
    return {"result": f"已执行：{state['action']}"}


builder = StateGraph(state_schema=ApprovalState)
builder.add_node("prepare", prepare)
builder.add_node("execute", execute)
builder.add_edge(START, "prepare")
builder.add_edge("prepare", "execute")
builder.add_edge("execute", END)

graph = builder.compile(checkpointer=InMemorySaver())


def run_until_interrupt(thread_id: str, action: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    for mode, data in graph.stream(
        {"action": action},
        stream_mode=["updates", "checkpoints"],
        config=config,
    ):
        if mode == "updates" and "__interrupt__" in data:
            print("需要审批:", data["__interrupt__"][0].value)
    return config


def resume_with(config: dict, decision: bool) -> None:
    for mode, data in graph.stream(
        Command(resume=decision),
        stream_mode=["updates", "checkpoints"],
        config=config,
    ):
        pass
    snapshot = graph.get_state(config)
    print("next:", snapshot.next)
    print("最终结果:", snapshot.values["result"])


if __name__ == "__main__":
    cfg = run_until_interrupt("t-1", "删除日志文件")
    resume_with(cfg, decision=True)

    print("---")
    cfg2 = run_until_interrupt("t-2", "删除日志文件")
    resume_with(cfg2, decision=False)
