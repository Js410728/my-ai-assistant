# ============================================
# RAG 知识库模块（使用 fastembed，轻量无依赖）
# ============================================

import os
import numpy as np
from fastembed import TextEmbedding
import faiss

# 初始化嵌入模型（fastembed 自动下载，只需几十 MB）
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

# 存储文档内容列表
documents = []
doc_vectors = []

def add_documents(docs, ids):
    """将文档添加到向量库中"""
    global documents, doc_vectors
    if not docs:
        return
    # 生成向量
    vectors = list(embedding_model.embed(docs))
    vectors = np.array(vectors)
    if len(doc_vectors) == 0:
        doc_vectors = vectors
    else:
        doc_vectors = np.vstack([doc_vectors, vectors])
    documents.extend(docs)
    print(f"✅ 成功添加 {len(docs)} 个文档片段到知识库。")

def query_knowledge_base(query, n_results=3):
    """检索最相关的文档片段"""
    if len(documents) == 0:
        return []
    # 将查询转为向量
    query_vec = list(embedding_model.embed([query]))[0]
    query_vec = np.array(query_vec).reshape(1, -1)
    # 归一化向量
    vectors_norm = doc_vectors / np.linalg.norm(doc_vectors, axis=1, keepdims=True)
    query_norm = query_vec / np.linalg.norm(query_vec, axis=1, keepdims=True)
    # 构建索引
    dim = doc_vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors_norm.astype(np.float32))
    # 检索
    distances, indices = index.search(query_norm.astype(np.float32), n_results)
    # 收集结果
    results = []
    for idx in indices[0]:
        if idx < len(documents):
            results.append(documents[idx])
    return results

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