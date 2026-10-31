"""中断恢复：在指定节点前或后暂停，改状态后再 invoke(None) 继续。

场景 A：interrupt_before=["node_generate"]
  分析完成后暂停，把 style 改成「幽默」，再生成和审核。

场景 B：interrupt_after=["node_generate"]
  内容生成后暂停，替换 content，再进入审核。

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from typing import TypedDict

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from loguru import logger

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)


class OverAllState(TypedDict, total=False):
    topic: str
    style: str
    content: str
    approved: bool
    final_output: str


def node_analyze(state: OverAllState) -> dict[str, str]:
    """根据主题确定写作风格。"""
    logger.info("node_analyze 正在执行")
    style = model.invoke(
        [
            HumanMessage(
                f"分析主题「{state['topic']}」适合什么写作风格，只回答一个词：幽默/严肃/抒情/哲理"
            )
        ]
    ).content
    style = str(style).strip()
    logger.info("分析结果 - 风格: {}", style)
    return {"style": style}


def node_generate(state: OverAllState) -> dict[str, str]:
    """按主题和风格生成短文。"""
    logger.info("node_generate 正在执行, style={}", state["style"])
    content = model.invoke(
        [
            HumanMessage(
                f"用{state['style']}风格写一段关于「{state['topic']}」的短文，不超过100字"
            )
        ]
    ).content
    content = str(content)
    logger.info("生成内容: {}", content[:50])
    return {"content": content}


def node_review(state: OverAllState) -> dict:
    """判断内容是否合格，并写出最终输出。"""
    logger.info("node_review 正在执行")
    verdict = model.invoke(
        [
            HumanMessage(
                "审核以下内容是否合格（内容健康、语句通顺），只回答 yes 或 no：\n"
                f"{state['content']}"
            )
        ]
    ).content
    approved = "yes" in str(verdict).strip().lower()
    logger.info("审核结果: approved={}", approved)
    final_output = state["content"] if approved else f"[未通过审核] {state['content']}"
    return {"approved": approved, "final_output": final_output}


def build_graph(interrupt_before=None, interrupt_after=None):
    builder = StateGraph(state_schema=OverAllState)
    builder.add_node("node_analyze", node_analyze)
    builder.add_node("node_generate", node_generate)
    builder.add_node("node_review", node_review)
    builder.add_edge(START, "node_analyze")
    builder.add_edge("node_analyze", "node_generate")
    builder.add_edge("node_generate", "node_review")
    builder.add_edge("node_review", END)
    return builder.compile(
        checkpointer=InMemorySaver(),
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
    )


def scenario_before() -> None:
    """生成前暂停，修改风格后再继续。"""
    print("=" * 60)
    print('场景 A：interrupt_before=["node_generate"]')
    print("=" * 60)

    config = {"configurable": {"thread_id": "interrupt-demo-a"}}
    graph = build_graph(interrupt_before=["node_generate"])

    print("\n── 第一轮：执行到中断点 ──")
    result = graph.invoke({"topic": "秋天"}, config=config)
    print(f"  topic = {result['topic']}")
    print(f"  style = {result.get('style', '(未生成)')}")
    print(f"  content = {result.get('content', '(未生成)')}")

    snapshot = graph.get_state(config)
    print("\n── 查看图状态 ──")
    print(f"  next = {snapshot.next}")
    print(f"  values = {dict(snapshot.values)}")

    print("\n── 人工干预：将 style 修改为「幽默」 ──")
    graph.update_state(config, values={"style": "幽默"})
    snapshot = graph.get_state(config)
    print(f"  修改后 style = {snapshot.values.get('style')}")

    print("\n── 第二轮：传入 None，从中断点恢复 ──")
    result = graph.invoke(None, config)
    print("\n── 最终结果 ──")
    print(f"  style = {result['style']}")
    print(f"  content = {result['content']}")
    print(f"  approved = {result['approved']}")


def scenario_after() -> None:
    """生成后暂停，替换内容后再审核。"""
    print("\n\n" + "=" * 60)
    print('场景 B：interrupt_after=["node_generate"]')
    print("=" * 60)

    config = {"configurable": {"thread_id": "interrupt-demo-b"}}
    graph = build_graph(interrupt_after=["node_generate"])

    print("\n── 第一轮：执行到中断点（node_generate 已完成） ──")
    result = graph.invoke({"topic": "人工智能"}, config=config)
    print(f"  topic = {result['topic']}")
    print(f"  style = {result.get('style', '(未生成)')}")
    print(f"  content = {str(result.get('content', '(未生成)'))[:60]}")

    snapshot = graph.get_state(config)
    print("\n── 查看图状态 ──")
    print(f"  next = {snapshot.next}")

    print("\n── 人工干预：替换 content ──")
    replacement = "人工智能是人类智慧的延伸，它帮助我们解决问题，也提醒我们思考什么才是真正重要的。"
    graph.update_state(config, values={"content": replacement})
    snapshot = graph.get_state(config)
    print(f"  修改后 content = {snapshot.values.get('content', '')[:50]}")

    print("\n── 第二轮：传入 None，从中断点恢复 ──")
    result = graph.invoke(None, config)
    print("\n── 最终结果 ──")
    print(f"  approved = {result['approved']}")
    print(f"  final_output = {result['final_output']}")


if __name__ == "__main__":
    scenario_before()
    scenario_after()
