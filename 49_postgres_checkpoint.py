"""PostgreSQL 检查点：进程重启后，同一 thread_id 仍能恢复会话。

流程与内存检查点相同：START → llm_node → output_node → END
区别是检查点写在数据库里。setup() 会在示例中建表，生产环境应单独做迁移。

前置：
  pip install langgraph-checkpoint-postgres
  本机 PostgreSQL 已创建 langgraph_user / langgraph_db
  .env 中配置 DEEPSEEK_API_KEY=...
"""

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState

load_dotenv(override=True)

model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={"thinking": {"type": "disabled"}},
)

DB_URL = "postgresql://langgraph_user:123456@localhost:5432/langgraph_db?sslmode=disable"


class OverAllState(MessagesState):
    output: str


def llm_node(state: OverAllState) -> dict:
    """把当前消息历史交给模型，追加一条 AI 回复。"""
    return {"messages": [model.invoke(state["messages"])]}


def output_node(state: OverAllState) -> dict:
    """取出最后一条模型回复。"""
    return {"output": state["messages"][-1].content}


builder = StateGraph(state_schema=OverAllState)
builder.add_node("llm_node", llm_node)
builder.add_node("output_node", output_node)
builder.add_edge(START, "llm_node")
builder.add_edge("llm_node", "output_node")
builder.add_edge("output_node", END)


def main() -> None:
    with PostgresSaver.from_conn_string(DB_URL) as checkpointer:
        checkpointer.setup()
        graph = builder.compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": "chapter_6_6.2.4"}}

        graph.invoke({"messages": [HumanMessage("你好，我是老王")]}, config=config)
        graph.invoke(
            {"messages": [HumanMessage("从现在开始，你是小王")]},
            config=config,
        )
        result = graph.invoke(
            {"messages": [HumanMessage("我是谁？你是谁？")]},
            config=config,
        )
        print(result["output"])

        print("=" * 30, "-> 完整消息列表 <-", "=" * 30)
        for message in result["messages"]:
            message.pretty_print()


if __name__ == "__main__":
    main()
