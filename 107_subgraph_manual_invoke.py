"""子图（手动调用）：父节点里 subgraph.invoke，字段显式映射。

流程：
父图 START → call_subgraph → END
子图 START → strip → punctuate → END

父子状态可完全不同；每次 invoke 都是全新子图执行。
不需要模型或 API Key。
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class SubgraphState(TypedDict):
    raw_text: str
    stripped_text: str
    punctuated_text: str


def subgraph_strip_node(state: SubgraphState) -> SubgraphState:
    stripped_text = state["raw_text"].strip()
    return {"stripped_text": stripped_text}


def subgraph_punctuate_node(state: SubgraphState) -> SubgraphState:
    punctuated_text = state["stripped_text"] + "。"
    return {"punctuated_text": punctuated_text}


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

parent_graph = parent_builder.compile()


if __name__ == "__main__":
    input_text = "   LangGraph 真有意思        "
    result = parent_graph.invoke({"input_text": input_text})

    print("原始文本：", repr(input_text))
    print("清洗后的文本：", result["cleaned_text"])
