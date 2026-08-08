# ============================================
# Agent 统一入口模块
# 这是整个系统的"门面"，app.py 只需要调用这里
# ============================================

import asyncio
from graph import AGENT_GRAPH
from memory import get_user_preference, set_user_preference
from city_utils import extract_city_from_text


# ============================================
# 主入口函数
# ============================================

async def run_agent(user_query: str, user_id: str = "default_user", thread_id: str = None):
    """
    Agent 统一入口
    user_query: 用户输入的问题
    user_id: 用户唯一标识（用于永久记忆）
    thread_id: 会话ID（用于 LangGraph 状态恢复）
    """
    if thread_id is None:
        thread_id = user_id

    # ============================================
    # 提前保存城市（让下一次提问能记住）
    # ============================================
    city = extract_city_from_text(user_query)
    if city:
        set_user_preference(user_id, "default_city", city)
        print(f"📝 提前保存城市：{city}")

    # ============================================
    # 构建初始状态
    # ============================================
    initial_state = {
        "messages": [{"role": "user", "content": user_query}],
        "tool_calls": [],
        "tool_results": [],
        "final_answer": "",
        "user_id": user_id
    }

    # ============================================
    # 调用 LangGraph
    # ============================================
    config = {"configurable": {"thread_id": thread_id}}
    final_state = await AGENT_GRAPH.ainvoke(initial_state, config=config)

    return final_state.get('final_answer', '')


# ============================================
# 同步版本（方便 streamlit 调用）
# ============================================

def run_agent_sync(user_query: str, user_id: str = "default_user", thread_id: str = None):
    """
    同步版本，方便在 Streamlit 中直接调用
    """
    return asyncio.run(run_agent(user_query, user_id, thread_id))


# ============================================
# 快速测试
# ============================================

if __name__ == "__main__":
    async def test():
        result = await run_agent("广州今天天气怎么样", user_id="test_user")
        print(f"📢 测试结果：{result[:100]}...")

    asyncio.run(test())