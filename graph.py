# ============================================
# LangGraph 流程编排模块
# 负责：定义状态、节点、图结构、条件路由
# ============================================

import json
from typing import TypedDict, Literal, List, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from config import CHECKPOINT_DB_PATH
from llm_client import call_llm
from tools import TOOLS, execute_tool
from memory import get_user_preference, set_user_preference
from city_utils import extract_city_from_text


# ============================================
# 1. 定义状态（所有节点共享的“黑板”）
# ============================================

class AgentState(TypedDict):
    messages: List[Dict[str, Any]]   # 对话历史
    tool_calls: List[Dict]           # 待执行的工具调用
    tool_results: List[str]          # 工具执行结果
    final_answer: str                # 最终回答
    user_id: str                     # 用户标识（用于永久记忆）


# ============================================
# 2. 节点函数
# ============================================

def node_prepare(state: AgentState):
    """
    节点0：准备消息
    从永久记忆读取默认城市，注入 System Prompt
    """
    print("🔧 节点0：准备消息...")
    user_id = state.get('user_id', 'default_user')

    # 从永久记忆读取默认城市
    city_pref = get_user_preference(user_id, "default_city")
    default_city = city_pref['value'] if city_pref else None

    # 如果没有，尝试从历史消息中提取
    if not default_city:
        for msg in reversed(state.get('messages', [])):
            if msg.get('role') == 'user':
                city = extract_city_from_text(msg.get('content', ''))
                if city:
                    default_city = city
                    break

    # 构建 System Prompt
    if default_city:
        system_prompt = f"你是智能助手。如果用户问天气时没有指定城市，默认使用：{default_city}。"
        print(f"📌 当前默认城市：{default_city}")
    else:
        system_prompt = "你是智能助手。当用户问天气时，如果没有提到城市，请主动询问用户想要查询哪个城市。"
        print("📌 没有默认城市，将询问用户")

    # 注入 System Prompt
    has_system = any(msg.get('role') == 'system' for msg in state.get('messages', []))
    if not has_system:
        state['messages'].insert(0, {"role": "system", "content": system_prompt})
    else:
        for msg in state['messages']:
            if msg.get('role') == 'system':
                msg['content'] = system_prompt
                break

    return {}


async def node_call_llm(state: AgentState):
    """
    节点1：调用大模型
    判断是否需要使用工具
    """
    print("🧠 节点1：调用大模型...")
    messages = state['messages']
    response = call_llm(messages, tools=TOOLS)

    message = response['choices'][0]['message']

    if 'tool_calls' in message:
        state['tool_calls'] = message['tool_calls']
        state['messages'].append(message)
        return {"messages": state['messages'], "tool_calls": state['tool_calls']}
    else:
        content = message.get('content', '')
        return {"messages": state['messages'], "final_answer": content}


async def node_execute_tools(state: AgentState):
    """
    节点2：执行所有工具（并发）
    """
    print("🔧 节点2：执行工具...")
    tool_calls = state['tool_calls']
    results = []

    for tc in tool_calls:
        tool_name = tc['function']['name']
        args = json.loads(tc['function']['arguments'])
        result = await execute_tool(tool_name, args)

        state['messages'].append({
            "role": "tool",
            "tool_call_id": tc['id'],
            "content": result
        })
        results.append(result)

    state['tool_calls'] = []
    return {"messages": state['messages'], "tool_results": results, "tool_calls": []}


async def node_generate_final(state: AgentState):
    """
    节点3：生成最终回答
    """
    print("📝 节点3：生成最终回答...")
    messages = state['messages']
    final_resp = call_llm(messages)
    content = final_resp['choices'][0]['message']['content']
    return {"final_answer": content, "messages": messages}


# ============================================
# 3. 条件路由
# ============================================

def route_after_llm(state: AgentState) -> Literal["execute_tools", "generate_final"]:
    """
    判断是否需要执行工具
    - 如果有 tool_calls → 执行工具
    - 如果没有 → 直接生成最终回答
    """
    if state.get('tool_calls'):
        return "execute_tools"
    return "generate_final"


# ============================================
# 4. 搭建图
# ============================================

def build_agent_graph():
    """
    构建完整的 LangGraph
    """
    builder = StateGraph(AgentState)

    # 添加节点
    builder.add_node("prepare", node_prepare)
    builder.add_node("call_llm", node_call_llm)
    builder.add_node("execute_tools", node_execute_tools)
    builder.add_node("generate_final", node_generate_final)

    # 设置入口
    builder.set_entry_point("prepare")

    # 添加边
    builder.add_edge("prepare", "call_llm")
    builder.add_conditional_edges("call_llm", route_after_llm)
    builder.add_edge("execute_tools", "call_llm")  # 执行完工具回到 call_llm
    builder.add_edge("generate_final", END)

    # 挂载永久记忆（SqliteSaver）
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)

    return graph


# ============================================
# 5. 对外接口：直接暴露编译好的图
# ============================================

AGENT_GRAPH = build_agent_graph()


# ============================================
# 快速测试（直接运行此文件时生效）
# ============================================

if __name__ == "__main__":
    print("✅ graph.py 加载成功")
    print(f"📌 检查点数据库路径：{CHECKPOINT_DB_PATH}")