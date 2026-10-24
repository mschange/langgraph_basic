"""Send 动态扇出：运行时为同一 worker 创建多个并行任务，各带私有状态。

流程：START → router(返回 3 个 Send) → 3× worker_node 并行 → END

前置：.env 中配置 DEEPSEEK_API_KEY=...
"""

from collections.abc import Sequence
from typing import Literal, TypedDict

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

load_dotenv(override=True)

CONTENT_TYPES = ("poem", "ci_poem", "joke")

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)


# ========== 四种状态 Schema ==========
class OverAllState(TypedDict):
    """图内部完整状态。"""
    topic: str
    poem: str
    ci_poem: str
    joke: str


class InputState(TypedDict):
    """外部 invoke 只能传 topic。"""
    topic: str


class WorkerState(TypedDict):
    """每个 Worker 任务的私有状态（由 Send.arg 注入）。"""
    content_type: Literal["poem", "ci_poem", "joke"]
    prompt: str


class OutputState(TypedDict):
    """最终返回给调用者的字段（不含 topic）。"""
    poem: str
    ci_poem: str
    joke: str


# ========== 节点 ==========
def worker_node(state: WorkerState) -> dict[str, str]:
    """按私有状态调用 LLM，返回单字段（如 {"poem": "..."}）合并进全局状态。"""
    content_type = state["content_type"]
    prompt = state["prompt"]
    content = model.invoke([HumanMessage(content=prompt)]).content
    return {content_type: str(content)}


def router(state: InputState) -> Sequence[Send]:
    """为每种内容类型创建一个 Send → 同一 worker_node 的多个并行任务。"""
    content_names = {
        "poem": "一首诗",
        "ci_poem": "一首词",
        "joke": "一个笑话",
    }
    return [
        Send(
            "worker_node",
            {
                "content_type": content_type,
                "prompt": f"请生成关于 {state['topic']} 的{content_names[content_type]}",
            },
        )
        for content_type in CONTENT_TYPES
    ]


# ========== 构建并编译 ==========
builder = StateGraph(
    state_schema=OverAllState,
    input_schema=InputState,
    output_schema=OutputState,
)
builder.add_node("worker_node", worker_node)
builder.add_conditional_edges(START, router, path_map=["worker_node"])
builder.add_edge("worker_node", END)

graph = builder.compile()


if __name__ == "__main__":
    result = graph.invoke({"topic": "布偶狗"})
    print("诗：")
    print(result["poem"])
    print("\n词：")
    print(result["ci_poem"])
    print("\n笑话：")
    print(result["joke"])
