import streamlit as st
import asyncio
import sys
import os
import json
import requests
import rag
import time
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
    st.subheader("📚 扩展知识库")
    with st.form(key="add_knowledge_form"):
        new_knowledge = st.text_area("输入新的知识点：", placeholder="例如：公司每年有12天带薪病假。")
        submit = st.form_submit_button("添加到知识库")
        if submit and new_knowledge.strip():
            doc_id = f"user_{int(time.time())}"
            rag.add_documents([new_knowledge.strip()], [doc_id])
            st.success(f"✅ 已添加：{new_knowledge.strip()[:30]}...")
            # 不再调用 st.rerun()，避免前端冲突
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
    # 1. 显示用户消息
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
    
    # 2. 准备助手回答区域
    with st.chat_message("assistant"):
        # 先显示一个思考中的状态
        placeholder = st.empty()
        placeholder.info("🤔 思考中...")
        
        try:
            # 调用 Agent
            response = asyncio.run(run_agent(
                user_input, 
                st.session_state.conversation_history
            ))
            
            # 3. 用 CSS 动画一次性显示回答（保留打字效果，避免 DOM 冲突）
            placeholder.markdown(f"""
<style>
    .typing {{
        animation: typewriter {min(len(response) * 0.02, 3)}s steps({len(response)}) forwards;
        overflow: hidden;
        white-space: pre-wrap;
        word-break: break-word;
    }}
    @keyframes typewriter {{
        from {{ width: 0; }}
        to {{ width: 100%; }}
    }}
</style>
<div class="typing">{response}</div>
""", unsafe_allow_html=True)
            
            # 4. 更新会话历史
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.conversation_history.append({"role": "user", "content": user_input})
            st.session_state.conversation_history.append({"role": "assistant", "content": response})
            if len(st.session_state.conversation_history) > 6:
                st.session_state.conversation_history = st.session_state.conversation_history[-6:]
                
        except Exception as e:
            error_msg = f"❌ 出错了：{str(e)}"
            placeholder.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})