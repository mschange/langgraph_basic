"""消息合并机制：add_messages 按 id 智能合并，而非简单拼接。

规则：
1. right 中的消息 id 在 left 中不存在 → 追加到末尾
2. right 中的消息 id 在 left 中已存在 → 替换旧消息
"""

from langchain.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from rich import print as rprint


# 左侧：已有对话历史
left = [
    SystemMessage(content="你是一个专业的翻译", id="1"),
    HumanMessage(content="你好", id="2"),
    AIMessage(content="你好，我是专业的翻译", id="3"),
]

# 右侧：新消息（id=2、3 与 left 重复 → 替换；id=4、5 新增 → 追加）
right = [
    HumanMessage(content="我是老王，你是小王", id="2"),
    AIMessage(content="好的我记住了", id="3"),
    HumanMessage(content="你是谁?", id="4"),
    AIMessage(content="我是小王", id="5"),
]


if __name__ == "__main__":
    merged = add_messages(left, right)
    rprint(merged)
    # 预期: id=1 保留；id=2、3 被替换；id=4、5 追加
