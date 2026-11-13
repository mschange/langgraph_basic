"""用 SDK 驱动本地开发服务器上的 chat_graph，完整演示一次审批流程。

运行前确认：
  1. 另一个终端里 langgraph dev 已经在跑
  2. .env 里的模型密钥有效（本脚本会真实调用模型）
"""

from langgraph_sdk import get_sync_client
from langgraph_sdk.schema import Command

# 开发服务器地址，与 langgraph dev 的 --host / --port 保持一致
SERVER_URL = "http://127.0.0.1:2024"

# 这里填 langgraph.json 中 graphs 的键，不是文件名、不是目录名
ASSISTANT_ID = "chat_graph"


def show_interrupt(result: dict) -> None:
    """打印本次运行是否被中断，以及中断里带了什么。"""
    interrupts = result.get("__interrupt__")

    if not interrupts:
        print("  未发生中断")
        return

    # 本例一次中断提交全部工具调用，所以列表长度固定为 1
    payload = interrupts[0]["value"]

    print(f"  中断个数：{len(interrupts)}")

    for index, request in enumerate(payload["action_requests"]):
        print(f"  [{index}] 工具：{request['name']}")
        print(f"       参数：{request['args']}")
        print(f"       说明：{request['description']}")

    for config in payload["review_configs"]:
        print(f"       可选决策：{config['allowed_decisions']}")


def show_messages(result: dict) -> None:
    """打印本次运行后的消息列表，只看类型和内容摘要。"""
    for message in result.get("messages", []):
        role = message.get("type")
        content = message.get("content")
        calls = message.get("tool_calls")

        if calls:
            names = [call["name"] for call in calls]
            args = [call["args"] for call in calls]
            print(f"  {role}: 请求调用 {names} 参数 {args}")
        else:
            print(f"  {role}: {content}")


def main() -> None:
    client = get_sync_client(url=SERVER_URL)

    # 每次新建线程，避免复用旧状态造成干扰
    thread = client.threads.create()
    thread_id = thread["thread_id"]
    print(f"线程：{thread_id}\n")

    # ---- 第一轮：提问，预期在 tool_node 前中断 ----
    print("第 1 步：提问「今天西安天气怎么样」")
    result = client.runs.wait(
        thread_id,
        ASSISTANT_ID,
        input={
            "messages": [
                {"role": "user", "content": "今天西安天气怎么样"}
            ]
        },
    )
    show_interrupt(result)
    print()

    # ---- 第二轮：回传同意决策 ----
    # 注意这里用 command=Command(resume=...)，不是 input=
    print("第 2 步：回传「同意」")
    result = client.runs.wait(
        thread_id,
        ASSISTANT_ID,
        command=Command(
            resume={"decisions": [{"type": "approve"}]}
        ),
    )
    show_messages(result)
    print()

    # ---- 第三轮：再问一次，这次拒绝 ----
    print("第 3 步：提问「今天北京天气怎么样」")
    result = client.runs.wait(
        thread_id,
        ASSISTANT_ID,
        input={
            "messages": [
                {"role": "user", "content": "今天北京天气怎么样"}
            ]
        },
    )
    show_interrupt(result)
    print()

    print("第 4 步：回传「拒绝」并附理由")
    result = client.runs.wait(
        thread_id,
        ASSISTANT_ID,
        command=Command(
            resume={
                "decisions": [
                    {"type": "reject", "message": "不想让你回答"}
                ]
            }
        ),
    )
    show_messages(result)
    print()

    # ---- 查看检查点历史 ----
    print("检查点历史（由新到旧）：")
    history = client.threads.get_history(thread_id, limit=10)

    for snapshot in history:
        metadata = snapshot.get("metadata") or {}
        print(
            f"  step={metadata.get('step')} "
            f"source={metadata.get('source')} "
            f"next={snapshot.get('next')}"
        )


if __name__ == "__main__":
    main()
