"""并行静态断点与汇合：断点作用于超级步边界，不是单分支开关。

流程：
START → node_a → node_b ─┐
      → node_d → node_e ─┴→ node_c → END

编译时设置 interrupt_before/after = node_a、node_b。
第一轮停在执行前时，node_a 与 node_d 都尚未执行。
继续后同一轮内 a 与 d 一起完成，再停在执行后边界。

node_d / node_e 返回 {}，避免与同轮写 final_res 的节点冲突。
汇合边 add_edge([node_b, node_e], node_c) 表示两个上游都完成后才进入。
不需要模型或 API Key。InMemorySaver 只在当前进程有效。
"""

from typing import TypedDict
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph


class BranchState(TypedDict, total=False):
    final_res: str


def node_a(state: BranchState) -> BranchState:
    print("[节点] node_a 被执行，输入状态：", state)
    return {"final_res": "node_a 运行的中间结果"}


def node_b(state: BranchState) -> BranchState:
    print("[节点] node_b 被执行，输入状态：", state)
    return {"final_res": "node_b 运行的中间结果"}


def node_c(state: BranchState) -> BranchState:
    print("[节点] node_c 被执行，输入状态：", state)
    return {"final_res": "node_c 运行的中间结果"}


def node_d(state: BranchState) -> BranchState:
    print("[节点] node_d 被执行，输入状态：", state)
    # 同轮不写 final_res，避免与 node_a 竞争默认单值字段。
    return {}


def node_e(state: BranchState) -> BranchState:
    print("[节点] node_e 被执行，输入状态：", state)
    return {}


def build_graph() -> CompiledStateGraph:
    builder = StateGraph(state_schema=BranchState)
    builder.add_node("node_a", node_a)
    builder.add_node("node_b", node_b)
    builder.add_node("node_c", node_c)
    builder.add_node("node_d", node_d)
    builder.add_node("node_e", node_e)

    builder.add_edge(START, "node_a")
    builder.add_edge(START, "node_d")
    builder.add_edge("node_a", "node_b")
    builder.add_edge("node_d", "node_e")
    # 列表边表达两个上游节点都完成后才安排 node_c。
    builder.add_edge(["node_b", "node_e"], "node_c")
    builder.add_edge("node_c", END)

    return builder.compile(
        checkpointer=InMemorySaver(),
        interrupt_before=["node_a", "node_b"],
        interrupt_after=["node_a", "node_b"],
    )


def show_state(graph: CompiledStateGraph, config: RunnableConfig) -> None:
    snapshot = graph.get_state(config)
    print("当前 values：", snapshot.values)
    print("待执行 next：", snapshot.next)
    for task in snapshot.tasks:
        print("待执行任务：", task.name, "任务 ID：", task.id)
        print("任务中断载荷：", task.interrupts)
        print("任务错误：", task.error)


def show_history(graph: CompiledStateGraph, config: RunnableConfig) -> None:
    print("\n=== 检查点历史：较新到较旧 ===")
    for snapshot in graph.get_state_history(config):
        print("检查点 ID：", snapshot.config["configurable"]["checkpoint_id"])
        print("元信息：", snapshot.metadata)
        print("values：", snapshot.values, "next：", snapshot.next)


def main() -> None:
    graph = build_graph()
    config: RunnableConfig = {
        "configurable": {"thread_id": uuid4().hex}
    }

    print("\n=== 第一次：启动，停在第一轮之前 ===")
    result = graph.invoke({}, config=config)
    print("本次返回：", result)
    show_state(graph, config)

    print("\n=== 第二次：继续，完成 node_a 与 node_d ===")
    result = graph.invoke(None, config=config)
    print("本次返回：", result)
    show_state(graph, config)

    print("\n=== 第三次：继续，完成 node_b 与 node_e ===")
    result = graph.invoke(None, config=config)
    print("本次返回：", result)
    show_state(graph, config)

    print("\n=== 第四次：继续，完成汇合节点 node_c ===")
    result = graph.invoke(None, config=config)
    print("本次返回：", result)
    show_state(graph, config)
    show_history(graph, config)


if __name__ == "__main__":
    main()
