# ============================================
# Streamlit 界面
# 这是用户交互的入口
# ============================================

import streamlit as st
import asyncio
import sys
import os
import time

# 确保项目根目录在 Python 路径中
sys.path.append(os.path.dirname(__file__))

# ============================================
# 导入新模块
# ============================================

from agent import run_agent_sync
import rag

# ============================================
# 页面配置
# ============================================

st.set_page_config(
    page_title="🤖 智能助手",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 我的超级智能助手")
st.caption("支持天气查询 · 基金查询 · 知识库检索 · 出行规划")

# ============================================
# 侧边栏
# ============================================

with st.sidebar:
    st.header("💡 使用说明")
    st.markdown("""
    **你可以问我：**
    - 🌤️ 广州天气怎么样
    - 📈 查询基金收益及推荐
    - 📚 上传 PDF/Excel 分析
    - 🌍 根据实时天气规划出行
    
    **提示**：城市名用拼音（如 `guangzhou`）
    """)
    st.divider()

    # ==========================================
# 用户身份（带确认按钮）
# ==========================================
    st.subheader("👤 用户身份")

    # 初始化 session_state 中的 user_id
    if "user_id" not in st.session_state:
        st.session_state.user_id = "default_user"
    if "user_id_saved" not in st.session_state:
        st.session_state.user_id_saved = False

    # 输入框：显示当前值，允许修改
    input_user_id = st.text_input(
        "请输入你的用户ID",
        value=st.session_state.user_id,
        help="输入后点击「确认」按钮生效"
    )
    col1, col2 = st.columns([1, 3])
    # 确认按钮
    with col1:
    # 根据保存状态改变按钮文字和颜色
        if st.session_state.user_id_saved:
            st.success("✅ 已保存")
        else:
            if st.button("💾 确认", type="primary"):
                if input_user_id.strip():
                    st.session_state.user_id = input_user_id.strip()
                    st.session_state.user_id_saved = True
                    st.success(f"✅ 用户ID已更新为：{st.session_state.user_id}")
                    st.rerun()
                else:
                    st.warning("⚠️ 用户ID不能为空")

    with col2:
        st.caption(f"👤 当前用户：**{st.session_state.user_id}**")
        if st.session_state.user_id_saved:
            st.caption("✅ 已保存到会话")

    # 显示当前使用的 ID
    st.caption(f"当前用户：{st.session_state.user_id}")

    # 清除记忆按钮
    if st.button("🗑️ 清除我的记忆", type="secondary"):
        from memory import clear_user_memory
        if clear_user_memory(st.session_state.user_id):
            st.success(f"✅ 已清除用户 {st.session_state.user_id} 的所有记忆")
            st.rerun()
        else:
            st.error("❌ 清除记忆失败")

    st.divider()

    # ==========================================
    # 知识库管理
    # ==========================================
    st.subheader("📚 扩展知识库")

    with st.form(key="add_knowledge_form"):
        new_knowledge = st.text_area(
            "输入新的知识点：",
            placeholder="例如：公司每年有12天带薪病假。"
        )
        submit = st.form_submit_button("添加到知识库")
        if submit and new_knowledge.strip():
            doc_id = f"user_{int(time.time())}"
            rag.add_documents([new_knowledge.strip()], [doc_id])
            st.success(f"✅ 已添加：{new_knowledge.strip()[:30]}...")
            st.rerun()

    st.divider()

    # ==========================================
    # 文件管理
    # ==========================================
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
            else:
                st.warning("⚠️ 文件内容为空或无法解析")
        except Exception as e:
            st.error(f"❌ 解析失败：{str(e)}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    st.caption("v2.0 · 模块化重构版")


# ============================================
# 初始化聊天历史
# ============================================

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "👋 你好！我是你的智能助手。有什么可以帮你的吗？"}
    ]

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []


# ============================================
# 显示历史消息
# ============================================

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])


# ============================================
# 用户输入
# ============================================

user_input = st.chat_input("请输入你的问题...")

if user_input:
    # 显示用户消息
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # 检索知识库
    retrieved_chunks = rag.query_knowledge_base(user_input)
    context = "\n\n".join(retrieved_chunks) if retrieved_chunks else ""
    enhanced_input = user_input
    if context:
        enhanced_input = f"【参考资料】\n{context}\n\n【用户问题】\n{user_input}"

    # 调用 Agent
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.info("🤔 思考中...")

        try:
            # 使用新的统一入口
            response = run_agent_sync(
                enhanced_input,
                user_id=st.session_state.user_id, 
                thread_id=st.session_state.user_id, 
            )

            # 显示回答
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

            # 更新历史
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.conversation_history.append({"role": "user", "content": user_input})
            st.session_state.conversation_history.append({"role": "assistant", "content": response})

            if len(st.session_state.conversation_history) > 6:
                st.session_state.conversation_history = st.session_state.conversation_history[-6:]

        except Exception as e:
            error_msg = f"❌ 出错了：{str(e)}"
            placeholder.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})