"""单节点串行中断：同一节点内依次收集用户名、年龄和选项。

流程：
START → get_info_node → END

节点内三个 interrupt() 按代码顺序触发，不是一次返回三个待答问题。
每次恢复后节点从头重执行；已回答的中断按顺序重放历史值。
局部变量在节点 return 前不写入业务状态。

本例用标量 Command(resume=...) 逐次恢复，不使用中断 ID 映射。
不需要模型或 API Key。InMemorySaver 只在当前进程有效。
"""

from typing import Literal, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt


Gender = Literal["male", "female"]


class UserInfoState(TypedDict, total=False):
    # 三项数据会在节点全部完成后一次性提交给业务状态。
    username: str
    age: int
    gender: Gender


def get_info_node(state: UserInfoState) -> UserInfoState:
    # 三次恢复都会从头进入节点，这条日志一共出现四次。
    print("[节点] 进入信息收集节点")

    # 顺序固定；恢复时已经回答过的问题会返回历史恢复值。
    username = interrupt("请输入您的用户名：")
    print(f"[节点] 已取得用户名：{username}")

    age = interrupt("请输入您的年龄：")
    print(f"[节点] 已取得年龄：{age}")

    gender = interrupt("请输入您的性别：(male/female)")
    print(f"[节点] 已取得性别选项：{gender}")

    # 中途的局部变量不等于已写入状态；直到这里才更新三个字段。
    return {"username": username, "age": age, "gender": gender}


def build_graph() -> CompiledStateGraph:
    builder = StateGraph(state_schema=UserInfoState)
    builder.add_node("get_info_node", get_info_node)
    builder.add_edge(START, "get_info_node")
    builder.add_edge("get_info_node", END)
    return builder.compile(checkpointer=InMemorySaver())


def read_age(prompt: str) -> int:
    while True:
        raw_age = input(prompt)
        try:
            age = int(raw_age)
        except ValueError:
            print("年龄必须是整数，请重新输入。")
        else:
            if age < 0:
                print("年龄不能为负数，请重新输入。")
                continue
            return age


def read_gender(prompt: str) -> Gender:
    # 这两个值是本例的输入选项，并非完整的性别分类。
    while True:
        value = input(f"{prompt}：").strip().lower()
        if value in {"male", "female"}:
            return "male" if value == "male" else "female"
        print("本示例只接受 male 或 female，请重新输入。")


def main() -> None:
    graph = build_graph()
    config: RunnableConfig = {
        "configurable": {"thread_id": "sequential-info-demo"}
    }

    print("\n1. 首次执行：等待用户名")
    username_result = graph.invoke({}, config=config)
    print("首次返回：", username_result)
    print("业务状态：", graph.get_state(config).values)
    username = input(username_result["__interrupt__"][0].value)

    print("\n2. 恢复用户名中断：继续等待年龄")
    age_result = graph.invoke(Command(resume=username), config=config)
    print("第二次返回：", age_result)
    print("业务状态：", graph.get_state(config).values)
    age = read_age(age_result["__interrupt__"][0].value)

    print("\n3. 恢复年龄中断：继续等待性别选项")
    gender_result = graph.invoke(Command(resume=age), config=config)
    print("第三次返回：", gender_result)
    print("业务状态：", graph.get_state(config).values)
    gender = read_gender(gender_result["__interrupt__"][0].value)

    print("\n4. 恢复最后一个中断：提交全部信息")
    final_result = graph.invoke(Command(resume=gender), config=config)
    print("最终业务状态：", final_result)
    print("完成后待执行的节点：", graph.get_state(config).next)


if __name__ == "__main__":
    # 模块可以被其他代码导入，不会自动启动终端交互。
    main()
