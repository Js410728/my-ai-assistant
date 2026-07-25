import os
import asyncio
import requests
import json
import aiohttp
from dotenv import load_dotenv

load_dotenv()


# ============================================
# 1. 异步工具函数
# ============================================

async def get_hot_news():
    """返回模拟热门新闻（用于测试）"""
    return """📰 今日热门新闻（模拟数据）：
  1. 全国多地迎来高温天气
  2. AI Agent 技术持续升温
  3. 特斯拉发布新款车型
  4. 电影暑期档票房突破纪录
  5. 国际油价小幅回升"""
async def get_stock_price(symbol: str):
    """查询股票实时价格（使用 yfinance）"""
    import yfinance as yf  # 在函数内导入，避免文件顶部缺少包导致整体报错
    try:
        # 用 asyncio.to_thread 将同步操作转为异步，避免阻塞
        stock = await asyncio.to_thread(yf.Ticker, symbol)
        info = await asyncio.to_thread(stock.info)
        price = info.get('regularMarketPrice')
        if price:
            return f"📈 {symbol.upper()} 当前股价：{price} USD"
        else:
            return f"未找到股票 {symbol}，请检查代码（如 AAPL, TSLA, 0700.HK）"
    except Exception as e:
        return f"股票查询异常：{str(e)}"
async def get_express(company: str, number: str):
    """查询快递物流信息（模拟数据）"""
    # 模拟物流轨迹（实际项目中这里替换为真实API请求）
    return f"""
📦 快递公司：{company}
📋 运单编号：{number}
🕒 最后更新：2025-07-26 14:30
📌 当前位置：【郑州市】 郑东新区中转站
📝 最新轨迹：
  1. [2025-07-26 14:30] 您的包裹已到达【郑州市】郑东新区中转站
  2. [2025-07-26 08:15] 包裹已离开【武汉市】华中分拨中心，发往【郑州市】
  3. [2025-07-25 22:00] 包裹已从【深圳】发出
🏷️ 预计送达：2025-07-28 18:00前
    """
async def get_weather(city: str):
    """异步查询当前天气"""
    url = f"https://wttr.in/{city}?format=j1"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    current = data['current_condition'][0]
                    temp = current['temp_C']
                    desc = current['weatherDesc'][0]['value']
                    humidity = current['humidity']
                    wind = current['windspeedKmph']
                    return f"{city}当前天气：{desc}，温度{temp}°C，湿度{humidity}%，风速{wind}km/h。"
                return f"天气查询失败，状态码：{response.status}"
        except Exception as e:
            return f"天气服务异常：{str(e)}"

async def get_weather_forecast(city: str, days: int = 3):
    """异步查询未来几天的天气预报"""
    url = f"https://wttr.in/{city}?format=j1"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    forecasts = data['weather'][1:days+1]
                    if not forecasts:
                        return f"无法获取{city}的预报数据"
                    result = f"📍 {city}未来{days}天天气：\n"
                    for day in forecasts:
                        date = day['date']
                        max_t = day['maxtempC']
                        min_t = day['mintempC']
                        desc = day['hourly'][0]['weatherDesc'][0]['value']
                        result += f"  📅 {date}：{desc}，{min_t}°C ~ {max_t}°C\n"
                    return result.strip()
                return f"预报查询失败，状态码：{response.status}"
        except Exception as e:
            return f"预报服务异常：{str(e)}"


# ============================================
# 2. 大模型调用（同步，用于获取意图和总结）
# ============================================

def call_llm(messages, tools=None):
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    URL = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-v4-pro",
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto"
    }
    resp = requests.post(URL, headers=headers, json=payload, timeout=30)
    return resp.json()


# ============================================
# 3. 工具说明书
# ============================================

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市当前的实时天气，当用户问'现在'天气时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市拼音，如 guangzhou"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_forecast",
            "description": "查询指定城市未来几天的天气预报，当用户问'未来几天'、'周末'、'明天'天气时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市拼音，如 xinxiang"},
                    "days": {"type": "integer", "description": "未来多少天，默认3，最多7", "default": 3}
                },
                "required": ["city"]
            }
        }
    },   # ← 这里添加了逗号
    {
        "type": "function",
        "function": {
            "name": "get_hot_news",
            "description": "查询当前最新的热门新闻，当用户问'今天有什么新闻'、'热点'时使用",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "查询指定股票的实时价格，当用户问'股价'、'股票'时使用。请用美股代码如 AAPL, TSLA",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "股票代码，例如：AAPL, TSLA, 0700.HK"}
                },
                "required": ["symbol"]
            }
        }
    },
        # ... 之前的 tools 定义 ... ,
    {
        "type": "function",
        "function": {
            "name": "get_express",
            "description": "查询快递物流信息，当用户提供快递单号或询问物流进度时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string", "description": "快递公司名称，如：顺丰、中通、圆通"},
                    "number": {"type": "string", "description": "快递单号，如：SF1234567890"}
                },
                "required": ["company", "number"]
            }
        }
    },
]
# ============================================
# 4. Agent 核心执行函数（支持并发）
# ============================================

async def run_agent(user_query):
    messages = [
        {"role": "system", "content": "你是一个智能助手，根据用户问题自动调用合适的工具获取信息。你可以使用的工具包括：get_weather（天气查询）、get_weather_forecast（天气预报）、get_hot_news（热门新闻）、get_stock_price（股票价格）。请注意，你没有 web_search 工具。"},
        {"role": "user", "content": user_query}
    ]
    
    response_data = call_llm(messages, tools=tools)
    if "error" in response_data:
        return f"❌ API错误：{response_data['error'].get('message', '未知错误')}"
    
    choice = response_data['choices'][0]
    message = choice['message']
    
    if message.get('tool_calls'):
        tool_calls = message['tool_calls']
        
        async def execute_tool(tool_call):
            tool_name = tool_call['function']['name']
            args = json.loads(tool_call['function']['arguments'])
            
            if tool_name == "get_weather":
                return await get_weather(args['city'])
            elif tool_name == "get_weather_forecast":
                days = args.get('days', 3)
                return await get_weather_forecast(args['city'], days)
            elif tool_name == "get_hot_news":
                return await get_hot_news()
            elif tool_name == "get_stock_price":
                return await get_stock_price(args['symbol'])
            elif tool_name == "get_express":
                return await get_express(args['company'], args['number']) 
            else:
                return "未知工具"
            
        
        results = await asyncio.gather(*[execute_tool(tc) for tc in tool_calls])
        
        messages.append(message)
        for i, tool_call in enumerate(tool_calls):
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call['id'],
                "content": results[i]
            })
        
        final_resp = call_llm(messages)
        return final_resp['choices'][0]['message']['content']
    else:
        return message['content']


# ============================================
# 5. 交互式主入口
# ============================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🤖 智能天气助手已启动（支持多城市并发查询）")
    print("💡 输入 'q' 或 '退出' 结束对话")
    print("="*50 + "\n")
    
    while True:
        user_input = input("👤 你：")
        if user_input.lower() in ['q', 'quit', '退出']:
            print("👋 再见！")
            break
        if not user_input.strip():
            continue
        
        print("🤖 助手：", end="", flush=True)
        response = asyncio.run(run_agent(user_input))
        print(response + "\n")