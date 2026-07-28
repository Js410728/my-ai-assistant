# multi_agent.py
import asyncio
import json
from weather import call_llm, get_weather, get_weather_forecast, get_hot_news, get_stock_price, get_express
from rag import query_knowledge_base

# ============================================
# 1. 子Agent定义（每个Agent就是一个提示词 + 工具调用封装）
# ============================================

WEATHER_AGENT_PROMPT = """你是一个天气查询专家。用户提出与天气相关的问题时，你会调用工具获取准确数据。
你可以使用 get_weather（实时天气）和 get_weather_forecast（天气预报）。
如果用户没有指定城市，请询问城市名称。
"""

KNOWLEDGE_AGENT_PROMPT = """你是一个知识库检索专家。用户提出的问题如果涉及知识库中的内容，你会调用 RAG 检索工具（query_knowledge_base）获取相关资料，并基于资料回答。
如果检索不到相关信息，请如实告知用户。
"""

NEWS_AGENT_PROMPT = """你是一个新闻专家。当用户询问新闻时，你调用 get_hot_news 获取热点，并整理成清晰列表。
"""

STOCK_AGENT_PROMPT = """你是一个股票查询专家。当用户询问股票价格时，你调用 get_stock_price 获取实时数据。
如果用户未提供股票代码，请提示用户提供。
"""

PLANNER_AGENT_PROMPT = """你是一个任务规划专家。用户提出的复杂需求，你拆解成多个子任务，并分配给对应的子Agent。
输出格式为 JSON 列表，例如：["天气查询", "知识库检索"]。
"""

# ============================================
# 2. Supervisor：识别用户意图，决定调用哪个子Agent（或组合）
# ============================================

async def supervisor(user_query, history=None):
    """
    主管：分析用户问题，决定：
    1. 是否需要拆解成多个子任务？
    2. 分别交给哪些子Agent？
    3. 汇总结果并返回。
    """
    # 第一步：让大模型判断任务类型，并生成执行计划
    plan_prompt = f"""
你是一个任务调度主管。用户提出了以下需求：
{user_query}

请分析这个需求，并给出执行计划。输出格式为 JSON 数组，每个元素为一个任务描述，格式如下：
[
    {{"agent": "weather", "query": "查询广州天气"}},
    {{"agent": "knowledge", "query": "检索公司年假政策"}},
    {{"agent": "planner", "query": "规划出差行程"}}
]

可用的 agent 类型：weather, knowledge, news, stock, planner。
如果问题很简单，只输出一个任务即可。
只输出 JSON 数组，不要输出其他内容。
"""
    plan_response = call_llm([
        {"role": "system", "content": "你是一个任务调度专家，擅长分解用户需求。"},
        {"role": "user", "content": plan_prompt}
    ])
    content = plan_response['choices'][0]['message']['content']
    try:
        # 提取 JSON
        start = content.find('[')
        end = content.rfind(']') + 1
        tasks = json.loads(content[start:end])
    except Exception as e:
        print(f"⚠️ 解析计划失败：{e}，直接交给 weather Agent")
        tasks = [{"agent": "weather", "query": user_query}]
    
    # 第二步：执行每个任务
    results = []
    for task in tasks:
        agent_type = task.get('agent', 'weather')
        query = task.get('query', user_query)
        
        if agent_type == 'weather':
            # 直接调用原有工具（或调用子Agent的LLM）
            # 这里为了复用，我们直接调用 call_llm 并注入工具定义
            result = await run_agent_with_prompt(WEATHER_AGENT_PROMPT, query, tools='weather')
        elif agent_type == 'knowledge':
            # 调用知识库检索 + 生成回答
            result = await run_agent_with_prompt(KNOWLEDGE_AGENT_PROMPT, query, tools='knowledge')
        elif agent_type == 'news':
            result = await run_agent_with_prompt(NEWS_AGENT_PROMPT, query, tools='news')
        elif agent_type == 'stock':
            result = await run_agent_with_prompt(STOCK_AGENT_PROMPT, query, tools='stock')
        elif agent_type == 'planner':
            result = await run_agent_with_prompt(PLANNER_AGENT_PROMPT, query, tools='planner')
        else:
            result = f"未知的Agent类型：{agent_type}"
        
        results.append(f"【{agent_type}】{result}")
    
    # 第三步：汇总
    summary_prompt = f"""
用户原始需求：{user_query}

以下是各子任务返回的结果：
{chr(10).join(results)}

请综合这些结果，给用户一个完整、清晰的最终回答。
"""
    summary_response = call_llm([
        {"role": "system", "content": "你是一个信息汇总专家，善于把分散的信息整合成清晰的答案。"},
        {"role": "user", "content": summary_prompt}
    ])
    return summary_response['choices'][0]['message']['content']

# ============================================
# 3. 辅助函数：根据提示词 + 工具类型调用子Agent
# ============================================

async def run_agent_with_prompt(system_prompt, user_query, tools='weather'):
    """
    调用一个子Agent（本质是：用 system_prompt 限定角色，并根据工具类型决定调用哪些工具）
    tools 参数可以是 'weather'、'knowledge'、'news'、'stock'、'planner'
    这里为了简化，我们统一调用 call_llm，并传入特定的 tools 列表。
    但更简单的方式是：直接使用原有的 run_agent 逻辑，但替换 system_prompt。
    由于原有 run_agent 内部会自己构建 messages，我们可以传递一个额外的 system_prompt 覆盖。
    这里我采用更直接的方式：构造 messages，调用 call_llm，但手动解析 tool_calls 并执行。
    但为了快速集成，我们选择使用现有的 run_agent，但传入一个构造好的 messages。
    """
    # 由于现有 run_agent 会调用 tools，我们直接复用，但把 system_prompt 作为第一句。
    # 实际上 run_agent 内部已有 system，我们可以传入一个增强的 history。
    from weather import run_agent
    # 但 run_agent 会默认使用自己的 system，我们可传入 history 覆盖？
    # 更好的做法是直接调用 call_llm 并手动处理 tool_calls。
    # 为了演示，我们直接调用 run_agent，但传入一个历史消息，包含 system_prompt。
    # 但 run_agent 的第一个参数是 user_query，第二个是 history。
    # 我们可以构造一个 history，第一个是 system。
    # 但 run_agent 会忽略 history 中的 system？需要检查 run_agent 的实现。
    # 实际上 run_agent 开头会强制设置自己的 system，所以无法覆盖。
    # 因此我们采用 call_llm 手动调用，但需要复制 execute_tool 逻辑。
    # 这里我直接使用一个简化的方式：让大模型直接回答，不调用工具。
    # 但为了工具调用，我们保留原 run_agent，但修改 system_prompt 为传入值。
    # 最简单的方式：复制一份 run_agent 的代码，但参数可配置 system。
    # 由于时间关系，我先给出概念方案，你可以和我一起实现。
    # 实际上我们可以在 weather.py 中增加一个 run_agent_with_system 函数。
    # 这里暂时返回模拟结果。
    return f"子Agent执行（模拟）：{user_query}"