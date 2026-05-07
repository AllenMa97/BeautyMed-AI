# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import os
import httpx
import asyncio
import threading
import json
import time
import concurrent.futures
import requests
from datetime import datetime
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

from typing import Dict, Optional, Any, AsyncGenerator, ClassVar, List

from algorithm_services.utils.logger import get_logger
from algorithm_services.utils.pattern import clean_think_tags
from algorithm_services.core.managers.metrics_models import LLMCostRecord, get_metrics_manager

logger = get_logger(__name__)

# 加载自定义路径的.env文件
# 拼接路径：项目根目录/config/LLM_API.env
env_path = Path(__file__).resolve().parent.parent / "config" / "LLM_API.env"
# 验证.env文件是否存在
if not env_path.exists():
    raise FileNotFoundError(f"未找到LLM配置文件：{env_path}")
# 加载.env文件
load_dotenv(dotenv_path=env_path, encoding="utf-8")



def load_all_llm_configs() -> Dict[str, Dict[str, Any]]:
    """加载所有服务商的配置（支持多服务商同时启用，支持多API Key，支持模型回退）"""
    common_config = {
        "timeout": int(os.getenv("LLM_TIMEOUT", 30)),
        "max_retries": int(os.getenv("LLM_MAX_RETRIES", 3))
    }
    all_configs = {}
    providers = ["aliyun", "glm", "lansee",]

    for provider in providers:
        prefix = provider.upper()
        config = common_config.copy()
        config.update({
            "api_base": os.getenv(f"{prefix}_API_BASE"),
            "api_key": os.getenv(f"{prefix}_API_KEY"),
            "model": os.getenv(f"{prefix}_DEFAULT_MODEL"),
            "models": json.loads(os.getenv(f"{prefix}_MODELS", "{}")),
            "fallback_models": json.loads(os.getenv(f"{prefix}_FALLBACK_MODELS", "[]")),
            "fallback_provider": os.getenv(f"{prefix}_FALLBACK_PROVIDER", None)
        })

        api_keys = [config["api_key"]]
        for i in range(2, 10):
            backup_key = os.getenv(f"{prefix}_API_KEY_{i}")
            if backup_key:
                api_keys.append(backup_key)
        config["api_keys"] = api_keys
        config["current_key_index"] = 0

        if config["api_base"] and config["api_key"] and config["model"]:
            all_configs[provider] = config
            logger.info(f"加载服务商[{provider}]配置：默认模型={config['model']}，模型映射={config['models']}，API Keys={len(config['api_keys'])}个")

            # 并行检测所有API Key及其可用模型
            logger.info(f"[Key检测] 开始并行检测服务商[{provider}]的API Keys...")
            valid_keys_with_models = _check_all_keys_parallel(
                config["api_base"],
                config["api_keys"],
                config.get("models", {}),
                config["model"]
            )

            if valid_keys_with_models:
                config["key_configs"] = valid_keys_with_models
                logger.info(f"[Key检测] 服务商[{provider}] 有效Key数量: {len(valid_keys_with_models)}/{len(config['api_keys'])}")
            else:
                logger.error(f"[Key检测] 服务商[{provider}] 所有Key都无效！")
        else:
            logger.info(f"服务商[{provider}]配置不完整，跳过加载")

    if not all_configs:
        raise EnvironmentError("无任何有效LLM服务商配置")
    return all_configs


async def _check_api_key_health(api_base: str, api_key: str, model: str) -> bool:
    """检测单个API Key是否有效（异步，用于启动后定期检测）"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                api_base.rstrip("/"),
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 10
                }
            )
            if response.status_code in (200, 400):
                return True
            return False
    except Exception as e:
        logger.warning(f"[Key检测] Key检测失败: {e}")
        return False


def _check_api_key_health_sync(api_base: str, api_key: str, model: str) -> bool:
    """检测单个API Key是否有效（同步，用于启动时检测）"""
    try:
        response = requests.post(
            api_base.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10
            },
            timeout=10
        )
        if response.status_code in (200, 400):
            return True
        return False
    except Exception as e:
        logger.warning(f"[Key检测] Key检测失败: {e}")
        return False


def _check_key_models_sync(api_base: str, api_key: str, model_mapping: dict) -> list:
    """检测单个API Key支持的模型列表（同步，用于启动时检测）"""
    test_models = list(model_mapping.keys()) if model_mapping else ["qwen-flash", "qwen-turbo", "qwen-plus"]
    available_models = []

    for model in test_models:
        try:
            response = requests.post(
                api_base.rstrip("/"),
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model_mapping.get(model, model),
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 10
                },
                timeout=5
            )
            if response.status_code in (200, 400):
                available_models.append(model)
        except Exception:
            pass

    return available_models


async def _check_key_models_async(api_base: str, api_key: str, model_mapping: dict) -> list:
    """检测单个API Key支持的模型列表（异步）"""
    test_models = list(model_mapping.keys()) if model_mapping else ["qwen-flash", "qwen-turbo", "qwen-plus"]
    available_models = []

    async def check_single_model(model: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(
                    api_base.rstrip("/"),
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model_mapping.get(model, model),
                        "messages": [{"role": "user", "content": "Hi"}],
                        "max_tokens": 10
                    }
                )
                if response.status_code in (200, 400):
                    return model
        except Exception:
            pass
        return None

    # 并行检测所有模型
    tasks = [check_single_model(m) for m in test_models]
    results = await asyncio.gather(*tasks)
    available_models = [r for r in results if r is not None]

    return available_models


def _check_all_keys_parallel(api_base: str, api_keys: list, model_mapping: dict, default_model: str) -> list:
    """并行检测所有API Key及其支持的模型"""
    def check_single_key_sync(idx: int, key: str) -> tuple:
        """同步检测单个Key的所有模型，返回(idx, result)"""
        available_models = []

        for model in model_mapping.keys():
            try:
                response = requests.post(
                    api_base.rstrip("/"),
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "model": model_mapping.get(model, model),
                        "messages": [{"role": "user", "content": "Hi"}],
                        "max_tokens": 10
                    },
                    timeout=5
                )
                if response.status_code in (200, 400):
                    available_models.append(model)
            except Exception:
                pass

        if available_models:
            result = {
                "key": key,
                "models": available_models,
                "default_model": default_model if default_model in available_models else available_models[0]
            }
            return (idx, result)
        return (idx, None)

    # 使用线程池并行检测所有Key
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(api_keys)) as executor:
        futures = [executor.submit(check_single_key_sync, idx, key) for idx, key in enumerate(api_keys)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # 按原始索引排序，保证Key顺序正确
    results.sort(key=lambda x: x[0])
    results = [r[1] for r in results]

    valid_keys_with_models = [r for r in results if r is not None]

    # 记录结果
    for idx, r in enumerate(results):
        if r:
            logger.info(f"[Key检测] Key {idx+1} ✅ 可用，支持模型: {len(r['models'])}个 - {r['models']}")
        else:
            logger.warning(f"[Key检测] Key {idx+1} ❌ 无效")

    return valid_keys_with_models

# 加载所有服务商配置
ALL_LLM_CONFIGS = load_all_llm_configs()
# 默认服务商
DEFAULT_PROVIDER = os.getenv("LLM_DEFAULT_PROVIDER", "aliyun").lower()
if DEFAULT_PROVIDER not in ALL_LLM_CONFIGS:
    DEFAULT_PROVIDER = list(ALL_LLM_CONFIGS.keys())[0]  # 兜底取第一个有效服务商

# ========== 请求模型 ==========
class LLMRequest(BaseModel):
    """LLM调用请求模型"""
    system_prompt: str
    user_prompt: str
    temperature: float = 0.3  # LLM 超参
    max_tokens: int = 32768 # 32768是Qwen flash模型的输入+输出的总token上限
    response_format: Optional[Dict[str, Any]] = None  # JSON格式约束
    stream: bool = False  # 是否启用流式响应
    response_language: str = "zh_CN"  # 限制返回的语种，默认中文
    model: Optional[str] = "qwen-flash"  # 模型名（可传别名）
    provider: Optional[str] = "aliyun"  # 指定服务商（aliyun/glm/lansee/haici）
    enable_search: bool = False  # 是否启用联网搜索
    source: Optional[str] = None  # 调用来源标识，用于日志追踪
    session_id: Optional[str] = None  # 会话ID，用于统计
    enable_context_cache: bool = False  # 是否启用阿里云Context Cache（Microcompact）


# ========== LLM Client（单服务商Client） ==========
class SingleProviderLLMClient:
    """单一服务商的LLM Client（内部使用，支持多API Key回退）"""

    def __init__(self, provider: str, config: Dict[str, Any]):
        self.provider = provider
        self.config = config
        self._client = None  # 延迟初始化客户端
        self.model_mapping = config.get("models", {})
        self.default_model = config["model"]
    
    @property
    def client(self):
        """懒加载HTTP客户端，避免在不同事件循环中复用"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config["timeout"])
        return self._client

    def _get_api_key(self) -> str:
        """获取当前API Key，支持回退"""
        # 优先使用新的key_configs结构
        key_configs = self.config.get("key_configs", [])
        if key_configs:
            current_idx = self.config.get("current_key_index", 0)
            if current_idx < len(key_configs):
                return key_configs[current_idx]["key"]
            return key_configs[0]["key"]

        # 兼容旧的api_keys结构
        api_keys = self.config.get("api_keys", [self.config.get("api_key", "")])
        current_idx = self.config.get("current_key_index", 0)
        if current_idx < len(api_keys):
            return api_keys[current_idx]
        return api_keys[0] if api_keys else ""

    def _get_current_key_models(self) -> list:
        """获取当前API Key支持的模型列表"""
        key_configs = self.config.get("key_configs", [])
        if key_configs:
            current_idx = self.config.get("current_key_index", 0)
            if current_idx < len(key_configs):
                return key_configs[current_idx].get("models", [])
        # 兼容旧的fallback_models结构
        return self.config.get("fallback_models", [])

    def _switch_to_backup_key(self) -> bool:
        """切换到备用API Key，返回是否成功"""
        # 优先使用新的key_configs结构
        key_configs = self.config.get("key_configs", [])
        if key_configs:
            current_idx = self.config.get("current_key_index", 0)
            if current_idx < len(key_configs) - 1:
                self.config["current_key_index"] = current_idx + 1
                new_key = key_configs[current_idx + 1]["key"]
                logger.info(f"[LLM] 服务商[{self.provider}] 切换到备用API Key {self.config['current_key_index'] + 1}/{len(key_configs)}，可用模型: {len(key_configs[current_idx + 1].get('models', []))}个")
                return True
            logger.warning(f"[LLM] 服务商[{self.provider}] 无更多备用API Key")
            return False

        # 兼容旧的api_keys结构
        api_keys = self.config.get("api_keys", [])
        current_idx = self.config.get("current_key_index", 0)
        if current_idx < len(api_keys) - 1:
            self.config["current_key_index"] = current_idx + 1
            logger.info(f"[LLM] 服务商[{self.provider}] 切换到备用API Key {self.config['current_key_index'] + 1}/{len(api_keys)}")
            return True
        logger.warning(f"[LLM] 服务商[{self.provider}] 无更多备用API Key")
        return False

    def list_supported_models(self) -> List[str]:
        """获取当前服务商支持的所有模型（含别名）"""
        # 别名 + 真实模型名
        alias_models = list(self.model_mapping.keys())
        real_models = list(self.model_mapping.values())
        all_models = list(set(alias_models + real_models + [self.default_model]))
        return sorted(all_models)

    def _get_effective_model(self, request_model: Optional[str] = None) -> str:
        """获取当前服务商下的有效模型名（考虑当前Key的可用模型）"""
        # 获取当前Key支持的模型列表
        current_key_models = self._get_current_key_models()

        if not request_model:
            # 未指定模型时，使用当前Key的默认模型
            key_configs = self.config.get("key_configs", [])
            if key_configs:
                current_idx = self.config.get("current_key_index", 0)
                if current_idx < len(key_configs):
                    default = key_configs[current_idx].get("default_model", self.default_model)
                    logger.info(f"服务商[{self.provider}]未指定模型，使用Key {current_idx+1}的默认模型：{default}")
                    return default
            logger.info(f"服务商[{self.provider}]未指定模型，使用默认模型：{self.default_model}")
            return self.default_model

        mapped_model = self.model_mapping.get(request_model, request_model)

        # 检查当前Key是否支持该模型
        if current_key_models and request_model not in current_key_models:
            # 模型不在当前Key的可用列表中，使用Key的默认模型
            key_configs = self.config.get("key_configs", [])
            if key_configs:
                current_idx = self.config.get("current_key_index", 0)
                if current_idx < len(key_configs):
                    fallback = key_configs[current_idx].get("default_model", self.default_model)
                    logger.warning(f"服务商[{self.provider}] Key {current_idx+1}不支持模型 {request_model}，使用默认模型：{fallback}")
                    return self.model_mapping.get(fallback, fallback)

        # 验证模型是否在有效模型列表中
        valid_models = set(self.model_mapping.values()) | {self.default_model}
        if mapped_model not in valid_models:
            # 尝试使用当前Key的默认模型
            key_configs = self.config.get("key_configs", [])
            if key_configs:
                current_idx = self.config.get("current_key_index", 0)
                if current_idx < len(key_configs):
                    fallback = key_configs[current_idx].get("default_model", self.default_model)
                    logger.warning(f"服务商[{self.provider}]模型 {request_model}不合法，使用Key {current_idx+1}默认模型：{fallback}")
                    return self.model_mapping.get(fallback, fallback)
            raise ValueError(
                f"服务商[{self.provider}]下指定的模型 {request_model}（映射后：{mapped_model}）不合法！\n"
                f"支持的有效模型：{list(valid_models)}"
            )
        return mapped_model

    def _get_stream_flag(self, request: LLMRequest) -> bool:
        """获取stream标识"""
        return bool(getattr(request, "stream", False))

    async def call_llm(self, request: LLMRequest) -> Dict[str, Any]:
        """非流式调用（支持多API Key回退 + 模型回退 + 供应商回退）"""
        if self._get_stream_flag(request):
            raise ValueError("非流式调用方法不支持stream=True，请使用call_llm_stream方法")

        retry_count = 0
        max_retries = self.config["max_retries"]
        key_switched = False
        model_switched = False
        fallback_models = self.config.get("fallback_models", [])
        current_fallback_index = 0
        
        while retry_count < max_retries:
            request_start_time = time.time()
            try:
                effective_model = self._get_effective_model(request.model)
                api_key = self._get_api_key()
                
                # 构建messages，支持Context Cache
                if request.enable_context_cache and self.provider == "aliyun":
                    # 阿里云Context Cache：为system_prompt添加cache_control标记
                    messages = [
                        {
                            "role": "system",
                            "content": [
                                {
                                    "type": "text",
                                    "text": request.system_prompt,
                                    "cache_control": {"type": "ephemeral"}
                                }
                            ]
                        },
                        {"role": "user", "content": request.user_prompt}
                    ]
                else:
                    messages = [
                        {"role": "system", "content": request.system_prompt},
                        {"role": "user", "content": request.user_prompt}
                    ]
                
                payload = {
                    "model": effective_model,
                    "messages": messages,
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "response_language": request.response_language,
                    "stream": False
                }
                if request.response_format:
                    payload["response_format"] = request.response_format
                if request.enable_search:
                    payload["enable_search"] = True

                response = await self.client.post(
                    self.config["api_base"].rstrip("/"),
                    timeout=self.config["timeout"],
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload
                )
                if response.status_code != 200:
                    logger.error(f"[LLM] 请求失败状态码: {response.status_code}, 响应: {response.text[:500]}")
                response.raise_for_status()
                llm_resp = response.json()
                
                # 提取token使用量（兼容多种字段名）
                usage_data = llm_resp.get("usage", {})
                # 阿里云可能返回 input_tokens, prompt_tokens, completion_tokens 等
                input_tokens = usage_data.get("input_tokens") or usage_data.get("prompt_tokens") or usage_data.get("total_tokens", 0)
                output_tokens = usage_data.get("output_tokens") or usage_data.get("completion_tokens") or 0
                total_tokens = usage_data.get("total_tokens") or (input_tokens + output_tokens) if input_tokens else 0
                
                latency_ms = int((time.time() - request_start_time) * 1000)
                
                # 获取当前模型名称
                current_model = self._get_effective_model(request.model)
                
                # 获取当前使用的 API Key 用于日志
                current_api_key = self._get_api_key()
                key_preview = current_api_key[:8] + "..." + current_api_key[-4:] if current_api_key and len(current_api_key) > 12 else "N/A"
                
                # 记录到metrics
                mgr = get_metrics_manager()
                if mgr:
                    mgr.record_llm_call(LLMCostRecord(
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    provider=self.provider,
                    model=current_model,
                    key_id=key_preview,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    success=True,
                    session_id=getattr(request, 'session_id', None),
                    request_source=getattr(request, 'source', None)
                ))
                
                # 额外记录详细日志，显示API Key、模型和token使用情况
                logger.info(f"[LLM调用成功] provider={self.provider} key={key_preview} model={current_model} input_tokens={input_tokens} output_tokens={output_tokens} total_tokens={total_tokens} latency={latency_ms}ms")
                
                # 检查choices数组是否存在且不为空，防止索引越界
                if "choices" in llm_resp and llm_resp["choices"]:
                    tmp_content = llm_resp["choices"][0]["message"]["content"].strip()
                    content = clean_think_tags(tmp_content)
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        # 尝试去掉空白后重试
                        content_stripped = content.strip()
                        try:
                            return json.loads(content_stripped)
                        except json.JSONDecodeError:
                            logger.warning(f"服务商[{self.provider}]返回非JSON格式：{content}")
                            return {"raw_content": content}
                else:
                    # 如果没有choices或者为空，返回错误信息
                    raise Exception(f"LLM响应中缺少choices字段或为空：{llm_resp}")

            except Exception as e:
                retry_count += 1
                source_info = f"[{request.source}] " if request.source else ""
                
                error_str = str(e)
                
                # 获取当前使用的 API Key 和模型信息用于日志
                current_api_key = self._get_api_key()
                key_preview = current_api_key[:8] + "..." + current_api_key[-4:] if current_api_key and len(current_api_key) > 12 else "N/A"
                current_model = self._get_effective_model(request.model)
                
                # 记录失败的LLM调用
                mgr = get_metrics_manager()
                if mgr:
                    mgr.record_llm_call(LLMCostRecord(
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    provider=self.provider,
                    model=current_model,
                    key_id=key_preview,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    latency_ms=int((time.time() - request_start_time) * 1000),
                    success=False,
                    error_type=error_str[:100],
                    session_id=getattr(request, 'session_id', None),
                    request_source=getattr(request, 'source', None)
                ))
                
                # 额外记录详细错误日志，显示API Key、模型和错误信息
                logger.error(f"[LLM调用失败] provider={self.provider} key={key_preview} model={current_model} error={error_str[:100]} latency={int((time.time() - request_start_time) * 1000)}ms")
                
                # 内容审核失败等不可重试错误，直接抛出
                if "data_inspection_failed" in error_str or "inappropriate content" in error_str.lower():
                    raise Exception(f"{source_info}内容审核未通过，输入内容可能包含不适宜信息，请修改后重试")
                
                # 400/403错误时尝试切换API Key
                if ("400" in error_str or "403" in error_str) and not key_switched:
                    if self._switch_to_backup_key():
                        key_switched = True
                        retry_count = 0
                        logger.info(f"[LLM] 提供商[{self.provider}] Key[{key_preview}] 模型[{current_model}] 切换API Key后重试")
                        continue
                
                # 403配额错误时尝试模型回退
                if "403" in error_str or "free" in error_str.lower() or "quota" in error_str.lower() or "配额" in error_str:
                    if not model_switched and fallback_models and current_fallback_index < len(fallback_models):
                        fallback_model = fallback_models[current_fallback_index]
                        current_fallback_index += 1
                        model_switched = True
                        retry_count = 0
                        logger.warning(f"[LLM] 提供商[{self.provider}] Key[{key_preview}] 模型[{current_model}] 配额不足，切换到备用模型: {fallback_model}")
                        # 临时覆盖请求的模型
                        original_model = request.model
                        request.model = fallback_model
                        try:
                            continue
                        finally:
                            request.model = original_model
                
                logger.error(f"[LLM] 提供商[{self.provider}] Key[{key_preview}] 模型[{current_model}] 调用失败（重试{retry_count}/{max_retries}）：{str(e)}")
                if retry_count >= max_retries:
                    raise Exception(f"{source_info}提供商[{self.provider}] Key[{key_preview}] 模型[{current_model}] 调用多次失败：{str(e)}")

    async def call_llm_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """流式调用（支持多API Key回退 + 模型回退）"""
        if not self._get_stream_flag(request):
            raise ValueError("流式调用方法要求stream=True")

        retry_count = 0
        max_retries = self.config["max_retries"]
        key_switched = False
        model_switched = False
        fallback_models = self.config.get("fallback_models", [])
        current_fallback_index = 0
        
        while retry_count < max_retries:
            stream_start_time = time.time()  # 初始化时间戳，防止异常时未定义
            try:
                effective_model = self._get_effective_model(request.model)
                current_model = effective_model  # 定义current_model变量
                api_key = self._get_api_key()
                
                # 构建messages，支持Context Cache
                if request.enable_context_cache and self.provider == "aliyun":
                    # 阿里云Context Cache：为system_prompt添加cache_control标记
                    messages = [
                        {
                            "role": "system",
                            "content": [
                                {
                                    "type": "text",
                                    "text": request.system_prompt,
                                    "cache_control": {"type": "ephemeral"}
                                }
                            ]
                        },
                        {"role": "user", "content": request.user_prompt}
                    ]
                else:
                    messages = [
                        {"role": "system", "content": request.system_prompt},
                        {"role": "user", "content": request.user_prompt}
                    ]
                
                payload = {
                    "model": effective_model,
                    "messages": messages,
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "stream": True,
                    "response_language": request.response_language,
                    "stream_options": {"include_usage": True}
                }
                if request.enable_search:
                    payload["enable_search"] = True

                async with self.client.stream(
                        "POST",
                        self.config["api_base"].rstrip("/"),
                        json=payload,
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=self.config["timeout"]
                ) as response:
                    response.raise_for_status()
                    stream_start_time = time.time()  # 重新设置开始时间
                    input_tokens = 0
                    output_tokens = 0
                    
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith("data: "):
                            line = line[6:]
                            if line == "[DONE]":
                                # 流式结束时记录token统计
                                total_tokens = input_tokens + output_tokens
                                latency_ms = int((time.time() - stream_start_time) * 1000)
                                
                                # 获取当前使用的 API Key 用于日志
                                current_api_key = self._get_api_key()
                                key_preview = current_api_key[:8] + "..." + current_api_key[-4:] if current_api_key and len(current_api_key) > 12 else "N/A"
                                
                                mgr = get_metrics_manager()
                                if mgr:
                                    mgr.record_llm_call(LLMCostRecord(
                                        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        provider=self.provider,
                                        model=current_model,
                                        key_id=key_preview,
                                        input_tokens=input_tokens,
                                        output_tokens=output_tokens,
                                        total_tokens=total_tokens,
                                        latency_ms=latency_ms,
                                        success=True,
                                        session_id=getattr(request, 'session_id', None),
                                        request_source=getattr(request, 'source', None)
                                    ))
                                
                                # 额外记录详细日志，显示API Key、模型和token使用情况
                                logger.info(f"[LLM流式调用成功] provider={self.provider} key={key_preview} model={current_model} input_tokens={input_tokens} output_tokens={output_tokens} total_tokens={total_tokens} latency={latency_ms}ms")
                                break
                            try:
                                chunk = json.loads(line)
                                # 检查是否有usage字段（最后一块）
                                # 阿里云可能有多种格式：usage, prompt_tokens+completion_tokens, 或 total_tokens
                                usage_data = chunk.get("usage", {})
                                if usage_data:
                                    input_tokens = usage_data.get("input_tokens") or usage_data.get("prompt_tokens") or usage_data.get("total_tokens", 0)
                                    output_tokens = usage_data.get("output_tokens") or usage_data.get("completion_tokens") or 0
                                    total_tokens = usage_data.get("total_tokens") or (input_tokens + output_tokens) if input_tokens else 0
                                else:
                                    # 某些API可能在顶层返回token数量
                                    input_tokens = chunk.get("prompt_tokens") or chunk.get("total_tokens", 0) or 0
                                    output_tokens = chunk.get("completion_tokens") or 0
                                    total_tokens = chunk.get("total_tokens") or (input_tokens + output_tokens) if input_tokens else 0
                                
                                # 检查choices列表是否存在且不为空，防止索引越界
                                if "choices" in chunk and chunk["choices"]:
                                    tmp_content = chunk["choices"][0]["delta"].get("content", "")
                                    content = clean_think_tags(tmp_content)
                                    if content:
                                        yield content
                                else:
                                    # 如果没有choices或者为空，可能是其他类型的响应，跳过
                                    continue
                            except (json.JSONDecodeError, KeyError, IndexError) as e:
                                logger.warning(f"服务商[{self.provider}]流式响应解析失败：{line}，错误：{e}")
                return

            except Exception as e:
                retry_count += 1
                source_info = f"[{request.source}] " if getattr(request, 'source', None) else ""
                
                error_str = str(e)
                
                # 获取当前使用的 API Key 和模型信息用于日志
                current_api_key = self._get_api_key()
                key_preview = current_api_key[:8] + "..." + current_api_key[-4:] if current_api_key and len(current_api_key) > 12 else "N/A"
                current_model = self._get_effective_model(request.model)
                
                # 记录失败的LLM调用（流式）
                mgr = get_metrics_manager()
                if mgr:
                    mgr.record_llm_call(LLMCostRecord(
                        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        provider=self.provider,
                        model=current_model,
                        key_id=key_preview,
                        input_tokens=0,
                        output_tokens=0,
                        total_tokens=0,
                        latency_ms=int((time.time() - stream_start_time) * 1000),
                        success=False,
                        error_type=error_str[:100],
                        session_id=getattr(request, 'session_id', None),
                        request_source=getattr(request, 'source', None)
                    ))
                
                # 额外记录详细错误日志，显示API Key、模型和错误信息
                logger.error(f"[LLM流式调用失败] provider={self.provider} key={key_preview} model={current_model} error={error_str[:100]} latency={int((time.time() - stream_start_time) * 1000)}ms")
                
                # 内容审核失败等不可重试错误，直接抛出
                if "data_inspection_failed" in error_str or "inappropriate content" in error_str.lower():
                    raise Exception(f"{source_info}内容审核未通过，输入内容可能包含不适宜信息，请修改后重试")
                
                # 400/403错误时尝试切换API Key
                if ("400" in error_str or "403" in error_str) and not key_switched:
                    if self._switch_to_backup_key():
                        key_switched = True
                        retry_count = 0
                        logger.info(f"[LLM] 提供商[{self.provider}] Key[{key_preview}] 模型[{current_model}] 流式切换API Key后重试")
                        continue
                
                # 403配额错误时尝试模型回退
                if "403" in error_str or "free" in error_str.lower() or "quota" in error_str.lower() or "配额" in error_str:
                    if not model_switched and fallback_models and current_fallback_index < len(fallback_models):
                        fallback_model = fallback_models[current_fallback_index]
                        current_fallback_index += 1
                        model_switched = True
                        retry_count = 0
                        logger.warning(f"[LLM] 提供商[{self.provider}] Key[{key_preview}] 模型[{current_model}] 流式配额不足，切换到备用模型: {fallback_model}")
                        original_model = request.model
                        request.model = fallback_model
                        try:
                            continue
                        finally:
                            request.model = original_model
                
                logger.error(f"[LLM] 提供商[{self.provider}] Key[{key_preview}] 模型[{current_model}] 流式调用失败（重试{retry_count}/{max_retries}）：{str(e)}")
                if retry_count >= max_retries:
                    raise Exception(f"[LLM] 提供商[{self.provider}] Key[{key_preview}] 模型[{current_model}] 流式调用多次失败：{str(e)}")

    async def free_call_llm(self, prompt_str, temperature=0, model: Optional[str] = None) -> str:
        """自由调用（非结构化）"""
        retry_count = 0
        max_retries = self.config["max_retries"]
        while retry_count < max_retries:
            try:
                effective_model = self._get_effective_model(model)
                payload = {
                    "model": effective_model,
                    "messages": prompt_str,
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
                source_info = f"[{prompt_str.get('source', 'unknown')}] " if isinstance(prompt_str, dict) else ""
                logger.error(f"{source_info}服务商[{self.provider}]自由调用失败（重试{retry_count}/{max_retries}）：{str(e)}")
                if retry_count >= max_retries:
                    raise Exception(f"{source_info}服务商[{self.provider}]自由调用多次失败：{str(e)}")

    async def close(self):
        """关闭当前服务商的客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None


# ========== 全局LLM Client工厂（单例） ==========
class LLMClientFactory:
    """LLM Client工厂（单例），管理多服务商Client实例"""
    _instance: ClassVar[Optional["LLMClientFactory"]] = None
    _client_map: Dict[str, SingleProviderLLMClient] = {}  # 服务商 -> Client实例
    _lock = threading.Lock()  # 加这行

    def __new__(cls):
        with cls._lock:  # 加这行
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                # 初始化所有服务商的Client实例
                for provider, config in ALL_LLM_CONFIGS.items():
                    cls._instance._client_map[provider] = SingleProviderLLMClient(provider, config)
            return cls._instance

    def get_client(self, provider: Optional[str] = None) -> SingleProviderLLMClient:
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

    async def call_llm_with_model(self, request: LLMRequest) -> Dict[str, Any]:
        """快捷方法：指定服务商+模型调用非流式LLM（支持供应商回退）"""
        fallback_provider = None
        
        # 获取当前供应商的备用供应商配置
        current_config = ALL_LLM_CONFIGS.get(request.provider, {})
        fallback_provider = current_config.get("fallback_provider")
        
        # 尝试当前供应商
        try:
            client = self.get_client(request.provider)
            return await client.call_llm(request)
        except Exception as primary_error:
            # 如果有备用供应商且当前失败，尝试备用供应商
            if fallback_provider and fallback_provider in self._client_map:
                logger.warning(f"[LLM] 主供应商[{request.provider}]失败，尝试备用供应商[{fallback_provider}]")
                try:
                    fallback_config = ALL_LLM_CONFIGS.get(fallback_provider, {})
                    original_provider = request.provider
                    original_model = request.model
                    request.provider = fallback_provider
                    # 使用备用供应商的默认模型
                    request.model = fallback_config.get("model")
                    client = self.get_client(fallback_provider)
                    result = await client.call_llm(request)
                    request.provider = original_provider
                    request.model = original_model
                    return result
                except Exception as fallback_error:
                    request.provider = original_provider
                    request.model = original_model
                    logger.error(f"[LLM] 备用供应商[{fallback_provider}]也失败：{fallback_error}")
                    raise primary_error  # 抛出原始错误
            raise

    async def call_llm_batch(self, requests: List[LLMRequest]) -> List[Dict[str, Any]]:
        """
        批量并发调用 LLM
        适用于多个独立请求并行执行，可显著提升速度
        """
        if not requests:
            return []
        
        tasks = [self.call_llm(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "error": str(result),
                    "request_index": i
                })
            else:
                processed_results.append(result)
        
        return processed_results

    async def call_llm_stream_with_model(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """快捷方法：指定服务商+模型调用流式LLM（支持供应商回退）"""
        fallback_provider = None
        
        # 获取当前供应商的备用供应商配置
        current_config = ALL_LLM_CONFIGS.get(request.provider, {})
        fallback_provider = current_config.get("fallback_provider")
        
        # 尝试当前供应商
        try:
            client = self.get_client(request.provider)
            async for chunk in client.call_llm_stream(request):
                yield chunk
        except Exception as primary_error:
            # 如果有备用供应商且当前失败，尝试备用供应商
            if fallback_provider and fallback_provider in self._client_map:
                logger.warning(f"[LLM] 流式主供应商[{request.provider}]失败，尝试备用供应商[{fallback_provider}]")
                try:
                    fallback_config = ALL_LLM_CONFIGS.get(fallback_provider, {})
                    original_provider = request.provider
                    original_model = request.model
                    request.provider = fallback_provider
                    # 使用备用供应商的默认模型
                    request.model = fallback_config.get("model")
                    client = self.get_client(fallback_provider)
                    async for chunk in client.call_llm_stream(request):
                        yield chunk
                    request.provider = original_provider
                    request.model = original_model
                except Exception as fallback_error:
                    request.provider = original_provider
                    request.model = original_model
                    logger.error(f"[LLM] 流式备用供应商[{fallback_provider}]也失败：{fallback_error}")
                    raise primary_error  # 抛出原始错误
            else:
                raise

    async def close_all(self):
        """关闭所有服务商的Client连接"""
        for client in self._client_map.values():
            await client.close()

# 全局单例工厂
llm_client_factory = LLMClientFactory()

# 兼容原有单例调用（兜底）
class LegacyLLMClientAdapter:
    """适配原有单例调用方式，兼容旧代码，支持供应商回退"""
    async def call_llm(self, request: LLMRequest) -> Dict[str, Any]:
        # 使用工厂的供应商回退机制
        return await llm_client_factory.call_llm_with_model(request)

    async def call_llm_batch(self, requests: List[LLMRequest]) -> List[Dict[str, Any]]:
        """批量并发调用 LLM"""
        return await llm_client_factory.call_llm_batch(requests)

    async def call_llm_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        client = llm_client_factory.get_client(request.provider)
        async for chunk in client.call_llm_stream(request):
            yield chunk

    async def free_call_llm(self, prompt_str, temperature=0, model: Optional[str] = None) -> str:
        client = llm_client_factory.get_client()
        return await client.free_call_llm(prompt_str, temperature, model)

    async def close(self):
        await llm_client_factory.close_all()


class EmbeddingRequest(BaseModel):
    """Embedding调用请求模型"""
    text: str
    model: str = "text-embedding-v3"
    dimensions: int = 1024


class EmbeddingClient:
    """Embedding 客户端"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
    
    async def get_embedding(self, request: EmbeddingRequest) -> List[float]:
        """获取单个文本的 embedding"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": request.model,
            "input": request.text,
            "dimensions": request.dimensions
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result["data"][0]["embedding"]
    
    async def get_embeddings_batch(self, texts: List[str], model: str = "text-embedding-v3", dimensions: int = 1024) -> List[List[float]]:
        """批量获取 embedding"""

        if not texts:
            return []
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "input": texts,
            "dimensions": dimensions
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return [item["embedding"] for item in result["data"]]


# 全局 embedding client
_embedding_client = None

def get_embedding_client() -> EmbeddingClient:
    """获取 embedding 客户端"""
    global _embedding_client
    if _embedding_client is None:
        api_key = os.getenv("ALIYUN_API_KEY", "")
        if not api_key:
            raise ValueError("未设置 ALIYUN_API_KEY 环境变量")
        _embedding_client = EmbeddingClient(api_key)
    return _embedding_client


# 保留原有单例变量，兼容旧Service代码
llm_client_singleton = LegacyLLMClientAdapter()

