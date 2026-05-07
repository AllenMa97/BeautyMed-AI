# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import os
import httpx
import asyncio
import json
from typing import Dict, Optional, Any, AsyncGenerator, ClassVar, List, Union
from dotenv import load_dotenv
from pathlib import Path
from pydantic import BaseModel, Field, validator

from algorithm_services.utils.logger import get_logger
from algorithm_services.utils.pattern import clean_think_tags

logger = get_logger(__name__)

# 加载自定义路径的.env文件
# 拼接路径：项目根目录/config/LVLM_API.env
env_path = Path(__file__).resolve().parent.parent / "config" / "LVLM_API.env"
# 验证.env文件是否存在
if not env_path.exists():
    raise FileNotFoundError(f"未找到LVLM配置文件：{env_path}")
# 加载.env文件
load_dotenv(dotenv_path=env_path, encoding="utf-8")


def load_all_lvlm_configs() -> Dict[str, Dict[str, Any]]:
    """加载所有服务商的配置（支持多服务商同时启用）"""
    common_config = {
        "timeout": int(os.getenv("LVLM_TIMEOUT", 30)),
        "max_retries": int(os.getenv("LVLM_MAX_RETRIES", 20))
    }
    all_configs = {}
    providers = ["aliyun", "glm", ]

    for provider in providers:
        prefix = provider.upper()
        config = common_config.copy()
        config.update({
            "api_base": os.getenv(f"{prefix}_API_BASE"),
            "api_key": os.getenv(f"{prefix}_API_KEY"),
            "model": os.getenv(f"{prefix}_DEFAULT_MODEL"),
            "models": json.loads(os.getenv(f"{prefix}_MODELS", "{}"))
        })
        if config["api_base"] and config["api_key"] and config["model"]:
            all_configs[provider] = config
            logger.info(f"加载服务商[{provider}]配置：默认模型={config['model']}，模型映射={config['models']}")
        else:
            logger.info(f"服务商[{provider}]配置不完整，跳过加载")

    if not all_configs:
        raise EnvironmentError("无任何有效LVLM服务商配置")
    return all_configs


# 加载所有服务商配置
ALL_LVLM_CONFIGS = load_all_lvlm_configs()
# 默认服务商
DEFAULT_PROVIDER = os.getenv("LVLM_DEFAULT_PROVIDER", "aliyun").lower()
if DEFAULT_PROVIDER not in ALL_LVLM_CONFIGS:
    DEFAULT_PROVIDER = list(ALL_LVLM_CONFIGS.keys())[0]  # 兜底取第一个有效服务商

# ========== 请求模型 ==========
class LVLMRequest(BaseModel):
    """LVLM 调用请求参数模型（标准化请求参数）"""
    system_prompt: str = Field(default="", description="系统提示词")
    user_prompt: str = Field(default="", description="用户提示词")
    temperature: float = Field(default=0.3, ge=0, le=1, description="生成温度，0-1之间")
    max_tokens: int = Field(default=32768, ge=1, le=65536, description="最大生成token数")
    response_format: Optional[Dict[str, Any]] = Field(default=None, description="响应格式要求")
    model: Optional[str] = Field(default=None, description="指定模型名（支持别名）")
    response_language: str = Field(default="zh_CN", description="响应语言")
    stream: bool = Field(default=False, description="是否流式调用")
    provider: Optional[str] = Field(default=None, description="指定调用的服务商")

    @validator("temperature")
    def validate_temperature(cls, v):
        """校验温度值范围"""
        if not (0 <= v <= 1):
            raise ValueError("temperature 必须在 0-1 之间")
        return v

    @validator("max_tokens")
    def validate_max_tokens(cls, v):
        """校验最大token数范围"""
        if v < 1 or v > 65536:
            raise ValueError("max_tokens 必须在 1-65536 之间")
        return v

    def to_call_kwargs(self) -> Dict[str, Any]:
        """转换为调用函数的关键字参数"""
        kwargs = {
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": self.response_format,
            "model": self.model,
            "response_language": self.response_language
        }
        return kwargs

# ========== LVLM Client（单服务商Client） ==========
class SingleProviderLVLMClient:
    """单一服务商的LVLM Client（内部使用）"""

    def __init__(self, provider: str, config: Dict[str, Any]):
        self.provider = provider
        self.config = config
        # 初始化HTTP客户端
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {config['api_key']}"},
            timeout=config["timeout"]
        )
        self.model_mapping = config.get("models", {})
        self.default_model = config["model"]

    def list_supported_models(self) -> List[str]:
        """获取当前服务商支持的所有模型（含别名）"""
        # 别名 + 真实模型名
        alias_models = list(self.model_mapping.keys())
        real_models = list(self.model_mapping.values())
        all_models = list(set(alias_models + real_models + [self.default_model]))
        return sorted(all_models)

    def _get_effective_model(self, model: Optional[str] = None) -> str:
        """获取当前服务商下的有效模型名"""
        if not model:
            logger.info(f"服务商[{self.provider}]未指定模型，使用默认模型：{self.default_model}")
            return self.default_model

        mapped_model = self.model_mapping.get(model, model)
        valid_models = set(self.model_mapping.values()) | {self.default_model}
        if mapped_model not in valid_models:
            raise ValueError(
                f"服务商[{self.provider}]下指定的模型 {model}（映射后：{mapped_model}）不合法！\n"
                f"支持的有效模型：{list(valid_models)}"
            )
        return mapped_model

    async def call_lvlm(
            self,
            system_prompt: str,
            user_prompt: str,
            temperature: float = 0.3,
            max_tokens: int = 32768,
            response_format: Optional[Dict[str, Any]] = None,
            model: Optional[str] = None,
            response_language: str = "zh_CN"
    ) -> Dict[str, Any]:
        """非流式调用LVLM"""
        retry_count = 0
        max_retries = self.config["max_retries"]
        while retry_count < max_retries:
            try:
                effective_model = self._get_effective_model(model)
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                payload = {
                    "model": effective_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "response_language": response_language,
                    "stream": False
                }
                if response_format:
                    payload["response_format"] = response_format

                response = await self.client.post(
                    self.config["api_base"].rstrip("/"),
                    timeout=self.config["timeout"],
                    json=payload
                )
                response.raise_for_status()
                llm_resp = response.json()

                tmp_content = llm_resp["choices"][0]["message"]["content"].strip()
                content = clean_think_tags(tmp_content)
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    logger.warning(f"服务商[{self.provider}]返回非JSON格式：{content}")
                    return {"raw_content": content}

            except Exception as e:
                retry_count += 1
                logger.error(f"服务商[{self.provider}]调用失败（重试{retry_count}/{max_retries}）：{str(e)}")
                if retry_count >= max_retries:
                    raise Exception(f"服务商[{self.provider}]调用多次失败：{str(e)}")

    async def call_lvlm_stream(
            self,
            system_prompt: str,
            user_prompt: str,
            temperature: float = 0.3,
            max_tokens: int = 32768,
            model: Optional[str] = None,
            response_language: str = "zh_CN"
    ) -> AsyncGenerator[str, None]:
        """流式调用LLM"""
        retry_count = 0
        max_retries = self.config["max_retries"]
        while retry_count < max_retries:
            try:
                effective_model = self._get_effective_model(model)
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                payload = {
                    "model": effective_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                    "response_language": response_language,
                    "stream_options": {"include_usage": False}
                }

                async with self.client.stream(
                        "POST",
                        self.config["api_base"].rstrip("/"),
                        json=payload,
                        timeout=self.config["timeout"]
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith("data: "):
                            line = line[6:]
                            if line == "[DONE]":
                                break
                            try:
                                chunk = json.loads(line)
                                tmp_content = chunk["choices"][0]["delta"].get("content", "")
                                content = clean_think_tags(tmp_content)
                                if content:
                                    yield content
                            except (json.JSONDecodeError, KeyError) as e:
                                logger.warning(f"服务商[{self.provider}]流式响应解析失败：{line}，错误：{e}")
                return

            except Exception as e:
                retry_count += 1
                logger.error(f"服务商[{self.provider}]流式调用失败（重试{retry_count}/{max_retries}）：{str(e)}")
                if retry_count >= max_retries:
                    raise Exception(f"服务商[{self.provider}]流式调用多次失败：{str(e)}")

    async def free_call_lvlm(
            self,
            prompt_messages: List[Dict[str, str]],
            temperature: float = 0,
            model: Optional[str] = None
    ) -> str:
        """自由调用（非结构化，直接传messages列表）"""
        retry_count = 0
        max_retries = self.config["max_retries"]
        while retry_count < max_retries:
            try:
                effective_model = self._get_effective_model(model)
                payload = {
                    "model": effective_model,
                    "messages": prompt_messages,
                    "temperature": temperature,
                    "stream": False
                }
                response = await self.client.post(
                    self.config["api_base"].rstrip("/"),
                    timeout=self.config["timeout"],
                    json=payload
                )
                response.raise_for_status()
                llm_resp = response.json()
                content = llm_resp["choices"][0]["message"]["content"].strip()
                return clean_think_tags(content)
            except Exception as e:
                retry_count += 1
                logger.error(f"服务商[{self.provider}]自由调用失败（重试{retry_count}/{max_retries}）：{str(e)}")
                if retry_count >= max_retries:
                    raise Exception(f"服务商[{self.provider}]自由调用多次失败：{str(e)}")

    async def close(self):
        """关闭当前服务商的客户端"""
        await self.client.aclose()


# ========== 全局LVLM Client工厂（单例） ==========
class LVLMClientFactory:
    """LLM Client工厂（单例），管理多服务商Client实例"""
    _instance: ClassVar[Optional["LVLMClientFactory"]] = None
    _client_map: Dict[str, SingleProviderLVLMClient] = {}  # 服务商 -> Client实例

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 初始化所有服务商的Client实例
            for provider, config in ALL_LVLM_CONFIGS.items():
                cls._instance._client_map[provider] = SingleProviderLVLMClient(provider, config)
        return cls._instance

    def get_client(self, provider: Optional[str] = None) -> SingleProviderLVLMClient:
        """获取指定服务商的Client（默认用DEFAULT_PROVIDER）"""
        target_provider = provider or DEFAULT_PROVIDER
        if target_provider not in self._client_map:
            raise ValueError(
                f"服务商[{target_provider}]未配置，当前支持的服务商：{list(self._client_map.keys())}"
            )
        return self._client_map[target_provider]

    def list_all_supported_models(self) -> Dict[str, List[str]]:
        """获取所有服务商支持的模型列表"""
        result = {}
        for provider, client in self._client_map.items():
            result[provider] = client.list_supported_models()
        return result

    async def close_all(self):
        """关闭所有服务商的Client连接"""
        for client in self._client_map.values():
            await client.close()

    async def execute_request(self, request: LVLMRequest) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """执行标准化的LVLM请求（兼容流式/非流式）"""
        # 获取指定服务商的客户端
        client = self.get_client(request.provider)

        # 转换请求参数为调用参数
        call_kwargs = request.to_call_kwargs()

        # 根据是否流式选择调用方式
        if request.stream:
            return await client.call_lvlm_stream(**call_kwargs)
        else:
            return await client.call_lvlm(**call_kwargs)

# 全局单例工厂
llm_client_factory = LVLMClientFactory()

# 兼容原有调用的极简适配器（可选保留）
class LegacyLVLMClientAdapter:
    """极简适配器，仅保留核心调用能力"""
    async def call_lvml(self, **kwargs) -> Dict[str, Any]:
        client = llm_client_factory.get_client(kwargs.pop("provider", None))
        return await client.call_lvml(**kwargs)

    async def call_lvml_stream(self, **kwargs) -> AsyncGenerator[str, None]:
        client = llm_client_factory.get_client(kwargs.pop("provider", None))
        return await client.call_lvml_stream(**kwargs)

    async def free_call_lvml(self, prompt_messages, temperature=0, model=None, provider=None) -> str:
        client = llm_client_factory.get_client(provider)
        return await client.free_call_lvml(prompt_messages, temperature, model)

    async def close(self):
        await llm_client_factory.close_all()

# 保留极简单例适配（如需完全移除可删除）
lvlm_client_singleton = LegacyLVLMClientAdapter()


# ========== 便捷调用函数 ==========
async def create_and_execute_lvlm_request(**kwargs) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
    """创建并执行LVLM请求（快捷函数）"""
    # 校验并创建请求模型
    request = LVLMRequest(** kwargs)
    # 执行请求
    return await llm_client_factory.execute_request(request)