"""Agent Chat 对话图：工具调用前 interrupt，支持同意 / 拒绝 / 编辑。

流程：
START → llm_node ⇄ tool_node → END

llm_node 调用绑定工具的模型。
tool_node 对本轮全部 tool_calls 发起一次审批中断，再按 decisions 下标逐个处理。
交给 langgraph dev 时 compile() 不传 checkpointer；持久化由服务器提供。

前端 Agent Chat 的 assistant/graph id 填 langgraph.json 中的键 chat_graph。
"""

from typing import Literal

from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.types import interrupt

from langchain.messages import ToolMessage
from langchain.tools import tool
from langchain_deepseek import ChatDeepSeek


# ----------------------------------------------------------------------
# 1. 模型
# ----------------------------------------------------------------------
# 这里直接读取环境变量里的凭据，不在代码中硬编码任何密钥。
# extra_body 关掉思维链输出，让返回内容更干净，便于前端渲染。
model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={
        "thinking": {
            "type": "disabled"
        }
    }
)


# ----------------------------------------------------------------------
# 2. 工具
# ----------------------------------------------------------------------
# parse_docstring=True 让 LangChain 从 docstring 的 Args 段自动抽取参数说明，
# 这些说明会随工具 schema 一起发给模型，描述写得越清楚，模型填参越准。
@tool(parse_docstring=True)
def get_weather(city: str) -> str:
    """
    根据城市名称，查询当日天气。

    Args:
        city: 城市名称
    """
    # 演示用的假实现。真实场景在这里调用天气服务。
    return f"{city} 今天天气很好"


tools = [get_weather]

# 名字到工具对象的映射。模型返回的 tool_call 只带工具名，
# 需要靠这张表找回真正可执行的对象。
tools_by_name = {
    current_tool.name: current_tool
    for current_tool in tools
}

# 把工具 schema 绑定到模型上，模型才知道自己有哪些工具可用。
model_with_tools = model.bind_tools(tools)


# ----------------------------------------------------------------------
# 3. 模型节点
# ----------------------------------------------------------------------
def llm_node(state: MessagesState) -> dict:
    """把当前完整对话历史交给模型，产出下一条 AI 消息。

    返回的消息可能带 tool_calls（要调工具），也可能是纯文本（直接回答）。
    MessagesState 的 messages 字段是追加语义，返回列表即为追加。
    """
    response = model_with_tools.invoke(state["messages"])

    return {
        "messages": [response]
    }


# ----------------------------------------------------------------------
# 4. 工具节点：执行前先中断，等人审批
# ----------------------------------------------------------------------
def tool_node(state: MessagesState) -> dict:
    """对本轮所有工具调用发起一次审批中断，再按决策逐个处理。"""
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls

    # 关键设计：一次 interrupt 提交本轮全部待审批的工具调用。
    # 不要在循环里逐个 interrupt，那样恢复顺序会变得很难对齐。
    #
    # payload 里两个字段的分工：
    #   action_requests  告诉前端「要审什么」：工具名、参数、给人看的说明
    #   review_configs   告诉前端「能怎么审」：每个工具允许哪些决策类型
    # 前端据此渲染出同意 / 拒绝 / 编辑的操作入口。
    resume_value = interrupt({
        "action_requests": [
            {
                "name": tool_call["name"],
                "args": tool_call["args"],
                "description": (
                    f"是否允许调用工具 {tool_call['name']}，"
                    f"参数为 {tool_call['args']}？"
                ),
            }
            for tool_call in tool_calls
        ],
        "review_configs": [
            {
                "action_name": tool_call["name"],
                "allowed_decisions": [
                    "approve",
                    "reject",
                    "edit",
                ],
            }
            for tool_call in tool_calls
        ],
    })

    # 恢复执行后，resume_value 就是外部回传的决策包。
    # decisions 与 tool_calls 按下标一一对应。
    decisions = resume_value.get("decisions", [])
    tool_messages = []

    for index, tool_call in enumerate(tool_calls):
        # 决策数量少于工具数量时，缺失的部分按「拒绝」兜底。
        # 这是安全默认值：宁可不执行，也不要在没人表态的情况下放行。
        decision = (
            decisions[index]
            if index < len(decisions)
            else {"type": "reject"}
        )

        decision_type = decision.get("type")

        if decision_type == "approve":
            # 同意：用模型原本给出的参数执行
            selected_tool = tools_by_name[tool_call["name"]]
            result = selected_tool.invoke(tool_call["args"])

        elif decision_type == "edit":
            # 编辑：丢弃模型参数，改用人改过的参数执行
            edited_action = decision["edited_action"]
            edited_args = edited_action["args"]

            selected_tool = tools_by_name[tool_call["name"]]
            result = selected_tool.invoke(edited_args)

        else:
            # 拒绝（以及任何无法识别的决策类型）：不执行工具，
            # 把人填的理由当作结果；没填理由就用默认话术。
            result = decision.get(
                "message",
                "用户拒绝调用该工具",
            )

        # 不论执行与否，都必须产出一条 ToolMessage，
        # 且 tool_call_id 要与原 tool_call 对应。
        # 缺了这条消息，下一轮模型会因为「有调用无结果」而报错。
        tool_messages.append(
            ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"],
            )
        )

    return {
        "messages": tool_messages
    }


# ----------------------------------------------------------------------
# 5. 路由
# ----------------------------------------------------------------------
def router(
    state: MessagesState,
) -> Literal["tool_node", END]:
    """模型这轮要调工具就去 tool_node，否则本轮对话结束。"""
    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "tool_node"

    return END


# ----------------------------------------------------------------------
# 6. 组图
# ----------------------------------------------------------------------
builder = StateGraph(state_schema=MessagesState)

builder.add_node("llm_node", llm_node)
builder.add_node("tool_node", tool_node)

builder.add_edge(START, "llm_node")

# 条件边：第三个参数声明所有可能的去向，供可视化与校验使用
builder.add_conditional_edges(
    "llm_node",
    router,
    ["tool_node", END],
)

# 工具执行完回到模型，让它根据工具结果组织最终回答
builder.add_edge("tool_node", "llm_node")

# 注意：这里不传 checkpointer。
# 开发服务器会自己注入持久化层，代码里再带一个会导致装载失败。
chat_graph = builder.compile()
