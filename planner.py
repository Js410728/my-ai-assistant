# planner.py
import json
from weather import call_llm

def plan_steps(user_query: str):
    prompt = f"""
你是一个任务规划专家。用户提出了一个复杂需求，请把它拆解成多个简单、可执行的步骤。

⚠️ 重要限制：
- 你可以使用以下工具：get_weather、get_weather_forecast、get_hot_news、get_stock_price、get_express、get_current_date
- 如果用户需求涉及“当前日期”、“今天”、“下周”，必须先用 get_current_date 获取准确日期。
- 如果用户需求超出了这些工具的范围，请用“基于知识推理”的方式完成该步骤。

用户需求：{user_query}

请以JSON格式输出，格式如下：
[
    "步骤1：查询北京7月28-30日天气（用 get_weather 工具，参数 city='北京'）",
    "步骤2：基于知识推理，推荐北京出差期间的酒店（建议三里屯、国贸附近，预算500-800元/晚）"
]

注意：只输出JSON数组，不要输出其他内容。
"""
    # ... 后面代码不变
    response = call_llm([
        {"role": "system", "content": "你是一个任务规划专家，擅长把复杂问题拆解成具体步骤。"},
        {"role": "user", "content": prompt}
    ])
    # 解析JSON
    try:
        content = response['choices'][0]['message']['content']
        # 提取JSON部分（有时模型会额外输出文字）
        start = content.find('[')
        end = content.rfind(']') + 1
        if start != -1 and end != -1:
            return json.loads(content[start:end])
        else:
            return json.loads(content)
    except Exception as e:
        print(f"⚠️ 规划步骤失败：{e}")
        return [f"直接回答用户：{user_query}"]