"""
MCP 风格的工具注册中心
支持 Pydantic Schema 自动转换为 MCP 格式
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from typing import Dict, Any, Type, Optional
from pydantic import BaseModel


class ToolRegistry:
    """工具注册中心"""
    _tools: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(cls, name: str, description: str, schema_class: Type[BaseModel]):
        """
        注册工具
        :param name: 工具名称
        :param description: 工具描述
        :param schema_class: Pydantic 请求模型类
        """
        cls._tools[name] = {
            "name": name,
            "description": description,
            "schema_class": schema_class,
            "mcp_schema": cls._convert_to_mcp_schema(schema_class)
        }
    
    @classmethod
    def _convert_to_mcp_schema(cls, schema_class: Type[BaseModel]) -> Dict[str, Any]:
        """
        将 Pydantic Schema 转换为 MCP 格式
        """
        pydantic_schema = schema_class.model_json_schema()
        
        properties = {}
        required = pydantic_schema.get("required", [])
        
        for field_name, field_info in pydantic_schema.get("properties", {}).items():
            properties[field_name] = {
                "type": field_info.get("type", "string"),
                "description": field_info.get("description", "")
            }
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    @classmethod
    def get_tool(cls, name: str) -> Optional[Dict[str, Any]]:
        """获取工具"""
        return cls._tools.get(name)
    
    @classmethod
    def get_all_tools(cls) -> Dict[str, Dict[str, Any]]:
        """获取所有工具"""
        return cls._tools
    
    @classmethod
    def get_mcp_tools(cls) -> list:
        """获取所有 MCP 格式的工具列表"""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["mcp_schema"]
            }
            for tool in cls._tools.values()
        ]


def register_tool(name: str, description: str):
    """
    装饰器：注册工具
    用法：
        @register_tool("free_chat", "自由对话")
        class FreeChatService:
            ...
    """
    def decorator(cls):
        ToolRegistry.register(name, description, cls)
        return cls
    return decorator
