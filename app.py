import streamlit as st
import asyncio
import sys
import os

# 导入你原来的 Agent 核心（复用代码，不重复造轮子！）
# 注意：需要把 weather.py 中的 run_agent 等函数导入进来
sys.path.append(os.path.dirname(__file__))
from weather import run_agent

# ============================================
# 页面配置（必须放在最前面）
# ============================================
st.set_page_config(
    page_title="🤖 智能助手",
    page_icon="🤖",
    layout="centered"
)

# ============================================
# 界面标题
# ============================================
st.title("🤖 我的超级智能助手")
st.caption("支持天气查询 · 未来预报 · 刚学会，后期更新其他内容")

# ============================================
# 侧边栏：功能介绍
# ============================================
with st.sidebar:
    st.header("💡 使用说明")
    st.markdown("""
    **你可以问我：**
    - 🌤️ 广州天气怎么样
    - 📅 新乡未来3天天气
    - 📰 今天有什么热点新闻
    - 📈 特斯拉股价多少
    - 🌍 对比广州和新乡天气
    
    **提示**：城市名请用拼音（如 `guangzhou`、`xinxiang`、`beijing`）
    """)
    st.divider()
    st.caption("v1.0 · 基于 DeepSeek Agent")

# ============================================
# 初始化聊天历史（存到 session_state 中，刷新页面不丢数据）
# ============================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "👋 你好！我是你的智能助手，可以帮你查天气。有什么可以帮你的吗？"}
    ]

# ============================================
# 显示历史聊天记录
# ============================================
for msg in st.session_state.messages:
    with st.chat_message(msg["" \
    "role"]):
        st.write(msg["content"])

# ============================================
# 输入框（用户打字的地方）
# ============================================
user_input = st.chat_input("请输入你的问题...")

if user_input:
    # 1. 把用户消息加入历史并显示
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
    
    # 2. 调用 Agent（复用 weather.py 中的 run_agent）
    with st.chat_message("assistant"):
        with st.spinner("🤔 思考中..."):
            try:
                # 注意：run_agent 是异步函数，需要 asyncio.run 执行
                response = asyncio.run(run_agent(user_input))
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                error_msg = f"❌ 出错了：{str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})