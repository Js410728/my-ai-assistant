# workers.py
import asyncio
from weather import get_weather, get_weather_forecast

# 定义共享状态（一个字典，所有Worker共享）
context = {}

# 1. WeatherWorker：查天气
async def weather_worker(city: str, days: int = 3):
    """Worker：查询指定城市的天气"""
    print(f"🌤️ WeatherWorker 开始查询 {city} 的天气...")
    # 调用已有的工具函数
    current = await get_weather(city)
    forecast = await get_weather_forecast(city, days)
    result = f"{current}\n{forecast}"
    # 写入共享状态
    context['weather'] = result
    print(f"✅ WeatherWorker 完成")
    return result

# 2. TrafficWorker：模拟查交通
async def traffic_worker(city: str):
    """Worker：模拟查询交通信息"""
    print(f"🚗 TrafficWorker 开始查询 {city} 的交通...")
    # 模拟数据（实际可接入真实API）
    result = f"从北京到{city}，推荐高铁，约2.5小时，票价约500元。当地出租车起步价14元。"
    context['traffic'] = result
    print(f"✅ TrafficWorker 完成")
    return result

# 3. ReportWorker：写报告
async def report_worker(user_query: str):
    """Worker：基于共享状态中的信息，生成最终报告"""
    print("📝 ReportWorker 开始生成报告...")
    # 从共享状态中读取其他Worker的结果
    weather_info = context.get('weather', '未获取天气信息')
    traffic_info = context.get('traffic', '未获取交通信息')
    
    report = f"""
    📋 出差报告
    ====================================
    用户需求：{user_query}
    
    天气情况：
    {weather_info}
    
    交通建议：
    {traffic_info}
    
    ====================================
    报告生成完毕，祝您出差顺利！
    """
    context['report'] = report
    print(f"✅ ReportWorker 完成")
    return report