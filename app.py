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
#import rag
#sample_docs = [
    #"公司员工每年享有5天带薪年假。",
    #"请假需要提前3天在OA系统提交申请。",
    #"公司提供免费的咖啡和下午茶。",
    #"上班时间是上午9点到下午6点。",
#]
# 为每个文档生成一个唯一ID
#doc_ids = [f"doc_{i}" for i in range(len(sample_docs))]
#rag.add_documents(sample_docs, doc_ids)
# ============================================
# 界面标题
# ============================================
st.title("🤖 我的超级智能助手")
st.caption("支持天气查询 · 未来预报 · 刚学会，后期更新其他内容")

# ============================================
# 侧边栏：功能介绍
# ============================================
# app.py 侧边栏添加
enable_multi_agent = st.checkbox("启用多智能体模式", value=False)
with st.sidebar:
    st.header("💡 使用说明")
    st.markdown("""
    **你可以问我：**
    - 🌤️ 广州天气怎么样
    - 📅 我可以帮你解析PDF、excle、word等文件
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
            st.rerun()
            # 不再调用 st.rerun()，避免前端冲突
    st.divider()
    st.subheader("📁 已上传的文件")

    # 使用 expander 实现可折叠列表
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
    if uploaded_file:
        # 保存临时文件
        temp_path = f"./temp_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # 解析并添加到知识库
        try:
            text = rag.extract_text_from_file(temp_path)
            if text.strip():
                # 按段落切分（每个段落作为一个知识块）
                chunks = [chunk.strip() for chunk in text.split('\n\n') if chunk.strip()]
                # 如果段落太少，按句子切分
                if len(chunks) < 2:
                    chunks = [sent.strip() for sent in text.split('。') if sent.strip()]
                # 生成唯一 ID
                import time
                doc_ids = [f"file_{uploaded_file.name}_{i}_{int(time.time())}" for i in range(len(chunks))]
                rag.add_documents(chunks, doc_ids,file_name=uploaded_file.name)
                st.success(f"✅ 已解析并添加 {len(chunks)} 条知识")
            else:
                st.warning("⚠️ 文件内容为空或无法解析")
        except Exception as e:
            st.error(f"❌ 解析失败：{str(e)}")
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)

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
    # 2. 从知识库检索相关内容
    retrieved_chunks = rag.query_knowledge_base(user_input)
    context = "\n\n".join(retrieved_chunks) if retrieved_chunks else ""
    
    # 3. 构建增强后的用户输入（把检索到的知识作为上下文）
    enhanced_input = user_input
    if context:
        enhanced_input = f"【参考资料】\n{context}\n\n【用户问题】\n{user_input}"
    # 2. 准备助手回答区域 ， 调用 Agent
    with st.chat_message("assistant"):
        # 先显示一个思考中的状态
        placeholder = st.empty()
        placeholder.info("🤔 思考中...")
        try:
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
            if enable_multi_agent:
                from multi_agent import supervisor
                response = asyncio.run(supervisor(enhanced_input, st.session_state.conversation_history))
            else:
                response = asyncio.run(run_agent(enhanced_input, st.session_state.conversation_history))
        except Exception as e:
            error_msg = f"❌ 出错了：{str(e)}"
            placeholder.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})