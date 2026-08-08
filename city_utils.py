# ============================================
# 城市工具模块
# 负责：加载城市列表、从文本中提取城市名
# ============================================

import os
from config import CITY_FILE_PATH

# ============================================
# 加载城市列表
# ============================================

def load_city_list(file_path=CITY_FILE_PATH):
    """
    从文本文件中读取城市列表，每行一个城市名
    返回一个列表
    """
    cities = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                city = line.strip()
                if city:  # 跳过空行
                    cities.append(city)
        print(f"✅ 已加载 {len(cities)} 个城市")
    except FileNotFoundError:
        print(f"⚠️ 未找到城市列表文件：{file_path}，将使用默认城市列表")
        # 备用默认城市
        cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "郑州", "南京", "西安", "重庆", "天津", "苏州", "长沙", "青岛", "沈阳"]
    return cities

# ============================================
# 全局城市列表（按长度从长到短排序）
# 避免“南宁”误匹配“南”
# ============================================

CITY_LIST = sorted(load_city_list(), key=len, reverse=True)

# ============================================
# 从文本中提取城市名
# ============================================

def extract_city_from_text(text: str) -> str:
    """
    从文本中提取城市名
    支持：
    - 用户说"新乡" → 匹配到"新乡市"
    - 用户说"新乡市" → 匹配到"新乡市"
    - 用户说"郑州市" → 匹配到"郑州市"
    """
    if not text:
        return None
    
    # 第一轮：精确匹配（城市列表中的原名）
    for city in CITY_LIST:
        if city in text:
            return city
    
    # 第二轮：去掉"市"字匹配
    # 如果城市名以"市"结尾，尝试去掉"市"后匹配
    for city in CITY_LIST:
        if city.endswith('市'):
            city_without_shi = city[:-1]  # 去掉最后一个"市"字
            if city_without_shi in text:
                return city
    
    # 第三轮：如果用户输入以"市"结尾，尝试去掉"市"后匹配
    # 例如用户说"新乡市"，我们去掉"市"变成"新乡"再匹配
    if text.endswith('市'):
        text_without_shi = text[:-1]
        for city in CITY_LIST:
            if city == text_without_shi or city == text:
                return city
    
    return None


# ============================================
# 快速测试（直接运行此文件时生效）
# ============================================

if __name__ == "__main__":
    test_text = "广州天气"
    result = extract_city_from_text(test_text)
    print(f"🧪 测试提取：'{test_text}' → '{result}'")