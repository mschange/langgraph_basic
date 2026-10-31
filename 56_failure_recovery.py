"""失败后恢复：并行节点有一个失败时，用同一 thread_id 从最新检查点继续。

第一次 node_joke 抛异常。当前版本会留下同一超步里已经成功的 node_poem，
恢复时只重新执行 node_joke。get_state().next 是 ("node_joke",)。
历史列表里更早的一条仍可能是进入该超步之前的检查点，next 里同时有两个节点。

检查点存在 PostgreSQL 里，两次运行可以分属不同的连接。
重复运行已完成的 thread_id 前，请换一个新的 thread_id。

前置：
  本机 PostgreSQL 已创建 langgraph_user / langgraph_db
  .env 中配置 DEEPSEEK_API_KEY=...
"""

from typing import TypedDict

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from loguru import logger

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)

DB_URL = "postgresql://langgraph_user:123456@localhost:5432/langgraph_db?sslmode=disable"
config = {"configurable": {"thread_id": "chapter03-recovery"}}

topics = ["布偶猫", "狸花猫", "金渐层"]
topic_index = 0


class OverAllState(TypedDict):
    topic: str
    poem: str
    joke: str
    final_output: str


class InputState(TypedDict):
    topic: str


class OutputState(TypedDict):
    final_output: str


def node_change_topic(state: InputState) -> dict[str, str]:
    global topic_index
    logger.info("node_change_topic 正在执行, topic_index={}", topic_index)
    sub_topic = topics[topic_index]
    topic_index = (topic_index + 1) % len(topics)
    return {"topic": f"{state['topic']}:{sub_topic}"}


def node_poem(state: OverAllState) -> dict[str, str]:
    logger.info("node_poem 正在执行")
    poem = model.invoke(
        [HumanMessage(f"写一首关于{state['topic']}主题的七言绝句，只给诗句")]
    ).content
    return {"poem": str(poem)}


def node_output(state: OverAllState) -> dict[str, str]:
    logger.info("node_output 正在执行")
    final_output = (
        f"关于{state['topic']}的七言绝句：\n{state['poem']}\n笑话：\n{state['joke']}"
    )
    return {"final_output": final_output}


def build_graph(node_joke_fn):
    builder = StateGraph(
        state_schema=OverAllState,
        input_schema=InputState,
        output_schema=OutputState,
    )
    builder.add_node("node_change_topic", node_change_topic)
    builder.add_node("node_poem", node_poem)
    builder.add_node("node_joke", node_joke_fn)
    builder.add_node("node_output", node_output)
    builder.add_edge(START, "node_change_topic")
    builder.add_edge("node_change_topic", "node_poem")
    builder.add_edge("node_change_topic", "node_joke")
    builder.add_edge("node_poem", "node_output")
    builder.add_edge("node_joke", "node_output")
    builder.add_edge("node_output", END)
    return builder


def broken_node_joke(state: OverAllState) -> dict[str, str]:
    logger.warning("node_joke 人为抛异常，模拟失败")
    raise RuntimeError("node_joke 执行失败！")


def fixed_node_joke(state: OverAllState) -> dict[str, str]:
    logger.info("node_joke 正在执行（已修复）")
    joke = model.invoke(
        [HumanMessage(f"写一个关于{state['topic']}主题的笑话，不超过一百字")]
    ).content
    return {"joke": str(joke)}


def main() -> None:
    print("=" * 60)
    print("第一次运行：node_joke 抛异常，图执行中断")
    print("=" * 60)

    with PostgresSaver.from_conn_string(DB_URL) as checkpointer:
        checkpointer.setup()
        graph = build_graph(broken_node_joke).compile(checkpointer=checkpointer)
        try:
            print(graph.invoke({"topic": "猫"}, config=config))
        except Exception as error:
            print(f"捕获异常: {error}")

        print("\n── 检查点历史 ──")
        for index, checkpoint in enumerate(graph.get_state_history(config)):
            checkpoint_id = checkpoint.config["configurable"]["checkpoint_id"][:16]
            print(f"  [{index}] checkpoint_id={checkpoint_id}...")
            print(f"       next={checkpoint.next}")
            print(f"       values keys={list(checkpoint.values.keys())}")
            print()

    print("=" * 60)
    print("第二次运行：修复 node_joke，传入 None 从最新检查点恢复")
    print("=" * 60)

    with PostgresSaver.from_conn_string(DB_URL) as checkpointer:
        graph = build_graph(fixed_node_joke).compile(checkpointer=checkpointer)
        result = graph.invoke(None, config=config)
        print("\n── 恢复执行结果 ──")
        print(result)


if __name__ == "__main__":
    main()
