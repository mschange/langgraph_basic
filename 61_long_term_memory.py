"""长期记忆加短期记忆：没有偏好时查 store，同一 thread 的下一轮直接复用。

第一次调用从 ("users", username) 读取 preferences，再交给模型。
第二次调用恢复检查点。偏好已经在状态里，路由会跳过查询节点。

先运行 60_store_seed.py 写入 Alice、Bob、Black 的偏好。

前置：
  本机 PostgreSQL 已创建 langgraph_user / langgraph_db
  .env 中配置 DEEPSEEK_API_KEY=...
"""

from typing import Literal

from dotenv import load_dotenv
from langchain.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState
from langgraph.runtime import Runtime
from langgraph.store.postgres import PostgresStore

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)

DB_URL = "postgresql://langgraph_user:123456@localhost:5432/langgraph_db?sslmode=disable"
USERS_NS = ("users",)
PREFERENCES_KEY = "preferences"


class OverAllState(MessagesState):
    username: str
    user_input: str
    output: str
    preferences: dict[str, str]


def check_preferences_node(state: OverAllState, runtime: Runtime) -> dict:
    """从长期记忆读取当前用户的偏好。"""
    item = runtime.store.get((*USERS_NS, state["username"]), PREFERENCES_KEY)
    if not item:
        return {}
    return {"preferences": item.value}


def router(state: OverAllState) -> Literal["check_preferences_node", "llm_node"]:
    """状态里还没有偏好时，先去长期记忆查询。"""
    if not state.get("preferences"):
        return "check_preferences_node"
    return "llm_node"


def llm_node(state: OverAllState) -> dict:
    """把偏好、历史消息和本轮需求一起交给模型。"""
    preferences = state.get("preferences", {})
    system_prompt = "请根据用户偏好解决用户需求"
    human_prompt = (
        f"这是用户的偏好: \n{preferences}\n这是用户的需求: \n{state['user_input']}\n"
    )
    messages = (
        [SystemMessage(content=system_prompt)]
        if not state.get("messages", [])
        else state["messages"]
    )
    response = model.invoke(messages + [HumanMessage(content=human_prompt)])
    return {
        "messages": messages + [HumanMessage(content=human_prompt), response],
        "output": response.content,
    }


builder = StateGraph(state_schema=OverAllState)
builder.add_node("check_preferences_node", check_preferences_node)
builder.add_node("llm_node", llm_node)
builder.add_conditional_edges(
    START,
    router,
    path_map=["check_preferences_node", "llm_node"],
)
builder.add_edge("check_preferences_node", "llm_node")
builder.add_edge("llm_node", END)


def main() -> None:
    with (
        PostgresSaver.from_conn_string(DB_URL) as checkpointer,
        PostgresStore.from_conn_string(DB_URL) as store,
    ):
        checkpointer.setup()
        graph = builder.compile(checkpointer=checkpointer, store=store)
        config = {"configurable": {"thread_id": "memory-demo"}}

        first = graph.invoke(
            {"username": "Alice", "user_input": "我有点无聊，和我聊聊天吧"},
            config=config,
        )
        print("第一次调用输出:", first["output"])

        second = graph.invoke(
            {"user_input": "推荐一下酸奶"},
            config=config,
        )
        print("第二次调用输出:", second["output"])


if __name__ == "__main__":
    main()
