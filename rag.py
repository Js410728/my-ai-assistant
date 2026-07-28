# ============================================
# RAG 知识库模块（支持本地持久化存储）
# ============================================

import os
import numpy as np
import pickle
from fastembed import TextEmbedding
import faiss

# 数据持久化文件路径
DOCS_FILE = "docs.pkl"          # 用于存储文本列表
VECTORS_FILE = "vectors.npy"    # 用于存储向量数组
FILE_NAMES_FILE = "file_names.pkl"   # 用于存储文件名列表
file_names = []   # 存储已上传的文件名

# 初始化嵌入模型
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en")

# 存储文档内容列表和向量（全局变量）
documents = []
doc_vectors = None

# ============================================
# 1. 加载持久化数据（如果存在）
# ============================================
def load_knowledge_base():
    """启动时自动从硬盘加载之前保存的知识库"""
    global documents, doc_vectors, file_names   # 添加 file_names
    
    if os.path.exists(DOCS_FILE) and os.path.exists(VECTORS_FILE):
        try:
            with open(DOCS_FILE, 'rb') as f:
                documents = pickle.load(f)
            doc_vectors = np.load(VECTORS_FILE)
            print(f"✅ 成功从本地加载知识库，共 {len(documents)} 条记录")
        except Exception as e:
            print(f"⚠️ 加载知识库失败：{e}，将使用空知识库")
            documents = []
            doc_vectors = None
         # 加载文件名列表
        if os.path.exists(FILE_NAMES_FILE):
            try:
                with open(FILE_NAMES_FILE, 'rb') as f:
                    file_names = pickle.load(f)
                print(f"✅ 成功加载文件名列表，共 {len(file_names)} 个文件")
            except Exception as e:
                print(f"⚠️ 加载文件名列表失败：{e}")
                file_names = []
        else:
            file_names = []
    else:
        print("📭 未找到本地知识库文件，将使用空知识库")
        documents = []
        doc_vectors = None
        file_names = []

   
# ============================================
# 2. 保存知识库到硬盘
# ============================================
def save_knowledge_base():
    global documents, doc_vectors, file_names
    try:
        with open(DOCS_FILE, 'wb') as f:
            pickle.dump(documents, f)
        if doc_vectors is not None:
            np.save(VECTORS_FILE, doc_vectors)
        with open(FILE_NAMES_FILE, 'wb') as f:
            pickle.dump(file_names, f)
        print(f"✅ 成功保存知识库到本地，共 {len(documents)} 条记录，{len(file_names)} 个文件")
    except Exception as e:
        print(f"❌ 保存知识库失败：{e}")
def get_file_names():
    """返回已上传的文件名列表"""
    return file_names

# ============================================
# 3. 清空知识库（保留初始化状态）
# ============================================
def clear_knowledge_base():
    """手动清空所有知识库数据"""
    global documents, doc_vectors
    documents = []
    doc_vectors = None
    # 同时删除本地文件
    if os.path.exists(DOCS_FILE):
        os.remove(DOCS_FILE)
    if os.path.exists(VECTORS_FILE):
        os.remove(VECTORS_FILE)
    if os.path.exists(FILE_NAMES_FILE):
        os.remove(FILE_NAMES_FILE)
    print("🗑️ 知识库已清空")

# ============================================
# 4. 添加文档到知识库
# ============================================
def add_documents(docs, ids, file_name=None):
    global documents, doc_vectors, file_names
    if not docs:
        return
    
    # 生成向量
    vectors = list(embedding_model.embed(docs))
    vectors = np.array(vectors)
    
    if len(documents) == 0:
        doc_vectors = vectors
    else:
        doc_vectors = np.vstack([doc_vectors, vectors])
    
    documents.extend(docs)
    print(f"✅ 成功添加 {len(docs)} 个文档片段到知识库")
    if file_name and file_name not in file_names:
        file_names.append(file_name)
    
    # 🔥 关键：每次添加后自动保存到硬盘
    save_knowledge_base()
def delete_file_by_name(file_name):
    """
    根据文件名删除知识库中对应的所有文档片段
    """
    global documents, doc_vectors, file_names
    if file_name not in file_names:
        print(f"⚠️ 文件 {file_name} 不存在于知识库中")
        return False

# ============================================
# 5. 检索文档
# ============================================
def query_knowledge_base(query, n_results=3):
    """检索最相关的文档片段"""
    if len(documents) == 0 or doc_vectors is None:
        return []
    
    # 将查询转为向量
    query_vec = list(embedding_model.embed([query]))[0]
    query_vec = np.array(query_vec).reshape(1, -1)
    
    # 归一化向量
    vectors_norm = doc_vectors / np.linalg.norm(doc_vectors, axis=1, keepdims=True)
    query_norm = query_vec / np.linalg.norm(query_vec, axis=1, keepdims=True)
    
    # 构建 FAISS 索引并检索
    dim = doc_vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors_norm.astype(np.float32))
    distances, indices = index.search(query_norm.astype(np.float32), n_results) 
    # 收集结果
    results = []
    for idx in indices[0]:
        if idx < len(documents):
            results.append(documents[idx])
    return results

# ============================================
# 6. 文件解析函数（保持不变）
# ============================================
def extract_text_from_pdf(file_path: str) -> str:
    """从 PDF 文件中提取所有文本"""
    import pypdf
    text = ""
    with open(file_path, 'rb') as f:
        reader = pypdf.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def extract_text_from_excel(file_path: str) -> str:
    """从 Excel 文件中提取所有文本"""
    import pandas as pd
    df = pd.read_excel(file_path, engine='openpyxl')
    text = ""
    for col in df.columns:
        col_text = " ".join([str(v) for v in df[col].dropna() if str(v).strip()])
        if col_text:
            text += f"{col}: {col_text}\n"
    return text

def extract_text_from_file(file_path: str) -> str:
    """根据文件扩展名自动选择解析方式"""
    if file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    elif file_path.endswith(('.xlsx', '.xls')):
        return extract_text_from_excel(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {file_path}")

# ============================================
# 7. 启动时自动加载知识库
# ============================================
load_knowledge_base()