"""子图（节点挂载）：compile 产物直接交给 add_node。

流程：
父图 START → subgraph_node → END
子图 START → strip → punctuate → END

父子共享状态字段；框架自动进入/退出子图并合并状态。
不需要模型或 API Key。
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class SharedState(TypedDict):
    raw_text: str
    cleaned_text: str


def subgraph_strip_node(state: SharedState) -> SharedState:
    stripped_text = state["raw_text"].strip()
    return {"cleaned_text": stripped_text}


def subgraph_punctuate_node(state: SharedState) -> SharedState:
    punctuated_text = state["cleaned_text"] + "。"
    return {"cleaned_text": punctuated_text}


sub_builder = StateGraph(state_schema=SharedState)
sub_builder.add_node("subgraph_strip_node", subgraph_strip_node)
sub_builder.add_node("subgraph_punctuate_node", subgraph_punctuate_node)
sub_builder.add_edge(START, "subgraph_strip_node")
sub_builder.add_edge("subgraph_strip_node", "subgraph_punctuate_node")
sub_builder.add_edge("subgraph_punctuate_node", END)

subgraph = sub_builder.compile()


parent_builder = StateGraph(state_schema=SharedState)
parent_builder.add_node("subgraph_node", subgraph)
parent_builder.add_edge(START, "subgraph_node")
parent_builder.add_edge("subgraph_node", END)

parent_graph = parent_builder.compile()


if __name__ == "__main__":
    raw_text = "   LangGraph 真有意思        "
    result = parent_graph.invoke({"raw_text": raw_text})

    print("原始文本：", repr(raw_text))
    print("清洗后的文本：", result["cleaned_text"])
