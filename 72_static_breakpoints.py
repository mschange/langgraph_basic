"""静态断点与配置作用域：compiled / repeated / omitted 三种传参方式。

流程：
START → node_a → node_b → node_c → END

interrupt_before / interrupt_after 在调度层暂停，节点函数内不调用 interrupt()。
三种模式各自新建图、存储器与 thread_id，互不共享进度。

- compiled：compile 时设默认断点，后续 invoke 省略仍继承
- repeated：四次 invoke 都显式传入相同 before/after
- omitted：前两次显式传入，后两次省略后连续跑完剩余节点

用 invoke(None, config) 从检查点继续。不需要模型或 API Key。
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Literal, TypedDict, cast
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

# 三种模式名称也用于命令行；Literal 限定程序内部的有效取值。
Mode = Literal["compiled", "repeated", "omitted"]


class GraphState(TypedDict, total=False):
    # total=False 允许初次输入为 {}，尚未执行节点时没有此字段。
    # 不使用 Annotated 或 reducer：后续节点的字符串覆盖前面的值。
    final_res: str


def node_a(state: GraphState) -> dict[str, str]:
    """普通节点：打印入口状态，然后返回局部状态更新。"""
    print(f"  执行 node_a，输入状态：{state}")
    return {"final_res": "node_a 完成"}


def node_b(state: GraphState) -> dict[str, str]:
    """串行执行时会读取 node_a 已更新的状态。"""
    print(f"  执行 node_b，输入状态：{state}")
    return {"final_res": "node_b 完成"}


def node_c(state: GraphState) -> dict[str, str]:
    """最后一个节点覆盖 final_res，并沿边进入 END。"""
    print(f"  执行 node_c，输入状态：{state}")
    return {"final_res": "node_c 完成"}


def build_graph(compiled_breakpoints: bool = False) -> CompiledStateGraph:
    """每次调用都创建新的图和内存存储器，不共享执行历史。"""
    builder = StateGraph(state_schema=GraphState)
    builder.add_node("node_a", node_a)
    builder.add_node("node_b", node_b)
    builder.add_node("node_c", node_c)
    builder.add_edge(START, "node_a")
    builder.add_edge("node_a", "node_b")
    builder.add_edge("node_b", "node_c")
    builder.add_edge("node_c", END)

    checkpointer = InMemorySaver()
    if compiled_breakpoints:
        # 这里设置的是编译默认值，invoke 省略相应参数时仍然使用。
        return builder.compile(
            checkpointer=checkpointer,
            interrupt_before=["node_a", "node_b"],
            interrupt_after=["node_a", "node_b"],
        )
    # 其余模式没有编译断点默认值，是否暂停由本次 invoke 的选项决定。
    return builder.compile(checkpointer=checkpointer)


def print_latest(graph: CompiledStateGraph, config: RunnableConfig) -> None:
    """读取已保存的快照；不要只靠 invoke 返回值判断执行位置。"""
    latest = graph.get_state(config)
    print(f"  latest.values = {latest.values!r}")
    print(f"  latest.next = {latest.next!r}")
    print("  latest.tasks（任务名与中断信息）：")
    for task in latest.tasks:
        # 静态暂停时 interrupts 为空，不存在需要回答的动态载荷。
        print(f"    name={task.name!r}, interrupts={task.interrupts!r}")
    if not latest.tasks:
        print("    ()")


def print_history(graph: CompiledStateGraph, config: RunnableConfig) -> None:
    """历史按新到旧输出；记录执行状态，不代表 invoke 调用计数。"""
    print("\n  checkpoint history（新 → 旧）：")
    for snapshot in graph.get_state_history(config):
        metadata = snapshot.metadata or {}
        checkpoint_id = snapshot.config.get("configurable", {}).get(
            "checkpoint_id"
        )
        print(
            f"    step={metadata.get('step')!r}, "
            f"source={metadata.get('source')!r}, "
            f"checkpoint_id={checkpoint_id!r}, "
            f"values={snapshot.values!r}, next={snapshot.next!r}"
        )


def run_mode(mode: Literal["compiled", "repeated", "omitted"]) -> None:
    """同一模式内固定线程 ID，四次 invoke 依次启动、继续、继续、继续。"""
    graph = build_graph(compiled_breakpoints=(mode == "compiled"))
    # uuid4 为本次模式生成独立会话；不能在四次调用之间重新生成。
    config: RunnableConfig = {
        "configurable": {"thread_id": f"{mode}-{uuid4().hex}"}
    }
    print(f"\n{'=' * 16} mode={mode} {'=' * 16}")
    print(f"thread_id={config['configurable']['thread_id']}")

    for call_no in range(1, 5):
        # {} 是初次输入；None 表示沿这个线程的已有检查点继续。
        input_value: dict[str, str] | None = {} if call_no == 1 else None
        runtime_breakpoints = mode == "repeated" or (
            mode == "omitted" and call_no <= 2
        )
        print(f"\n第 {call_no} 次 invoke，input={input_value!r}")
        if runtime_breakpoints:
            # repeated 四次都传；omitted 只有前两次传。
            print("  本次显式设置 before/after = ['node_a', 'node_b']")
            result = graph.invoke(
                input_value,
                config=config,
                interrupt_before=["node_a", "node_b"],
                interrupt_after=["node_a", "node_b"],
            )
        else:
            # 真正省略断点关键字，不用空列表替代省略。
            print("  本次省略运行时断点参数")
            result = graph.invoke(input_value, config=config)
        print(f"  invoke 返回 = {result!r}")
        print_latest(graph, config)

    # 四次调用结束后展示此线程的全部检查点历史。
    print_history(graph, config)


def main(args: Sequence[str] | None = None) -> None:
    """args=None 时解析终端参数，也允许直接传入参数序列。"""
    parser = argparse.ArgumentParser(description="LangGraph 静态断点作用域演示")
    parser.add_argument(
        "--mode",
        choices=["all", "compiled", "repeated", "omitted"],
        default="all",
        help="all 依次运行三个独立模式；默认 all",
    )
    parsed = parser.parse_args(args)
    # choices 已限制取值；cast 仅用于类型提示，不改变运行时行为。
    modes: tuple[Mode, ...] = (
        ("compiled", "repeated", "omitted")
        if parsed.mode == "all"
        else (cast(Mode, parsed.mode),)
    )
    for mode in modes:
        run_mode(mode)


if __name__ == "__main__":
    main()
