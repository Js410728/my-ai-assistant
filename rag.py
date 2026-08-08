# ============================================
# RAG 知识库模块（支持持久化 + 文件删除 + doc_meta）
# ============================================

import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
import numpy as np
import pickle
from fastembed import TextEmbedding
import faiss

# 数据持久化文件路径
DOCS_FILE = "docs.pkl"          # 存储文档内容列表 (list of str)
VECTORS_FILE = "vectors.npy"    # 存储向量数组 (numpy array)
FILE_NAMES_FILE = "file_names.pkl"   # 存储文件名列表 (list of str)
DOC_META_FILE = "doc_meta.pkl"  # 存储每个文档对应的文件名 (list of str, 与 documents 一一对应)
# 初始化嵌入模型
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en")

# 全局变量
documents = []      # 文本列表
doc_vectors = None  # 向量数组 (numpy)
file_names = []     # 文件名列表
doc_meta = []       # 每个文档对应的文件名（与 documents 索引对齐）

# ============================================
# 1. 加载持久化数据（自动迁移旧数据）
# ============================================
def load_knowledge_base():
    global documents, doc_vectors, file_names, doc_meta
    
    if os.path.exists(DOCS_FILE) and os.path.exists(VECTORS_FILE):
        try:
            with open(DOCS_FILE, 'rb') as f:
                documents = pickle.load(f)
            doc_vectors = np.load(VECTORS_FILE)
            print(f"✅ 成功加载知识库，共 {len(documents)} 条记录")
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

        # 加载文档元数据（文件名映射）
        if os.path.exists(DOC_META_FILE):
            try:
                with open(DOC_META_FILE, 'rb') as f:
                    doc_meta = pickle.load(f)
                print(f"✅ 成功加载文档元数据，共 {len(doc_meta)} 条记录")
                # 如果 doc_meta 长度与 documents 不一致，则重建
                if len(doc_meta) != len(documents):
                    print("⚠️ doc_meta 长度与 documents 不一致，将重建...")
                    rebuild_doc_meta()
            except Exception as e:
                print(f"⚠️ 加载文档元数据失败：{e}，将重建")
                rebuild_doc_meta()
        else:
            print("📭 未找到 doc_meta 文件，将重建...")
            rebuild_doc_meta()
    else:
        print("📭 未找到本地知识库文件，将使用空知识库")
        documents = []
        doc_vectors = None
        file_names = []
        doc_meta = []

def rebuild_doc_meta():
    """根据现有数据重建 doc_meta（用于旧数据迁移）"""
    global doc_meta, file_names
    # 如果 file_names 为空，则无法映射，将 doc_meta 设为 None 列表
    if not file_names:
        doc_meta = [None] * len(documents)
        print("⚠️ file_names 为空，doc_meta 设为 None")
        return
    # 如果只有一个文件，全部归为那个文件名
    if len(file_names) == 1:
        doc_meta = [file_names[0]] * len(documents)
        print(f"✅ 根据唯一文件名 '{file_names[0]}' 重建 doc_meta")
    else:
        # 多个文件，无法准确重建，设为 'unknown' 并提示
        doc_meta = ['unknown'] * len(documents)
        print("⚠️ 存在多个文件，无法准确重建映射，所有文档标记为 'unknown'")
        print("💡 建议：清空知识库后重新上传所有文件，以建立正确映射")

# ============================================
# 2. 保存知识库到硬盘
# ============================================
def save_knowledge_base():
    global documents, doc_vectors, file_names, doc_meta
    try:
        with open(DOCS_FILE, 'wb') as f:
            pickle.dump(documents, f)
        if doc_vectors is not None:
            np.save(VECTORS_FILE, doc_vectors)
        with open(FILE_NAMES_FILE, 'wb') as f:
            pickle.dump(file_names, f)
        with open(DOC_META_FILE, 'wb') as f:
            pickle.dump(doc_meta, f)
        print(f"✅ 成功保存知识库，{len(documents)} 条记录，{len(file_names)} 个文件")
    except Exception as e:
        print(f"❌ 保存知识库失败：{e}")

# ============================================
# 3. 获取文件名列表
# ============================================
def get_file_names():
    return file_names

# ============================================
# 4. 清空知识库
# ============================================
def clear_knowledge_base():
    global documents, doc_vectors, file_names, doc_meta
    documents = []
    doc_vectors = None
    file_names = []
    doc_meta = []
    for f in [DOCS_FILE, VECTORS_FILE, FILE_NAMES_FILE, DOC_META_FILE]:
        if os.path.exists(f):
            os.remove(f)
    print("🗑️ 知识库已清空")

# ============================================
# 5. 添加文档到知识库
# ============================================
def add_documents(docs, ids, file_name=None):
    global documents, doc_vectors, file_names, doc_meta
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
    # 记录每个文档对应的文件名
    if file_name:
        doc_meta.extend([file_name] * len(docs))
        if file_name not in file_names:
            file_names.append(file_name)
    else:
        doc_meta.extend([None] * len(docs))
    
    print(f"✅ 成功添加 {len(docs)} 个文档片段到知识库")
    save_knowledge_base()

# ============================================
# 6. 删除单个文件
# ============================================
def delete_file_by_name(file_name):
    global documents, doc_vectors, file_names, doc_meta
    
    if file_name not in file_names:
        print(f"⚠️ 文件 {file_name} 不存在于知识库中")
        return False
    
    # 找出所有不属于该文件的文档索引
    keep_indices = [i for i, f in enumerate(doc_meta) if f != file_name]
    if len(keep_indices) == len(documents):
        print(f"⚠️ 未找到属于文件 {file_name} 的文档，可能元数据不一致")
        return False
    
    # 更新 documents 和 doc_meta
    documents = [documents[i] for i in keep_indices]
    doc_meta = [doc_meta[i] for i in keep_indices]
    
    # 更新向量数组
    if len(keep_indices) > 0:
        doc_vectors = doc_vectors[keep_indices]
    else:
        doc_vectors = None
    
    file_names.remove(file_name)
    
    print(f"🗑️ 已删除文件 {file_name}，剩余 {len(documents)} 条记录")
    save_knowledge_base()
    return True

# ============================================
# 7. 检索文档
# ============================================
def query_knowledge_base(query, n_results=3):
    if len(documents) == 0 or doc_vectors is None:
        return []
    
    query_vec = list(embedding_model.embed([query]))[0]
    query_vec = np.array(query_vec).reshape(1, -1)
    
    vectors_norm = doc_vectors / np.linalg.norm(doc_vectors, axis=1, keepdims=True)
    query_norm = query_vec / np.linalg.norm(query_vec, axis=1, keepdims=True)
    
    dim = doc_vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors_norm.astype(np.float32))
    distances, indices = index.search(query_norm.astype(np.float32), n_results)
    
    results = []
    for idx in indices[0]:
        if idx < len(documents):
            results.append(documents[idx])
    return results

# ============================================
# 8. 文件解析函数
# ============================================
def extract_text_from_pdf(file_path: str) -> str:
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
    """从 Excel 文件中提取所有文本，支持 .xlsx 和 .xls"""
    import pandas as pd
    # 根据扩展名选择引擎
    if file_path.endswith('.xls'):
        engine = 'xlrd'  # 需要 pip install xlrd
    else:
        engine = 'openpyxl'
    df = pd.read_excel(file_path, engine=engine)
    text = ""
    for col in df.columns:
        col_text = " ".join([str(v) for v in df[col].dropna() if str(v).strip()])
        if col_text:
            text += f"{col}: {col_text}\n"
    return text

def extract_text_from_file(file_path: str) -> str:
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
# 9. 启动时自动加载
# ============================================
load_knowledge_base()