"""综合示例：条件入口、普通边、条件终止放在同一张订单图里。

普通订单且金额 <= 1000：
  START → quick_check → decide → END

重要订单且金额 > 5000：
  START → full_check → decide → manual_review → END
"""

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class OrderState(TypedDict, total=False):
    order_type: str
    amount: float
    approved: bool
    result: str


def entry_router(state: OrderState) -> Literal["quick_check", "full_check"]:
    if state["order_type"] == "normal":
        return "quick_check"
    return "full_check"


def quick_check(state: OrderState) -> dict[str, bool | str]:
    approved = state["amount"] <= 1000
    return {"approved": approved, "result": "快速校验完成"}


def full_check(state: OrderState) -> dict[str, bool | str]:
    approved = state["amount"] <= 5000
    return {"approved": approved, "result": "完整校验完成"}


def decide(state: OrderState) -> None:
    return None


def decision_router(state: OrderState) -> Literal["manual_review", END]:
    if state["approved"]:
        return END
    return "manual_review"


def manual_review(state: OrderState) -> dict[str, bool | str]:
    return {"approved": True, "result": "人工审核通过"}


builder = StateGraph(state_schema=OrderState)
builder.add_node("quick_check", quick_check)
builder.add_node("full_check", full_check)
builder.add_node("decide", decide)
builder.add_node("manual_review", manual_review)

builder.add_conditional_edges(START, entry_router)
builder.add_edge("quick_check", "decide")
builder.add_edge("full_check", "decide")
builder.add_conditional_edges("decide", decision_router)
builder.add_edge("manual_review", END)

graph = builder.compile()


if __name__ == "__main__":
    print(
        graph.invoke(
            {
                "order_type": "normal",
                "amount": 800,
            }
        )
    )
    print(
        graph.invoke(
            {
                "order_type": "important",
                "amount": 8000,
            }
        )
    )
