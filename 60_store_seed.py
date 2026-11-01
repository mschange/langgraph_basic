"""写入长期记忆：把三个用户的偏好保存到 PostgreSQL store。

命名空间是 ("users", 用户名)，键是 "preferences"。
61_long_term_memory.py 会按这个结构读取。

前置：本机 PostgreSQL 已创建 langgraph_user / langgraph_db。
"""

from typing import Final

from langgraph.store.postgres import PostgresStore

DB_URL = "postgresql://langgraph_user:123456@localhost:5432/langgraph_db?sslmode=disable"
USERS_NS: Final[tuple[str, ...]] = ("users",)
PREFERENCES_KEY: Final[str] = "preferences"

PREFERENCES = {
    "Alice": {
        "food": "紫光园奶皮子酸奶",
        "sports": "跑步",
        "course": "计算机组成原理",
    },
    "Bob": {
        "food": "奶皮子糖葫芦",
        "sports": "跑步",
        "course": "数字电路与模拟电路",
    },
    "Black": {
        "food": "紫光园奶皮子酸奶",
        "sports": "羽毛球",
        "course": "数字电路与模拟电路",
    },
}


def main() -> None:
    with PostgresStore.from_conn_string(DB_URL) as store:
        store.setup()
        for username, preferences in PREFERENCES.items():
            store.put((*USERS_NS, username), PREFERENCES_KEY, preferences)

        for item in store.search(USERS_NS):
            print(item)


if __name__ == "__main__":
    main()
