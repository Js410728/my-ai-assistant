import streamlit as st
import asyncio
import sys
import os
import json
import requests
import rag
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
# 加载示例文档到知识库（用于测试 RAG）
# ============================================
import rag
sample_docs = [
    "公司员工每年享有5天带薪年假。",
    "请假需要提前3天在OA系统提交申请。",
    "公司提供免费的咖啡和下午茶。",
    "上班时间是上午9点到下午6点。",
]
# 为每个文档生成一个唯一ID
doc_ids = [f"doc_{i}" for i in range(len(sample_docs))]
rag.add_documents(sample_docs, doc_ids)
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
        #---- 新增：RAG 检索逻辑 ----
    # 从知识库中检索与用户问题相关的文档片段
    retrieved_chunks = rag.query_knowledge_base(user_input)
    context = "\n\n".join(retrieved_chunks) if retrieved_chunks else ""
    
    # 构建包含上下文的系统提示词
    system_prompt = "你是一个智能助手，根据用户问题自动调用合适的工具获取信息。"
    if context:
        system_prompt += f"\n\n请基于以下参考资料回答用户的问题。如果参考资料中没有相关信息，请如实告知。\n\n参考资料：\n{context}"
    # ---- RAG 逻辑结束 ----
    
    # 2. 调用 Agent（非流式）
    with st.chat_message("assistant"):
        with st.spinner("🤔 思考中..."):
            try:
                # 注意：这里不需要修改，run_agent 会自动使用我们构建好的 messages
                # 但我们之前没有把 messages 传进去？实际上 run_agent 内部会自己构建 messages
                # 所以我们需要改用另一种方式：直接调用 call_llm 或者修改 run_agent
                # 为了最小改动，我们保持 run_agent 不变，而是把检索到的上下文加到 user_input 里
                # 或者直接给 run_agent 传一个额外的 context 参数
                
                # 最简单的方式：把上下文拼到用户输入里
                enhanced_input = user_input
                if context:
                    enhanced_input = f"【参考资料】\n{context}\n\n【用户问题】\n{user_input}"
                # 使用原来的 run_agent（非流式）
                response = asyncio.run(run_agent(enhanced_input, st.session_state.conversation_history))
                
                # 3. 模拟逐字输出
                placeholder = st.empty()
                full_response = ""
                for char in response:
                    full_response += char
                    placeholder.write(full_response + "▌")
                    import time
                    time.sleep(0.02)  # 每字间隔20ms
                placeholder.write(full_response)
                
                # 4. 更新会话历史
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.session_state.conversation_history.append({"role": "user", "content": user_input})
                st.session_state.conversation_history.append({"role": "assistant", "content": response})
                if len(st.session_state.conversation_history) > 6:
                    st.session_state.conversation_history = st.session_state.conversation_history[-6:]
                    
            except Exception as e:
                error_msg = f"❌ 出错了：{str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})