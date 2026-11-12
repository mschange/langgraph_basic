"""驱动脚本：连接 langgraph dev，逐个回答动态中断并越过静态断点。

运行前先在本目录启动：
  langgraph dev --no-browser --port 2024

SERVER_URL 的端口须与 --port 一致。
ASSISTANT_ID 是 langgraph.json 中 graphs 的键，不是文件名。
动态中断用 Command(resume=...)；静态断点用 input=None 继续。
"""

from typing import Any

from langgraph_sdk import get_sync_client
from langgraph_sdk.schema import Command

# 服务器地址需与 langgraph dev 的 --port 保持一致。
SERVER_URL = "http://127.0.0.1:2024"
# 这里的 "graph" 是 langgraph.json 中 graphs 的键，不是文件名。
ASSISTANT_ID = "graph"


def show_state(client: Any, thread_id: str, tag: str) -> None:
    """打印线程最新状态：业务值、待执行节点与任务上的中断载荷。"""
    state = client.threads.get_state(thread_id)
    print(f"\n--- {tag} ---")
    print(f"  values = {state['values']!r}")
    print(f"  next   = {state['next']!r}")
    if not state["tasks"]:
        print("  tasks  = ()")
    for task in state["tasks"]:
        print(f"  task name={task['name']!r}")
        if not task["interrupts"]:
            # 静态暂停时这里为空，说明没有需要回答的问题。
            print("    interrupts = ()  （静态暂停，无待回答载荷）")
        for item in task["interrupts"]:
            print(f"    interrupt id={item.get('id')!r}, value={item.get('value')!r}")


def show_history(client: Any, thread_id: str) -> None:
    """检查点历史按从新到旧返回；它记录执行进度，不是调用流水账。"""
    print("\n=== 检查点历史（新 → 旧）===")
    for snapshot in client.threads.get_history(thread_id, limit=10):
        metadata = snapshot.get("metadata") or {}
        checkpoint_id = snapshot["checkpoint"]["checkpoint_id"]
        print(
            f"  step={metadata.get('step')!r}, "
            f"source={metadata.get('source')!r}, "
            f"checkpoint_id={checkpoint_id[:8]}..., "
            f"next={snapshot['next']!r}, values={snapshot['values']!r}"
        )


def main() -> None:
    client = get_sync_client(url=SERVER_URL)
    thread_id = client.threads.create()["thread_id"]
    print(f"thread_id = {thread_id}")

    # 第一次运行：提交空输入，图停在第一个动态中断处。
    result = client.runs.wait(thread_id, ASSISTANT_ID, input={})
    print(f"\n第 1 次运行返回：{result!r}")
    show_state(client, thread_id, "第 1 次运行后")

    # 三个问题按节点内的代码顺序依次出现，逐个回答。
    # 年龄传入的是整数，类型转换由调用方负责，框架不会替你转。
    for index, answer in enumerate(["小黄", 18, "male"], start=2):
        result = client.runs.wait(thread_id, ASSISTANT_ID, command=Command(resume=answer))
        print(f"\n第 {index} 次运行（提交 {answer!r}）返回：{result!r}")
        show_state(client, thread_id, f"提交 {answer!r} 后")

    # 三个问题答完后，图停在 confirm_node 的静态前置断点上。
    # 静态断点用 input=None 继续，不是用 Command(resume=...)。
    result = client.runs.wait(thread_id, ASSISTANT_ID, input=None)
    print(f"\n越过静态断点后返回：{result!r}")
    show_state(client, thread_id, "越过静态断点后")

    show_history(client, thread_id)


if __name__ == "__main__":
    # 导入本模块只定义函数；运行前请确认开发服务器已经就绪。
    main()
