"""子图检查点：父图有 checkpointer，手动 invoke 子图。

流程：
父图 START → call_subgraph → END
子图 START → strip → punctuate → END

父图检查点只记录 call_subgraph 这一层，不含子图内部节点。
不需要模型或 API Key。
"""

from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph


class SubgraphState(TypedDict):
    raw_text: str
    stripped_text: str
    punctuated_text: str


def subgraph_strip_node(state: SubgraphState) -> SubgraphState:
    return {"stripped_text": state["raw_text"].strip()}


def subgraph_punctuate_node(state: SubgraphState) -> SubgraphState:
    return {"punctuated_text": state["stripped_text"] + "。"}


sub_builder = StateGraph(state_schema=SubgraphState)
sub_builder.add_node("subgraph_strip_node", subgraph_strip_node)
sub_builder.add_node("subgraph_punctuate_node", subgraph_punctuate_node)
sub_builder.add_edge(START, "subgraph_strip_node")
sub_builder.add_edge("subgraph_strip_node", "subgraph_punctuate_node")
sub_builder.add_edge("subgraph_punctuate_node", END)

subgraph = sub_builder.compile()


class ParentState(TypedDict):
    input_text: str
    cleaned_text: str


def call_subgraph(state: ParentState) -> ParentState:
    subgraph_result = subgraph.invoke({"raw_text": state["input_text"]})
    return {"cleaned_text": subgraph_result["punctuated_text"]}


parent_builder = StateGraph(state_schema=ParentState)
parent_builder.add_node("call_subgraph", call_subgraph)
parent_builder.add_edge(START, "call_subgraph")
parent_builder.add_edge("call_subgraph", END)

checkpointer = InMemorySaver()
parent_graph = parent_builder.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    config = {"configurable": {"thread_id": "observe_checkpoint_1"}}
    input_text = "   LangGraph 真有意思        "

    result = parent_graph.invoke({"input_text": input_text}, config=config)
    print("原始文本：", repr(input_text))
    print("清洗后的文本：", result["cleaned_text"])

    snapshot = parent_graph.get_state(config)
    print("\n当前检查点 values：", snapshot.values)
    print("下一个待执行节点：", snapshot.next)

    print("\n检查点历史：")
    for item in parent_graph.get_state_history(config):
        print(
            "step =", item.metadata.get("step"),
            "| next =", item.next,
            "| values =", item.values,
        )
