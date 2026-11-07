"""审核编辑：先生成原稿，人工修改后再继续，默认离线固定样例。

流程：
START → llm_node → review_node → END

生成节点先写入 poem。审核节点用 interrupt() 展示原稿并暂停。
外部用 Command(resume=完整审核文本) 交回字符串，写入 reviewed_poem。
正常恢复同一检查点时，审核节点从头重执行，llm_node 不会再次生成。

默认 demo_generate_poem 返回固定布偶猫样例，不按新主题创作。
--live-model 才导入真实模型。InMemorySaver 只在当前进程有效。
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from typing import TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt


class ReviewState(TypedDict, total=False):
    """状态逐步补齐：topic 是输入，poem 是原稿，reviewed_poem 是审核稿。"""

    topic: str
    poem: str
    reviewed_poem: str


def demo_generate_poem(topic: str) -> str:
    """固定离线样例；topic 不参与生成，不宣称能按任意主题创作。"""
    return (
        "绒雪团团卧小窗\n"
        "蓝眸映月梦微凉\n"
        "轻摇长尾迎归客\n"
        "一室温柔伴夜长"
    )


def live_generate_poem(topic: str) -> str:
    """真实生成器：依赖与环境变量仅在调用时加载，默认导入无 API 调用。"""
    from dotenv import load_dotenv
    from langchain_deepseek import ChatDeepSeek

    # 不覆盖调用方已设置的环境变量；示例本身不创建或修改 .env。
    load_dotenv(override=False)
    llm = ChatDeepSeek(
        model="deepseek-v4-flash",
        extra_body={"thinking": {"type": "disabled"}},
    )
    response = llm.invoke(
        f"请以“{topic}”为主题写一首七言绝句，四句，每句七个汉字。"
        "只输出诗句，不要标题、解释或 Markdown 标记。"
    )
    # 外部模型可能返回结构化 content；本演示只接受纯文本，不做隐式转换。
    if not isinstance(response.content, str):
        raise TypeError("模型 response.content 必须是 str，不能直接使用结构化内容。")
    return response.content


def review_node(state: ReviewState) -> dict[str, str]:
    """发送展示载荷；恢复时 interrupt 的返回值是调用方提交的文本。"""
    reviewed_poem = interrupt(
        {
            "instruction": "请审核并修改大模型生成的七言绝句",
            "poem": state["poem"],
        }
    )
    # Command 来自图外；类型注解不能阻止 HTTP/CLI 等边界传入错误类型。
    if not isinstance(reviewed_poem, str):
        raise TypeError("审核恢复值必须是 str，请使用 Command(resume=审核文本)。")
    # 不覆盖 poem，保留模型原稿；是否保留原稿由调用方提前决定。
    return {"reviewed_poem": reviewed_poem}


def build_graph(
    generate_poem: Callable[[str], str] = demo_generate_poem,
) -> CompiledStateGraph:
    """构建独立图与内存检查点；可注入 spy 或自定义纯文本生成器。"""

    def llm_node(state: ReviewState) -> dict[str, str]:
        """闭包捕获生成器；无论离线还是真实模式，都只负责生成原稿。"""
        poem = generate_poem(state["topic"])
        if not isinstance(poem, str):
            raise TypeError("generate_poem(topic) 必须返回 str。")
        return {"poem": poem}

    builder = StateGraph(state_schema=ReviewState)
    builder.add_node("llm_node", llm_node)
    builder.add_node("review_node", review_node)
    builder.add_edge(START, "llm_node")
    builder.add_edge("llm_node", "review_node")
    builder.add_edge("review_node", END)
    return builder.compile(checkpointer=InMemorySaver())


def read_review(original_poem: str) -> str:
    """首行空白或 '.' 保留原诗，否则多行收集，以单独一行 '.' 结束。"""
    print("直接回车（或首行仅输入空白）保留原诗。")
    print("修改时逐行输入完整新诗，最后用单独一行英文句点 . 提交。")
    print("首行 . 也表示不修改；编辑中的空行会保留；不裁剪修改文本。")
    first_line = input("审核第 1 行：")
    if first_line.strip() == "" or first_line == ".":
        return original_poem

    lines = [first_line]
    while True:
        line = input("继续输入（. 结束）：")
        if line == ".":
            break
        lines.append(line)
    return "\n".join(lines)


def main() -> None:
    """CLI 调用方：启动同一线程，读取中断，收集文本，再恢复到 END。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", default="布偶猫", help="诗歌主题，默认：布偶猫")
    parser.add_argument(
        "--live-model", action="store_true", help="显式启用真实 DeepSeek 模型调用"
    )
    args = parser.parse_args()

    generator = live_generate_poem if args.live_model else demo_generate_poem
    if args.live_model:
        print("真实模型模式：生成原稿会调用 API；恢复审核不会再次生成。")
    else:
        print("离线模式：固定展示布偶猫样例，不调用 API，也不按输入主题重新创作。")
    print(f"输入主题：{args.topic}")

    graph = build_graph(generator)
    # 一次运行一个新线程；两次 invoke 必须使用同一个 graph 和 config。
    config = {"configurable": {"thread_id": f"review-edit-{uuid4().hex}"}}
    first_result = graph.invoke({"topic": args.topic}, config=config)
    payload = first_result["__interrupt__"][0].value
    print("\n中断展示载荷：")
    print(payload)
    original_poem = payload["poem"]
    print("\n待审核原诗：")
    print(original_poem)
    print(f"暂停时 next：{graph.get_state(config).next}")

    try:
        review_text = read_review(original_poem)
    except (EOFError, KeyboardInterrupt):
        print("\n审核输入已取消，没有提交恢复；本进程退出后内存检查点不再保留。")
        return

    final_state = graph.invoke(Command(resume=review_text), config=config)
    print("\n原诗（poem，保持不变）：")
    print(final_state["poem"])
    print("\n审核后诗歌（reviewed_poem）：")
    print(final_state["reviewed_poem"])
    print("\n审核后状态：")
    print(final_state)
    print(f"结束时 next：{graph.get_state(config).next}")


if __name__ == "__main__":
    main()
