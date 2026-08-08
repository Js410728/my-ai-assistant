# ============================================
# 大模型通信模块
# 负责：调用 DeepSeek API（普通 + 流式）
# ============================================

import requests
from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, MODEL_NAME

# ============================================
# 普通调用（非流式）
# ============================================

def call_llm(messages, tools=None):
    """
    调用 DeepSeek 大模型 API（同步请求）
    messages: 对话历史列表
    tools: 工具定义列表（可选）
    返回：API 响应的 JSON 字典
    """
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto"
    }
    resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=120)
    return resp.json()


# ============================================
# 流式调用
# ============================================

def call_llm_stream(messages, tools=None):
    """
    流式调用 DeepSeek API
    返回：原始响应对象（可迭代）
    """
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "stream": True
    }
    response = requests.post(
        DEEPSEEK_API_URL,
        headers=headers,
        json=payload,
        stream=True,
        timeout=120
    )
    return response


# ============================================
# 快速测试（直接运行此文件时生效）
# ============================================

if __name__ == "__main__":
    # 简单测试
    test_messages = [{"role": "user", "content": "你好，请简单介绍一下你自己"}]
    try:
        result = call_llm(test_messages)
        content = result['choices'][0]['message']['content']
        print(f"🧪 测试调用成功！\n回复：{content[:100]}...")
    except Exception as e:
        print(f"❌ 测试失败：{e}")