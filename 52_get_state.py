"""获取最新检查点：graph.get_state(config) 读取该 thread 的当前状态。

图结构与输入输出分离示例相同。invoke 的返回值只有 final_output，
检查点里仍保存 topic、poem、joke 等内部字段。

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from typing import TypedDict

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from loguru import logger
from rich import print as rprint

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)


class OverAllState(TypedDict):
    topic: str
    poem: str
    joke: str
    final_output: str


class InputState(TypedDict):
    topic: str


class OutputState(TypedDict):
    final_output: str


def node_poem(state: InputState) -> dict[str, str]:
    logger.info("node_poem 已执行")
    poem = model.invoke(
        [HumanMessage(f"写一首关于 {state['topic']} 的七言绝句，不要赏析，只给诗句即可")]
    ).content
    return {"poem": str(poem)}


def node_joke(state: InputState) -> dict[str, str]:
    logger.info("node_joke 已执行")
    joke = model.invoke(
        [HumanMessage(f"写一个关于 {state['topic']} 的笑话，尽可能简单，不超过一百字")]
    ).content
    return {"joke": str(joke)}


def node_output(state: OverAllState) -> dict[str, str]:
    logger.info("node_output 已执行")
    final_output = (
        f"关于 {state['topic']} 的七言绝句：\n{state['poem']}\n笑话：\n{state['joke']}"
    )
    return {"final_output": final_output}


builder = StateGraph(
    state_schema=OverAllState,
    input_schema=InputState,
    output_schema=OutputState,
)
builder.add_node("node_poem", node_poem)
builder.add_node("node_joke", node_joke)
builder.add_node("node_output", node_output)
builder.add_edge(START, "node_poem")
builder.add_edge(START, "node_joke")
builder.add_edge("node_poem", "node_output")
builder.add_edge("node_joke", "node_output")
builder.add_edge("node_output", END)

graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "123"}}


if __name__ == "__main__":
    result = graph.invoke({"topic": "猫咪"}, config=config)
    rprint("=" * 30, "-> 运行结果 <-", "=" * 30)
    rprint(result)

    rprint("=" * 30, "-> 最新历史检查点 <-", "=" * 30)
    rprint(graph.get_state(config))
