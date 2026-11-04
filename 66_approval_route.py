"""人工审批动态路由：默认离线生成，批准后才调用注入的生成函数。

流程：
START → approve_node → llm_node → END
                     → default_node → END

审批节点用 interrupt() 暂停。外部用 Command(resume=True/False) 交回布尔值。
节点再用 Command(goto=..., update=...) 写入 is_approved 并选择唯一后继。
审批节点没有静态出边。拒绝路径不会调用生成函数。

默认 demo_generate_poem 返回固定菊花诗，不按新主题创作。
--live-model 只在批准并进入 llm_node 后才导入模型。
InMemorySaver 只在当前进程有效。两个会话使用不同的 thread_id。

在 LangGraph 1.2.16 上，非布尔恢复值会让 approve_node 抛出 TypeError，
并把该错误留在原 thread 的待执行任务上。之后再对同一 thread 提交 True 或 False，
仍会抛出同一个 TypeError。换一个 thread_id，或换一个新的 InMemorySaver，
都会在新会话里重新停在审批节点。
"""

import argparse
from collections.abc import Callable
from typing import Literal, TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt


class ApprovalState(TypedDict, total=False):
    """字段按执行阶段逐步填充；TypedDict 不提供运行时数据校验。"""

    topic: str
    poem: str
    is_approved: bool


def approve_node(
    state: ApprovalState,
) -> Command[Literal["llm_node", "default_node"]]:
    """暂停等待布尔反馈，并同时更新审批状态、选择唯一后继节点。"""
    approval = interrupt("是否同意调用模型?")
    # 不能用 bool(approval)：非空字符串 'n' 或 'false' 也会变成 True。
    if not isinstance(approval, bool):
        raise TypeError("审批恢复值必须是 bool（True 或 False），不接受字符串或整数")
    destination = "llm_node" if approval else "default_node"
    return Command(goto=destination, update={"is_approved": approval})


def demo_generate_poem(topic: str) -> str:
    """返回固定菊花示例，仅演示分支执行，不模拟真实主题创作。"""
    print(
        f"离线固定演示：不调用模型；输入主题为{topic!r}，固定示例主题为'菊花'。"
    )
    return "秋风吹落满庭霜\n独有黄花映夕阳\n不与春红争艳色\n清香一缕入诗章"


def live_generate_poem(topic: str) -> str:
    """仅在审批通过且真实生成函数被调用时，加载环境并初始化模型。"""
    # 惰性导入：拒绝路径不需要这两个可选依赖，也不会读取 API Key。
    from dotenv import load_dotenv
    from langchain_deepseek import ChatDeepSeek

    load_dotenv(override=False)
    model = ChatDeepSeek(
        model="deepseek-v4-flash",
        extra_body={"thinking": {"type": "disabled"}},
    )
    response = model.invoke(f"请以{topic}为主题写一首七言绝句，只返回四句诗。")
    if not isinstance(response.content, str):
        raise TypeError("模型返回的 .content 必须是 str，当前返回值不是字符串")
    return response.content


def default_node(state: ApprovalState) -> ApprovalState:
    """拒绝后返回固定结果；不会触发任何生成函数。"""
    return {"poem": "请求被拒绝"}


def build_graph(
    generate_poem: Callable[[str], str] = demo_generate_poem,
) -> CompiledStateGraph:
    """构建独立图与内存检查点；可注入生成函数观察调用次数。"""

    def llm_node(state: ApprovalState) -> ApprovalState:
        # 只有 approve_node 动态选择本节点后，才会调用生成函数。
        return {"poem": generate_poem(state["topic"])}

    builder = StateGraph(state_schema=ApprovalState)
    builder.add_node("approve_node", approve_node)
    builder.add_node("llm_node", llm_node)
    builder.add_node("default_node", default_node)
    builder.add_edge(START, "approve_node")
    # 审批节点没有静态出边：后继完全由 Command(goto=...) 决定。
    builder.add_edge("llm_node", END)
    builder.add_edge("default_node", END)
    return builder.compile(checkpointer=InMemorySaver())


def read_approval(question: str) -> bool:
    """只接受 y/n，忽略前后空白及大小写，其他输入继续询问。"""
    while True:
        answer = input(f"{question} [y/n]：").strip().lower()
        if answer == "y":
            return True
        if answer == "n":
            return False
        print("输入无效，请仅输入 y 或 n。")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="人工审批动态路由演示：默认离线固定诗歌，两个会话均由人工选择分支。"
    )
    parser.add_argument("--topic", default="菊花", help="诗歌主题（默认：菊花）")
    parser.add_argument(
        "--live-model", action="store_true", help="审批通过后才调用真实 DeepSeek 模型"
    )
    args = parser.parse_args()
    # 这里只选择函数，不调用函数，因此 --live-model 不会提前初始化模型。
    generate_poem = live_generate_poem if args.live_model else demo_generate_poem
    graph = build_graph(generate_poem)

    # 同一张图的两个独立会话；不是预设一次通过、一次拒绝。
    for session_number in (1, 2):
        config = {"configurable": {"thread_id": f"approval-{uuid4().hex}"}}
        print(f"\n=== 会话 {session_number} ===")
        print("thread_id：", config["configurable"]["thread_id"])
        paused_result = graph.invoke({"topic": args.topic}, config=config)
        question = paused_result["__interrupt__"][0].value
        print("中断载荷：", question)
        paused_state = graph.get_state(config)
        print("暂停状态：", paused_state.values)
        print("待执行节点：", paused_state.next)

        approval = read_approval(question)
        # 必须沿用当前会话的 config，恢复该 thread_id 的挂起执行。
        final_result = graph.invoke(Command(resume=approval), config=config)
        final_state = graph.get_state(config)
        print("最终状态：", final_result)
        print("待执行节点：", final_state.next)
        print("诗歌结果：\n" + final_result["poem"])


if __name__ == "__main__":
    main()
