# ============================================
# 工具集模块
# 负责：所有工具函数 + 工具说明书 + 执行路由
# ============================================

import asyncio
import json
import aiohttp
from datetime import datetime
from llm_client import call_llm
import tushare as ts
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================
# 通用工具：获取当前日期
# ============================================

async def get_current_date():
    """获取当前日期和星期几"""
    now = datetime.now()
    weekdays = ['一', '二', '三', '四', '五', '六', '日']
    return f"今天是 {now.strftime('%Y年%m月%d日')}，星期{weekdays[now.weekday()]}"


# ============================================
# 天气工具
# ============================================

async def get_weather(city: str):
    """查询当前天气"""
    url = f"https://wttr.in/{city}?format=j1"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    current = data['current_condition'][0]
                    desc = current['weatherDesc'][0]['value']
                    temp = current['temp_C']
                    humidity = current['humidity']
                    wind = current['windspeedKmph']
                    return f"{city}当前天气：{desc}，温度{temp}°C，湿度{humidity}%，风速{wind}km/h。"
                return f"天气查询失败，状态码：{response.status}"
        except Exception as e:
            return f"天气服务异常：{str(e)}"


async def get_weather_forecast(city: str, days: int = 3):
    """查询未来几天的天气预报"""
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
# 股票工具
# ============================================

async def get_stock_price(symbol: str):
    """查询股票实时价格（美股）"""
    import yfinance as yf
    try:
        stock = await asyncio.to_thread(yf.Ticker, symbol)
        info = await asyncio.to_thread(stock.info)
        price = info.get('regularMarketPrice')
        if price:
            return f"📈 {symbol.upper()} 当前股价：{price} USD"
        return f"未找到股票 {symbol}，请检查代码（如 AAPL, TSLA）"
    except Exception as e:
        return f"股票查询异常：{str(e)}"



# ============================================
# 基金工具（Tushare）
# ============================================


TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")
if TUSHARE_TOKEN:
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    print("✅ Tushare 初始化成功")
else:
    pro = None
    print("⚠️ Tushare Token 未配置，基金功能不可用")


async def search_fund(keyword: str):
    """根据关键词搜索基金"""
    if pro is None:
        return "基金功能未配置，请检查 Tushare Token"
    try:
        df = pro.fund_basic()
        result = df[df['name'].str.contains(keyword) | df['ts_code'].str.contains(keyword)]
        if result.empty:
            return f"未找到包含 '{keyword}' 的基金"
        return result[['ts_code', 'name', 'fund_type']].head(10).to_dict('records')
    except Exception as e:
        return f"搜索基金失败：{str(e)}"


async def get_fund_info(fund_code: str):
    """获取单只基金详细信息"""
    if pro is None:
        return "基金功能未配置，请检查 Tushare Token"
    try:
        basic = pro.fund_basic(ts_code=fund_code)
        if basic.empty:
            return f"未找到基金 {fund_code}"
        nav = pro.fund_nav(ts_code=fund_code, limit=30)
        info = {
            "代码": fund_code,
            "名称": basic.iloc[0]['name'],
            "类型": basic.iloc[0]['fund_type'],
            "管理人": basic.iloc[0]['management'],
            "成立日期": basic.iloc[0]['setup_date'],
            "最新净值": nav.iloc[0]['nav'] if not nav.empty else "暂无",
            "净值日期": nav.iloc[0]['nav_date'] if not nav.empty else "暂无",
        }
        return info
    except Exception as e:
        return f"查询基金失败：{str(e)}"


# ============================================
# 工具说明书（tools 列表）
# ============================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_date",
            "description": "获取当前日期和星期几，当用户问'今天几号'、'现在是什么时候'时使用",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
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
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "查询指定股票的实时价格，当用户问'股价'、'股票'时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "股票代码，如 AAPL, TSLA"}
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
                    "company": {"type": "string", "description": "快递公司名称，如：顺丰、中通"},
                    "number": {"type": "string", "description": "快递单号，如：SF1234567890"}
                },
                "required": ["company", "number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_fund",
            "description": "根据关键词搜索基金，返回匹配的基金列表（含代码和名称）",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词，如：'白酒'、'沪深300'、'161725'"}
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_fund_info",
            "description": "获取单只基金的详细信息（类型、管理人、最新净值、成立日期等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "fund_code": {"type": "string", "description": "基金代码，如 161725"}
                },
                "required": ["fund_code"]
            }
        }
    }
]


# ============================================
# 工具执行路由
# ============================================

async def execute_tool(tool_name: str, args: dict):
    """
    根据工具名称执行对应的工具函数
    """
    if tool_name == "get_current_date":
        return await get_current_date()
    elif tool_name == "get_weather":
        return await get_weather(args.get('city'))
    elif tool_name == "get_weather_forecast":
        days = args.get('days', 3)
        return await get_weather_forecast(args.get('city'), days)
    elif tool_name == "get_stock_price":
        return await get_stock_price(args.get('symbol'))
    elif tool_name == "get_express":
        return await get_express(args.get('company'), args.get('number'))
    elif tool_name == "search_fund":
        return await search_fund(args.get('keyword'))
    elif tool_name == "get_fund_info":
        return await get_fund_info(args.get('fund_code'))
    else:
        return f"未知工具：{tool_name}"