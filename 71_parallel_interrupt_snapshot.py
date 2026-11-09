"""并行动态中断与历史快照：姓名和年龄分支同时暂停，按中断 ID 恢复。

流程：
START → name_node → END
      → age_node  → END

两个节点在同一 superstep 调度，彼此没有依赖边。
终端依次 input() 只是收集反馈，不会把图改成先姓名后年龄。
恢复映射的键是 Interrupt.id，不是 field 名或列表下标。

每次 invoke 后打印最新状态视图和从新到旧的历史快照。
待回答问题只来自本轮 __interrupt__，不从历史 tasks 汇总。
不需要模型或 API Key。InMemorySaver 只在当前进程有效。
"""

from collections.abc import Sequence
from typing import TypedDict
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, Interrupt, interrupt


class ProfileState(TypedDict, total=False):
    """两个字段均可暂时缺失；初次执行可以传入空字典。"""

    username: str
    age: int


def name_node(state: ProfileState) -> ProfileState:
    """暂停收集姓名，只更新姓名通道。"""
    username = interrupt({
        "field": "username",
        "prompt": "请输入姓名（不能为空）：",
    })
    # 恢复时从节点开头重跑；匹配的回答成为 interrupt() 的返回值。
    if not isinstance(username, str) or not username.strip():
        raise ValueError("姓名必须是非空字符串")
    return {"username": username.strip()}


def age_node(state: ProfileState) -> ProfileState:
    """暂停收集年龄，只更新年龄通道。"""
    age = interrupt({
        "field": "age",
        "prompt": "请输入年龄（非负整数）：",
    })
    # bool 是 int 的子类，需额外排除，避免把 True 当作年龄 1。
    if isinstance(age, bool) or not isinstance(age, int) or age < 0:
        raise ValueError("年龄必须是非负整数")
    return {"age": age}


def build_graph() -> CompiledStateGraph:
    """建立两个并行分支，并为这一个图实例配置内存检查点。"""
    builder = StateGraph(state_schema=ProfileState)
    builder.add_node("name_node", name_node)
    builder.add_node("age_node", age_node)
    builder.add_edge(START, "name_node")
    builder.add_edge(START, "age_node")
    builder.add_edge("name_node", END)
    builder.add_edge("age_node", END)
    return builder.compile(checkpointer=InMemorySaver())


def read_age(prompt: str) -> int:
    """在本地重复读取，直到得到非负整数；不会提交无效回答。"""
    while True:
        raw = input(prompt).strip()
        try:
            age = int(raw)
        except ValueError:
            print("请输入整数，例如 0 或 18；不能输入小数或空字符串。")
            continue
        if age < 0:
            print("年龄不能为负数，请重新输入。")
            continue
        return age


def collect_resume_map(pending: Sequence[Interrupt]) -> dict[str, str | int]:
    """按结构化字段选择读取方式，按真实中断 ID 绑定回答。"""
    resume_map: dict[str, str | int] = {}
    for item in pending:
        payload = item.value
        if not isinstance(payload, dict):
            raise ValueError("中断 payload 必须是字典")
        field = payload.get("field")
        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("中断 payload 缺少有效 prompt")
        print(f"\n回答问题：field={field!r}, interrupt_id={item.id}")
        if field == "username":
            while True:
                username = input(prompt).strip()
                if username:
                    break
                print("姓名不能为空，请重新输入。")
            resume_map[item.id] = username
        elif field == "age":
            resume_map[item.id] = read_age(prompt)
        else:
            raise ValueError(f"不支持的中断字段：{field!r}")
    return resume_map


def show_state_and_history(
    graph: CompiledStateGraph, config: RunnableConfig
) -> None:
    """分开打印最新视图和倒序历史；历史任务不用于生成待回答问题。"""
    latest = graph.get_state(config)
    print("\n=== 最新状态视图 ===")
    print(f"values={latest.values!r}")
    print(f"next={latest.next!r}")
    print(f"checkpoint_id={latest.config.get('configurable', {}).get('checkpoint_id')!r}")
    print("tasks（诊断记录；interrupts 不一定全部仍在等待）：")
    if not latest.tasks:
        print("  （无任务）")
    for task in latest.tasks:
        print(f"  name={task.name!r}, id={task.id!r}, error={task.error!r}")
        print(f"    result={task.result!r}, 位于 next={task.name in latest.next}")
        for item in task.interrupts:
            print(f"    interrupt id={item.id!r}, value={item.value!r}")
        if not task.interrupts:
            print("    interrupts=()")

    print("\n=== 历史快照：新 → 旧，仅供回溯 ===")
    # 该迭代器本身已按新到旧返回；不要再 reverse()。
    for index, snapshot in enumerate(graph.get_state_history(config), start=1):
        metadata = snapshot.metadata or {}
        checkpoint_id = snapshot.config.get("configurable", {}).get("checkpoint_id")
        print(f"\n历史 #{index}（不是当前待办队列）")
        print(f"  metadata.step={metadata.get('step')!r}")
        print(f"  metadata.source={metadata.get('source')!r}")
        print(f"  config.checkpoint_id={checkpoint_id!r}")
        print(f"  values={snapshot.values!r}, next={snapshot.next!r}")
        if not snapshot.tasks:
            print("  tasks=()")
        for task in snapshot.tasks:
            print(f"  task name={task.name!r}, id={task.id!r}, error={task.error!r}")
            print(f"    result={task.result!r}")
            for item in task.interrupts:
                print(f"    interrupt id={item.id!r}, value={item.value!r}")
            if not task.interrupts:
                print("    interrupts=()")


def main() -> None:
    """首次运行、读取回答、按 ID 恢复，然后展示最终状态。"""
    graph = build_graph()
    # 同一次会话复用同一个配置；每次启动程序创建新的会话标识。
    config: RunnableConfig = {"configurable": {"thread_id": str(uuid4())}}
    print(f"会话 thread_id={config['configurable']['thread_id']}")
    result = graph.invoke({}, config)
    show_state_and_history(graph, config)

    # 只使用刚刚结束的调用输出，不从历史 tasks 收集待恢复中断。
    while pending := result.get("__interrupt__", ()):
        resume_map = collect_resume_map(pending)
        print("\n提交本轮 ID → 回答映射。")
        result = graph.invoke(Command(resume=resume_map), config)
        show_state_and_history(graph, config)

    latest = graph.get_state(config)
    if latest.next:
        raise RuntimeError("图仍有待执行节点，却没有可交互的动态中断")
    print(f"\n收集完成：{latest.values!r}")


if __name__ == "__main__":
    # 导入本模块只定义函数，不创建会话、不读取终端输入。
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\n输入已取消；进程结束后，此内存会话不能跨进程恢复。")
