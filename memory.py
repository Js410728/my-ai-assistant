# memory.py
import sqlite3
from datetime import datetime
import json

DB_PATH = "permanent_memory.db"

def init_db():
    """初始化永久记忆数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 用户画像表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            default_city TEXT,
            default_fund_code TEXT,
            preferred_response_style TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    
    # 用户偏好表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            key TEXT,
            value TEXT,
            confidence INTEGER DEFAULT 50,
            updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
        )
    ''')
    
    # 对话摘要表（长期记忆压缩）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            summary TEXT,
            date TEXT,
            FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 永久记忆数据库初始化完成")

# ============================================
# 用户画像操作
# ============================================

def get_user_profile(user_id: str):
    """获取用户画像"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, default_city, default_fund_code, preferred_response_style FROM user_profiles WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"name": row[0], "default_city": row[1], "default_fund_code": row[2], "preferred_response_style": row[3]}
    return None

def update_user_profile(user_id: str, **kwargs):
    """更新用户画像（如果不存在则创建）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 先检查是否存在
    cursor.execute("SELECT user_id FROM user_profiles WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone()
    
    now = datetime.now().isoformat()
    
    if exists:
        # 更新
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [now, user_id]
        cursor.execute(f"UPDATE user_profiles SET {set_clause}, updated_at = ? WHERE user_id = ?", values)
    else:
        # 插入
        columns = ["user_id", "created_at", "updated_at"] + list(kwargs.keys())
        placeholders = ["?"] * len(columns)
        values = [user_id, now, now] + list(kwargs.values())
        cursor.execute(f"INSERT INTO user_profiles ({', '.join(columns)}) VALUES ({', '.join(placeholders)})", values)
    
    conn.commit()
    conn.close()
    return True

# ============================================
# 用户偏好操作
# ============================================

def get_user_preference(user_id: str, key: str):
    """获取用户某个偏好（按更新时间取最新）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT value, confidence FROM user_preferences WHERE user_id = ? AND key = ? ORDER BY updated_at DESC LIMIT 1",
        (user_id, key)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"value": row[0], "confidence": row[1]}
    return None

def set_user_preference(user_id: str, key: str, value: str, confidence: int = 50):
    """设置或更新用户偏好"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO user_preferences (user_id, key, value, confidence, updated_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, key, value, confidence, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    print(f"✅ 已写入偏好：{key} = {value} (user: {user_id})")  # 添加这行
    return True

# ============================================
# 对话摘要操作
# ============================================

def add_conversation_summary(user_id: str, summary: str):
    """保存对话摘要"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversation_summaries (user_id, summary, date) VALUES (?, ?, ?)",
        (user_id, summary, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_conversation_summaries(user_id: str, limit: int = 5):
    """获取最近的对话摘要"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT summary, date FROM conversation_summaries WHERE user_id = ? ORDER BY date DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"summary": row[0], "date": row[1]} for row in rows]
def clear_all_preferences():
    """清空所有偏好数据（谨慎使用）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_preferences")
    conn.commit()
    conn.close()
    print("🗑️ 已清空所有偏好数据")

# ============================================
# 初始化
# ============================================
init_db()