import streamlit as st
import asyncio
import sys
import os
import json
import requests
from dotenv import load_dotenv

# 导入你原来的 Agent 核心（复用代码，不重复造轮子！）
# 注意：需要把 weather.py 中的 run_agent 等函数导入进来
sys.path.append(os.path.dirname(__file__))
from weather import call_llm_stream, tools, run_agent

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
# 对话历史（用于 Agent 的记忆）
# ============================================
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []   # 存储结构：[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
# ============================================
# 显示历史聊天记录
# ============================================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
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
    
     # 2. 构建消息（包含历史）
    messages = [
        {"role": "system", "content": "你是一个智能助手，根据用户问题自动调用合适的工具获取信息。你可以使用的工具包括：get_weather（天气查询）、get_weather_forecast（天气预报）、get_hot_news（热门新闻）、get_stock_price（股票价格）。请注意，你没有 web_search 工具。"}
    ]
    if st.session_state.conversation_history:
        recent = st.session_state.conversation_history[-6:] if len(st.session_state.conversation_history) > 6 else st.session_state.conversation_history
        messages.extend(recent)
    messages.append({"role": "user", "content": user_input})

    # 3. 调用流式 API
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        
        try:
            # 调用流式 API
            stream_response = call_llm_stream(messages, tools=tools)
            
            # 解析流式响应（SSE 格式）
            for line in stream_response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # 去掉 "data: " 前缀
                        if data == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            if 'choices' in chunk and len(chunk['choices']) > 0:
                                delta = chunk['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta.get('content', '')   # 如果 content 不存在或为 None，返回空字符串
                                    if content:
                                        full_response += content
                                        placeholder.write(full_response + "▌")
                        except json.JSONDecodeError:
                            pass
            
            # 最终去掉光标
            placeholder.write(full_response)
            
            # 4. 更新会话历史
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.session_state.conversation_history.append({"role": "user", "content": user_input})
            st.session_state.conversation_history.append({"role": "assistant", "content": full_response})
            if len(st.session_state.conversation_history) > 6:
                st.session_state.conversation_history = st.session_state.conversation_history[-6:]
                
        except Exception as e:
            error_msg = f"❌ 出错了：{str(e)}"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})