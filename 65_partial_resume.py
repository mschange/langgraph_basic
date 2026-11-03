"""部分恢复：先只回答姓名，年龄中断继续保留，再单独交回年龄。

这不是 64 的默认流程。恢复键仍然是中断 ID。
只恢复姓名后，业务状态里只有 username，next 里还剩下 request_age。

运行：python 65_partial_resume.py
"""

from importlib import import_module

from langgraph.types import Command

demo = import_module("64_parallel_interrupt")


def main() -> None:
    graph = demo.build_graph()
    config = {"configurable": {"thread_id": "partial-profile-demo"}}
    first_result = graph.invoke({}, config=config)

    by_field = {
        pending.value["field"]: pending for pending in first_result["__interrupt__"]
    }
    partial_result = graph.invoke(
        Command(resume={by_field["username"].id: "林同学"}),
        config=config,
    )
    print("部分恢复返回：", partial_result)
    print("部分恢复后的业务状态：", graph.get_state(config).values)
    print("仍待执行的节点：", graph.get_state(config).next)

    remaining_interrupt = partial_result["__interrupt__"][0]
    final_result = graph.invoke(
        Command(resume={remaining_interrupt.id: 24}),
        config=config,
    )
    print("全部恢复后的业务状态：", final_result)
    print("完成后待执行的节点：", graph.get_state(config).next)


if __name__ == "__main__":
    main()
