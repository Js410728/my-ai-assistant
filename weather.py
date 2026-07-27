# ============================================
# 导入所需的 Python 库
# ============================================

import os
# os：操作系统接口模块，用于读取环境变量（如从 .env 文件中获取 API Key）
# 在代码中通过 os.getenv("DEEPSEEK_API_KEY") 读取 DeepSeek 的密钥

import asyncio
# asyncio：Python 内置的异步 I/O 库，支持 async/await 语法
# 用于并发执行多个工具调用（如同时查询多个城市的天气），提升效率

import requests
# requests：同步 HTTP 请求库，用于向 DeepSeek 大模型 API 发送 POST 请求
# 这里只用于调用大模型（因为大模型调用通常是单次请求，不需要并发）

import json
# json：用于解析和生成 JSON 格式的数据
# 大模型返回的 tool_calls 参数是 JSON 字符串，需要用 json.loads() 解析

import aiohttp
# aiohttp：异步 HTTP 客户端，用于异步调用外部 API（如天气、新闻接口）
# 与 requests 不同，aiohttp 支持 async/await，适合并发请求

from dotenv import load_dotenv
# python-dotenv：用于从 .env 文件中加载环境变量到 Python 进程
# 这样可以把 API Key 等敏感信息放在 .env 文件中，避免硬编码在代码里

load_dotenv()
# 执行加载 .env 文件的操作。默认会在当前目录查找 .env 文件
# 加载后，可以通过 os.getenv("变量名") 读取

from datetime import datetime
# ============================================
# 1. 异步工具函数（Agent 可以调用的工具）
# ============================================
async def get_current_date():
    """获取当前日期和星期几"""
    now = datetime.now()
    return f"今天是 {now.strftime('%Y年%m月%d日')}，星期{['一','二','三','四','五','六','日'][now.weekday()]}"
async def get_hot_news():
    """
    获取热门新闻（当前为模拟数据，用于测试）
    async 关键字表示这是一个异步函数，可以被 await 调用
    返回值：一段包含模拟新闻标题的字符串
    """
    # 三引号 """...""" 表示多行字符串，保留换行和缩进
    return """📰 今日热门新闻（模拟数据）：
  1. 全国多地迎来高温天气
  2. AI Agent 技术持续升温
  3. 特斯拉发布新款车型
  4. 电影暑期档票房突破纪录
  5. 国际油价小幅回升"""


async def get_stock_price(symbol: str):
    """
    查询股票实时价格（使用 yfinance 库）
    symbol: 股票代码（如 AAPL, TSLA）
    返回值：包含股票价格的字符串
    """
    import yfinance as yf  # 在函数内导入，避免文件顶部缺少包导致整体报错
    # 如果 yfinance 未安装，只有在调用这个函数时才会报错，不影响其他功能
    try:
        # asyncio.to_thread 把同步函数（yfinance）放到后台线程执行，不阻塞事件循环
        # 因为 yfinance 不支持异步，直接用会阻塞整个 Agent
        stock = await asyncio.to_thread(yf.Ticker, symbol)
        # yf.Ticker(symbol) 创建一个股票对象
        
        info = await asyncio.to_thread(stock.info)
        # stock.info 获取股票的详细信息（包含价格、市值等）
        
        price = info.get('regularMarketPrice')
        # 从 info 字典中提取 'regularMarketPrice'（当前市价）
        # 如果取不到，返回 None
        
        if price:
            return f"📈 {symbol.upper()} 当前股价：{price} USD"
            # symbol.upper() 把股票代码转成大写（如 aapl → AAPL）
        else:
            return f"未找到股票 {symbol}，请检查代码（如 AAPL, TSLA, 0700.HK）"
    except Exception as e:
        # 捕获所有异常，返回友好的错误信息，避免程序崩溃
        return f"股票查询异常：{str(e)}"


async def get_express(company: str, number: str):
    """
    查询快递物流信息（当前为模拟数据）
    company: 快递公司名称（如：顺丰、中通）
    number: 快递单号（如：SF1234567890）
    返回值：包含物流轨迹的字符串
    """
    # 实际项目中可替换为快递100、菜鸟裹裹等真实 API
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
    """
    异步查询当前天气（使用 wttr.in 免费接口）
    city: 城市拼音（如 guangzhou, xinxiang）
    返回值：包含天气信息的字符串
    """
    # f"{city}" 是 f-string，把变量插入字符串中
    # ?format=j1 表示返回 JSON 格式的数据（便于解析）
    url = f"https://wttr.in/{city}?format=j1"
    
    # async with 是异步上下文管理器，自动管理资源的打开和关闭
    # ClientSession 是 aiohttp 的会话对象，用于发送 HTTP 请求
    async with aiohttp.ClientSession() as session:
        try:
            # session.get(url, timeout=10) 发起异步 GET 请求，超时 10 秒
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    # HTTP 状态码 200 表示请求成功
                    # content_type=None：忽略响应头中的 MIME 类型，强制解析 JSON
                    data = await response.json(content_type=None)
                    
                    # data['current_condition'] 是一个列表，取第一个元素 [0]
                    current = data['current_condition'][0]
                    temp = current['temp_C']         # 摄氏温度
                    desc = current['weatherDesc'][0]['value']  # 天气描述（晴、多云等）
                    humidity = current['humidity']   # 湿度百分比
                    wind = current['windspeedKmph']  # 风速（公里/小时）
                    
                    return f"{city}当前天气：{desc}，温度{temp}°C，湿度{humidity}%，风速{wind}km/h。"
                return f"天气查询失败，状态码：{response.status}"
        except Exception as e:
            return f"天气服务异常：{str(e)}"


async def get_weather_forecast(city: str, days: int = 3):
    """
    异步查询未来几天的天气预报
    city: 城市拼音
    days: 要查询的未来天数，默认 3 天
    返回值：包含逐日预报的字符串
    """
    url = f"https://wttr.in/{city}?format=j1"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    # data['weather'] 是一个列表，包含今天及未来多天的数据
                    # [1:days+1] 从索引 1 开始取，跳过今天（索引 0）
                    forecasts = data['weather'][1:days+1]
                    if not forecasts:
                        return f"无法获取{city}的预报数据"
                    
                    result = f"📍 {city}未来{days}天天气：\n"
                    for day in forecasts:
                        date = day['date']            # 日期（如 2025-07-27）
                        max_t = day['maxtempC']       # 最高温度
                        min_t = day['mintempC']       # 最低温度
                        # day['hourly'][0] 取当天第一小时的天气描述（一般作为当天代表）
                        desc = day['hourly'][0]['weatherDesc'][0]['value']
                        result += f"  📅 {date}：{desc}，{min_t}°C ~ {max_t}°C\n"
                    return result.strip()  # .strip() 去掉末尾多余的换行
                return f"预报查询失败，状态码：{response.status}"
        except Exception as e:
            return f"预报服务异常：{str(e)}"


# ============================================
# 2. 大模型调用函数（同步）
# ============================================

def call_llm(messages, tools=None):
    """
    调用 DeepSeek 大模型 API（同步请求）
    messages: 对话历史列表，如 [{"role": "user", "content": "广州天气"}]
    tools: 工具定义列表，告诉大模型有哪些工具可用
    返回值：大模型返回的 JSON 响应（包含 choices[0].message 等）
    """
    # 从环境变量中读取 DeepSeek API Key（在 .env 文件中配置）
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    
    # DeepSeek 的 API 地址（兼容 OpenAI 格式）
    URL = "https://api.deepseek.com/v1/chat/completions"
    
    # 请求头：包含认证信息和数据类型
    headers = {
        "Authorization": f"Bearer {API_KEY}",   # Bearer Token 认证
        "Content-Type": "application/json"      # 告诉服务器发送的是 JSON 格式
    }
    
    # 请求体（Payload）：包含模型名称、对话内容、工具列表等
    payload = {
        "model": "deepseek-v4-pro",      # 模型名称（注意版本号）
        "messages": messages,            # 对话历史
        "tools": tools,                  # 工具说明书
        "tool_choice": "auto"            # 让模型自动决定是否调用工具
    }
    
    # 发起 POST 请求，timeout=30 表示最多等待 30 秒
    resp = requests.post(URL, headers=headers, json=payload, timeout=30)
    return resp.json()  # 将返回的 JSON 字符串解析为 Python 字典
def call_llm_stream(messages, tools=None):
    """
    流式调用 DeepSeek API，返回一个生成器（逐块输出）
    """
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
        "tool_choice": "auto",
        "stream": True  # 关键：开启流式
    }
    # 使用 requests 的 stream 模式
    response = requests.post(URL, headers=headers, json=payload, stream=True, timeout=60)
    return response  # 返回原始响应对象，用于迭代

# ============================================
# 3. 工具说明书（Tools 定义）
# ============================================

# tools 是一个列表，每个元素是一个工具的定义
# 大模型会根据这些定义来判断何时调用哪个工具
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_date",
            "description": "获取当前日期和星期几，当用户问‘今天几号’、‘现在是什么时候’、或者需要规划行程时使用",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",   # 固定写法：表示这是一个函数工具
        "function": {
            "name": "get_weather",   # 工具名称，必须和实际函数名一致
            "description": "查询指定城市当前的实时天气，当用户问'现在'天气时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市拼音，如 guangzhou"}
                },
                "required": ["city"]   # 必须提供的参数
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
    },
    {
        "type": "function",
        "function": {
            "name": "get_hot_news",
            "description": "查询当前最新的热门新闻，当用户问'今天有什么新闻'、'热点'时使用",
            "parameters": {
                "type": "object",
                "properties": {},    # 没有参数
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
    }
]


# ============================================
# 4. Agent 核心执行函数（支持并发工具调用）
# ============================================

async def run_agent(user_query, history=None):
    # ========== 新增：任务规划逻辑 ==========
    from planner import plan_steps
    
    # 先判断是否需要规划（简单问题直接走原流程）
    simple_keywords = ["天气", "新闻", "股价", "快递", "温度", "预报"]
    is_complex = True
    for kw in simple_keywords:
        if kw in user_query and len(user_query) < 20:
            is_complex = False
            break
    
    if is_complex:
        print(f"🧠 识别为复杂任务，启动规划器...")
        steps = plan_steps(user_query)
        print(f"📋 规划步骤：{steps}")
        
        # 执行每个步骤（这里简化：把步骤拼成提示词，让大模型直接回答）
        # 更高级的方式是逐步执行并收集结果，我们一步步来
        step_results = []
        for step in steps:
            # 先用一个简单的方式：把步骤交给大模型执行
            # 未来可以改为实际调用工具
            step_prompt = f"你正在执行一个子任务。原始需求是：{user_query}。当前步骤是：{step}。请完成这个步骤，并返回结果。"
            step_response = call_llm([
                {"role": "system", "content": "你是一个执行专家，严格按照要求完成子任务。"},
                {"role": "user", "content": step_prompt}
            ])
            result = step_response['choices'][0]['message']['content']
            step_results.append(f"【{step}】\n{result}")
        
        # 汇总所有步骤结果
        summary_prompt = f"""用户原始需求：{user_query}
        
下面是各步骤的执行结果：
{'='*40}
{chr(10).join(step_results)}
{'='*40}

请综合以上信息，给用户一个完整、清晰的最终回答。
"""
        final_response = call_llm([
            {"role": "system", "content": "你是一个总结专家，善于把零散信息整合成完整回答。"},
            {"role": "user", "content": summary_prompt}
        ])
        return final_response['choices'][0]['message']['content']
    
    # ========== 原有逻辑（简单问题走原流程） ==========
    # ... 你原来的 run_agent 代码保持不变 ...
    # （复制你原来的代码到这里）
    """
    Agent 主入口
    user_query: 用户输入的文本
    history: 之前的对话历史列表（每条消息是 {"role": "user" 或 "assistant", "content": "..."}）
    """
    # 如果 history 为空，初始化为空列表
    if history is None:
        history = []
    
    # 构建消息列表：system + 历史消息（只取最近 3 轮）+ 当前用户消息
    messages = [
        {"role": "system", "content": "你是一个智能助手，根据用户问题自动调用合适的工具获取信息。你可以使用的工具包括：get_weather（天气查询）、get_weather_forecast（天气预报）、get_hot_news（热门新闻）、get_stock_price（股票价格）。请注意，你没有 web_search 工具。"}
    ]
    
    # 添加历史消息（最近 3 轮 = 最近 6 条消息）
    # 每轮对话包含 1 条 user + 1 条 assistant
    if history:
        # 取最近 6 条消息（3 轮）
        recent_history = history[-6:] if len(history) > 6 else history
        messages.extend(recent_history)
    
    # 添加当前用户消息
    messages.append({"role": "user", "content": user_query})
    
    # 第一次调用大模型，带上工具定义
    response_data = call_llm(messages, tools=tools)
    
    # 检查返回结果是否包含错误信息
    if "error" in response_data:
        return f"❌ API错误：{response_data['error'].get('message', '未知错误')}"
    
    # 提取大模型的回复消息
    choice = response_data['choices'][0]    # choices 是列表，取第一个结果
    message = choice['message']
    
    # 判断大模型是否决定调用工具
    # tool_calls 字段存在且非空，表示大模型想调用工具
    if message.get('tool_calls'):
        tool_calls = message['tool_calls']  # 获取所有工具调用列表
        
        # 内部函数：执行单个工具
        # 放在这里是为了捕获 tool_call 的上下文
        async def execute_tool(tool_call):
            # 提取工具名称和参数
            tool_name = tool_call['function']['name']
            # arguments 是 JSON 字符串，需要解析成 Python 字典
            args = json.loads(tool_call['function']['arguments'])
            
            # 根据工具名称，调用对应的异步函数
            if tool_name == "get_weather":
                return await get_weather(args['city'])
            elif tool_name == "get_weather_forecast":
                days = args.get('days', 3)   # 如果未提供 days，默认 3
                return await get_weather_forecast(args['city'], days)
            elif tool_name == "get_hot_news":
                return await get_hot_news()
            elif tool_name == "get_stock_price":
                return await get_stock_price(args['symbol'])
            elif tool_name == "get_express":
                return await get_express(args['company'], args['number'])
            elif tool_name == "get_current_date":
                return await get_current_date()
            else:
                return "未知工具"
        
        # asyncio.gather：并发执行所有工具调用
        # *[execute_tool(tc) for tc in tool_calls] 把列表解包成多个参数
        # 所有工具并发执行，总耗时约等于最慢的那个工具
        results = await asyncio.gather(*[execute_tool(tc) for tc in tool_calls])
        
        # 把大模型的第一次回复（包含 tool_calls）加入对话历史
        messages.append(message)
        
        # 把每个工具的执行结果也加入对话历史
        # role="tool" 表示这是工具返回的结果
        # tool_call_id 必须和对应的 tool_call 的 id 匹配
        for i, tool_call in enumerate(tool_calls):
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call['id'],
                "content": results[i]
            })
        
        # 第二次调用大模型，让它根据工具结果生成最终回答
        final_resp = call_llm(messages)
        return final_resp['choices'][0]['message']['content']
    
    else:
        # 如果大模型没有调用工具，直接返回它的文本回复
        return message['content']


# ============================================
# 5. 交互式命令行主入口
# ============================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🤖 智能天气助手已启动（支持多城市并发查询 + 3轮对话记忆）")
    print("💡 输入 'q' 或 '退出' 结束对话")
    print("="*50 + "\n")
    
    # 💡 在外部维护对话历史
    conversation_history = []
    
    while True:
        user_input = input("👤 你：")
        
        if user_input.lower() in ['q', 'quit', '退出']:
            print("👋 再见！")
            break
        
        if not user_input.strip():
            continue
        
        print("🤖 助手：", end="", flush=True)
        
        # 💡 把对话历史传给 run_agent
        response = asyncio.run(run_agent(user_input, conversation_history))
        print(response + "\n")
        
        # 💡 将本轮对话添加到历史中
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": response})
        
        # 💡 只保留最近 3 轮（6 条消息），防止历史无限增长
        if len(conversation_history) > 6:
            # 保留最近 6 条消息
            conversation_history = conversation_history[-6:]
        
        # 如果用户只按回车（空输入），跳过本次循环
        if not user_input.strip():
            continue
        
        # 输出 "助手："，不换行（end=""），并立即刷新缓冲区（flush=True）
        print("🤖 助手：", end="", flush=True)
        
        # asyncio.run() 执行异步的 run_agent 函数
        # 因为 run_agent 是 async 函数，需要用 asyncio.run 来启动
        response = asyncio.run(run_agent(user_input))
        
        # 打印最终回答并换行
        print(response + "\n")