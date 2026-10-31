"""检查点重放：从 node_poem / node_joke 之前的历史检查点重新执行后续节点。

Replay 会再次调用模型，结果可以和第一次不同。
node_change_topic 在该检查点之前，重放时不会再执行。

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
    logger.info("topic_index: {}", topic_index)
    sub_topic = topics[topic_index]
    topic_index = (topic_index + 1) % len(topics)
    return {"topic": f"{state['topic']}:{sub_topic}"}


def node_poem(state: OverAllState) -> dict[str, str]:
    logger.info("node_poem 正在执行")
    poem = model.invoke(
        [HumanMessage(f"写一首关于{state['topic']}主题的七言绝句")]
    ).content
    return {"poem": str(poem)}


def node_joke(state: OverAllState) -> dict[str, str]:
    logger.info("node_joke 正在执行")
    joke = model.invoke(
        [HumanMessage(f"写一个关于{state['topic']}主题的笑话")]
    ).content
    return {"joke": str(joke)}


def node_output(state: OverAllState) -> dict[str, str]:
    logger.info("node_output 正在执行")
    final_output = f"关于{state['topic']}的七言绝句:{state['poem']}\n 笑话:{state['joke']}\n"
    return {"final_output": final_output}


builder = StateGraph(
    state_schema=OverAllState,
    input_schema=InputState,
    output_schema=OutputState,
)
builder.add_node("node_change_topic", node_change_topic)
builder.add_node("node_poem", node_poem)
builder.add_node("node_joke", node_joke)
builder.add_node("node_output", node_output)
builder.add_edge(START, "node_change_topic")
builder.add_edge("node_change_topic", "node_poem")
builder.add_edge("node_change_topic", "node_joke")
builder.add_edge("node_poem", "node_output")
builder.add_edge("node_joke", "node_output")
builder.add_edge("node_output", END)


def main() -> None:
    with PostgresSaver.from_conn_string(DB_URL) as checkpointer:
        checkpointer.setup()
        graph = builder.compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": "chapter03-08"}}

        result = graph.invoke({"topic": "猫咪"}, config=config)
        print("首次运行结果:", result)

        history = list(graph.get_state_history(config))
        target = next(
            (item for item in history if item.next == ("node_poem", "node_joke")),
            None,
        )
        if target is None:
            logger.error("没有找到 node_poem / node_joke 执行前的检查点")
            return

        logger.info("找到目标检查点，开始 Replay")
        replayed = graph.invoke(None, config=target.config)
        print("Replay 结果:", replayed)


if __name__ == "__main__":
    main()
