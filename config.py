# ============================================
# 全局配置文件
# 所有 API Key、路径、常量统一管理
# ============================================

import os
from dotenv import load_dotenv

# 加载 .env 文件（包含 DEEPSEEK_API_KEY 等）
load_dotenv()

# ============================================
# API 配置
# ============================================

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# ============================================
# 模型配置
# ============================================

MODEL_NAME = "deepseek-v4-pro"

# ============================================
# 文件路径配置
# ============================================

CITY_FILE_PATH = "china_city.txt"

# ============================================
# 数据库配置
# ============================================

MEMORY_DB_PATH = "permanent_memory.db"
CHECKPOINT_DB_PATH = "checkpoints.db"