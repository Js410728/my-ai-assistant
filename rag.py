import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import json
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

# 初始化嵌入模型
embedding_model = SentenceTransformer('paraphrase-MiniLM-L3-v2')

# 存储文档内容列表
documents = []
# 存储文档向量（后续用于检索）
doc_vectors = []

def add_documents(docs, ids):
    """将文档添加到向量库中"""
    global documents, doc_vectors
    if not docs:
        return
    # 生成向量
    vectors = embedding_model.encode(docs)
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
    query_vec = embedding_model.encode([query])
    # 计算相似度（使用余弦相似度）
    # FAISS 默认用 L2 距离，我们用归一化后的内积近似余弦相似度
    # 归一化向量
    vectors_norm = doc_vectors / np.linalg.norm(doc_vectors, axis=1, keepdims=True)
    query_norm = query_vec / np.linalg.norm(query_vec, axis=1, keepdims=True)
    # 构建索引
    dim = doc_vectors.shape[1]
    index = faiss.IndexFlatIP(dim)  # 内积索引（归一化后相当于余弦相似度）
    index.add(vectors_norm.astype(np.float32))
    # 检索
    distances, indices = index.search(query_norm.astype(np.float32), n_results)
    # 收集结果
    results = []
    for idx in indices[0]:
        if idx < len(documents):
            results.append(documents[idx])
    return results

# 如果需要持久化存储，可以将 documents 和 doc_vectors 保存到文件
# 但作为演示，先放在内存中