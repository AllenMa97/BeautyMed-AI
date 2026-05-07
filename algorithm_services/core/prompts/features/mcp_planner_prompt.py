"""
MCP 风格的 Planner Prompt 生成器
动态从 ToolRegistry 获取工具列表
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import json
from typing import Optional, List, Dict, Any
from algorithm_services.core.tools.tool_registry import ToolRegistry


def get_mcp_planner_prompt(
    user_input: str,
    context: str = "",
    time_location_info: Optional[Dict[str, Any]] = None,
    trending_topics_info: Optional[Dict[str, Any]] = None,
    intermediate_results: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    获取 MCP 风格的 Planner Prompt
    工具列表从 ToolRegistry 动态获取
    """
    mcp_tools = ToolRegistry.get_mcp_tools()
    
    tools_description = ""
    for tool in mcp_tools:
        tools_description += f'''
### {tool["name"]}
描述: {tool["description"]}
参数:
{json.dumps(tool["inputSchema"], ensure_ascii=False, indent=2)}
'''
    
    time_str = ""
    if time_location_info:
        time_str = f"当前时间: {time_location_info.get('combined_context', '未知')}"
    
    trending_str = ""
    if trending_topics_info:
        trending_str = f"热搜: {trending_topics_info.get('combined_context', '暂无')}"
    
    results_str = ""
    if intermediate_results:
        results_str = f"已有结果: {json.dumps(intermediate_results, ensure_ascii=False)}"
    
    system_prompt = f"""你是一个智能助手，可以调用以下工具来帮助用户。

{tools_description}

请根据用户输入，选择合适的工具进行调用。

返回格式（JSON）：
{{
  "function": "工具名",
  "params": {{参数}}
}}

如果不需要调用工具，直接返回：
{{
  "function": "直接回复",
  "params": {{"content": "你的回复"}}
}}
"""

    user_prompt = f"""
{time_str}
{trending_str}
{results_str}

用户输入: {user_input}
上下文: {context}
"""
    
    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "tools": mcp_tools  # 返回工具列表供参考
    }
