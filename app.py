import streamlit as st
import asyncio
import sys
import os
import json
import requests
import rag
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(__file__))
from weather import call_llm_stream, tools, run_agent

st.set_page_config(
    page_title="🤖 智能助手",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 我的超级智能助手")
st.caption("支持天气查询 · 未来预报 · 刚学会，后期更新其他内容")

# ============================================
# 侧边栏
# ============================================
with st.sidebar:
    st.header("💡 使用说明")
    st.markdown("""
    **你可以问我：**
    - 🌤️ 广州天气怎么样
    - 📅 我可以帮你解析PDF、excle、word等文件并汇总报告
    - 📰 查询分析基金收益情况及推荐
    - 📈 知识库检索
    - 🌍 根据实时天气、交通等情况为你规划出行指南
    
    **提示**：城市名请用拼音（如 `guangzhou`、`xinxiang`、`beijing`）
    """)
    st.divider()
    
    enable_multi_agent = st.checkbox("启用多智能体模式", value=False)
    st.divider()
    
    st.subheader("📚 扩展知识库")
    with st.form(key="add_knowledge_form"):
        new_knowledge = st.text_area("输入新的知识点：", placeholder="例如：公司每年有12天带薪病假。")
        submit = st.form_submit_button("添加到知识库")
        if submit and new_knowledge.strip():
            doc_id = f"user_{int(time.time())}"
            rag.add_documents([new_knowledge.strip()], [doc_id])
            st.success(f"✅ 已添加：{new_knowledge.strip()[:30]}...")
            st.rerun()
    
    st.divider()
    st.subheader("📁 已上传的文件")
    with st.expander("点击展开/折叠文件列表"):
        file_list = rag.get_file_names()
        if file_list:
            for fname in file_list:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"📄 {fname}")
                with col2:
                    if st.button("🗑️", key=f"del_{fname}"):
                        if rag.delete_file_by_name(fname):
                            st.success(f"已删除 {fname}")
                            st.rerun()
                        else:
                            st.error(f"删除 {fname} 失败")
            st.caption(f"共 {len(file_list)} 个文件")
        else:
            st.info("暂无已上传的文件")
    
    st.subheader("📤 上传文件到知识库")
    uploaded_file = st.file_uploader(
        "支持 PDF、TXT、Excel (.xlsx/.xls)",
        type=["pdf", "txt", "xlsx", "xls"]
    )
    if st.button("🗑️ 清空知识库"):
        rag.clear_knowledge_base()
        st.success("知识库已清空")
        st.rerun()
    
    if uploaded_file:
        temp_path = f"./temp_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        try:
            text = rag.extract_text_from_file(temp_path)
            if text.strip():
                chunks = [chunk.strip() for chunk in text.split('\n\n') if chunk.strip()]
                if len(chunks) < 2:
                    chunks = [sent.strip() for sent in text.split('。') if sent.strip()]
                doc_ids = [f"file_{uploaded_file.name}_{i}_{int(time.time())}" for i in range(len(chunks))]
                rag.add_documents(chunks, doc_ids, file_name=uploaded_file.name)
                st.success(f"✅ 已解析并添加 {len(chunks)} 条知识")
                #st.rerun()
            else:
                st.warning("⚠️ 文件内容为空或无法解析")
        except Exception as e:
            st.error(f"❌ 解析失败：{str(e)}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    st.caption("v1.0 · 基于 DeepSeek Agent")

# ============================================
# 初始化聊天历史
# ============================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "👋 你好！我是你的智能助手，可以帮你查天气。有什么可以帮你的吗？"}
    ]

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ============================================
# 用户输入
# ============================================
user_input = st.chat_input("请输入你的问题...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
    
    # 检索知识库
    retrieved_chunks = rag.query_knowledge_base(user_input)
    context = "\n\n".join(retrieved_chunks) if retrieved_chunks else ""
    enhanced_input = user_input
    if context:
        enhanced_input = f"【参考资料】\n{context}\n\n【用户问题】\n{user_input}"
    
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.info("🤔 思考中...")
        try:
            # 根据开关选择 Agent
            if enable_multi_agent:
                from multi_agent import supervisor
                response = asyncio.run(supervisor(enhanced_input, st.session_state.conversation_history))
            else:
                response = asyncio.run(run_agent(enhanced_input, st.session_state.conversation_history))
            
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
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.conversation_history.append({"role": "user", "content": user_input})
            st.session_state.conversation_history.append({"role": "assistant", "content": response})
            if len(st.session_state.conversation_history) > 6:
                st.session_state.conversation_history = st.session_state.conversation_history[-6:]
        except Exception as e:
            error_msg = f"❌ 出错了：{str(e)}"
            placeholder.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})