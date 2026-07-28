# supervisor.py
import asyncio
from workers import weather_worker, traffic_worker, report_worker, context

async def supervisor(user_query: str):
    """主管：拆解任务，分配Worker，收集结果"""
    print("🧠 Supervisor 开始处理任务...")
    
    # 1. 拆解任务（这里简单硬编码，后续可结合planner）
    # 实际场景中，可以用大模型动态拆解，这里为了演示先写死
    print("📋 Supervisor 拆解任务：")
    print("  - 任务1：查询天气（WeatherWorker）")
    print("  - 任务2：查询交通（TrafficWorker）")
    print("  - 任务3：生成报告（ReportWorker）")
    
    # 2. 并行执行所有Worker（除了ReportWorker，它依赖前两个的结果）
    # 先并发执行前两个Worker
    tasks = [
        weather_worker("北京", 3),  # 示例城市，实际可从user_query提取
        traffic_worker("北京")
    ]
    # 等待前两个Worker完成
    await asyncio.gather(*tasks)
    
    # 3. 执行ReportWorker（依赖于前两个的结果）
    report = await report_worker(user_query)
    
    # 4. 返回最终结果
    print("✅ Supervisor 任务完成")
    return report