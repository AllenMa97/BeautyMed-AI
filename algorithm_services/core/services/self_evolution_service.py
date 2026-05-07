# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import json
import asyncio
import os
from typing import Dict, Any, List
from datetime import datetime
from algorithm_services.utils.logger import get_logger
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.core.prompts.features.self_evolution_prompt import get_self_evolution_prompt, get_learn_from_correction_prompt

logger = get_logger(__name__)


DEFAULT_PROVIDER = "aliyun"
DEFAULT_MODEL = "qwen-plus"  # qwen3-max不可用
LLM_REQUEST_MAX_TOKENS = int(32768)

# DEFAULT_PROVIDER = "lansee"
# DEFAULT_MODEL = "Qwen/Qwen2.5-32B-Instruct-AWQ"
# LLM_REQUEST_MAX_TOKENS = int(512)


LLM_REQUEST_TEMPERATURE = float(0.5)


EVOLUTION_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "evolution")
KNOWLEDGE_FILE = os.path.join(EVOLUTION_DATA_DIR, "knowledge_base.json")
BEHAVIOR_FILE = os.path.join(EVOLUTION_DATA_DIR, "behavior_modifications.json")
INTERACTION_FILE = os.path.join(EVOLUTION_DATA_DIR, "interaction_strategies.json")
FEATURE_CONFIG_FILE = os.path.join(EVOLUTION_DATA_DIR, "feature_enhancements.json")


class EvolutionStorage:
    """
    进化数据存储管理器
    负责持久化存储进化结果
    """
    
    def __init__(self):
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        if not os.path.exists(EVOLUTION_DATA_DIR):
            os.makedirs(EVOLUTION_DATA_DIR, exist_ok=True)
    
    def load_json(self, file_path: str, default: Any = None) -> Any:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载文件失败 {file_path}: {e}")
        return default if default is not None else {}
    
    def save_json(self, file_path: str, data: Any) -> bool:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存文件失败 {file_path}: {e}")
            return False
    
    def append_to_list(self, file_path: str, item: Dict) -> bool:
        data = self.load_json(file_path, [])
        if not isinstance(data, list):
            data = []
        item["_timestamp"] = datetime.now().isoformat()
        data.append(item)
        if len(data) > 1000:
            data = data[-1000:]
        return self.save_json(file_path, data)


evolution_storage = EvolutionStorage()


class SelfEvolutionService:
    """
    自进化服务
    用于分析系统表现并提出改进建议
    """
    
    def __init__(self):
        self.DEFAULT_PROVIDER = DEFAULT_PROVIDER
        self.DEFAULT_MODEL = DEFAULT_MODEL
        self.LLM_REQUEST_MAX_TOKENS = LLM_REQUEST_MAX_TOKENS
        self.LLM_REQUEST_TEMPERATURE = LLM_REQUEST_TEMPERATURE
        self.storage = evolution_storage
        self._runtime_knowledge = {}
        self._runtime_behavior = {}
        self._runtime_interaction = {}
        self._load_runtime_state()

    def _load_runtime_state(self):
        """
        加载运行时状态
        """
        self._runtime_knowledge = self.storage.load_json(KNOWLEDGE_FILE, {})
        self._runtime_behavior = self.storage.load_json(BEHAVIOR_FILE, {})
        self._runtime_interaction = self.storage.load_json(INTERACTION_FILE, {})
        logger.info(f"加载进化状态: 知识{len(self._runtime_knowledge)}条, 行为{len(self._runtime_behavior)}条")

    def get_runtime_knowledge(self, key: str = None) -> Any:
        """
        获取运行时知识（供其他服务调用）
        """
        if key:
            return self._runtime_knowledge.get(key)
        return self._runtime_knowledge

    def get_runtime_behavior(self, key: str = None) -> Any:
        """
        获取运行时行为配置（供其他服务调用）
        """
        if key:
            return self._runtime_behavior.get(key)
        return self._runtime_behavior

    def get_interaction_strategy(self, scenario: str = None) -> Any:
        """
        获取交互策略（供其他服务调用）
        """
        if scenario:
            return self._runtime_interaction.get(scenario)
        return self._runtime_interaction


    async def analyze_system_performance(self, 
                                      user_profile: Dict[str, Any], 
                                      error_records: List[Dict[str, Any]], 
                                      recent_dialogs: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        分析系统性能并提出改进建议
        """
        try:
            # 构建提示词
            tmp = get_self_evolution_prompt(
                user_profile=str(user_profile),
                error_records=str(error_records[-10:]),  # 只取最近10条错误记录
                recent_dialogs=str(recent_dialogs[-5:])   # 只取最近5次对话
            )
            # 构建LLM请求
            llm_request = LLMRequest(
                system_prompt=tmp["system_prompt"],
                user_prompt=tmp["user_prompt"],
                temperature=self.LLM_REQUEST_TEMPERATURE,
                max_tokens=self.LLM_REQUEST_MAX_TOKENS,
                provider=self.DEFAULT_PROVIDER,
                model=self.DEFAULT_MODEL,
            )
            
            # 调用LLM进行分析
            response = await llm_client_singleton.call_llm(llm_request)
            
            # 解析返回结果
            try:
                # 检查response是否已经是字典类型
                if isinstance(response, dict):
                    result = response
                else:
                    # 如果是字符串，则解析为JSON
                    result = json.loads(response)
                result["evolution_timestamp"] = datetime.now().isoformat()
                return result
            except (json.JSONDecodeError, TypeError):
                # 如果不是JSON格式，返回基本结构
                logger.warning("LLM返回的自进化分析不是有效的JSON格式")
                return {
                    "behavior_improvements": [],
                    "knowledge_updates": [],
                    "interaction_adjustments": [],
                    "feature_enhancements": [],
                    "analysis_summary": str(response),
                    "evolution_timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"自进化分析失败: {e}")
            return {
                "behavior_improvements": [],
                "knowledge_updates": [],
                "interaction_adjustments": [],
                "feature_enhancements": [],
                "analysis_summary": f"分析失败: {str(e)}",
                "evolution_timestamp": datetime.now().isoformat()
            }
    
    async def learn_from_correction(self, 
                                  original_info: str, 
                                  correction: str) -> Dict[str, Any]:
        """
        从用户纠正中学习
        """
        try:
            # 构建提示词
            tmp = get_learn_from_correction_prompt(
                original_info=original_info or "无原始信息",
                correction=correction
            )

            # 构建LLM请求
            llm_request = LLMRequest(
                system_prompt=tmp["system_prompt"],
                user_prompt=tmp["user_prompt"],
                temperature=self.LLM_REQUEST_TEMPERATURE,
                max_tokens=self.LLM_REQUEST_MAX_TOKENS,
                provider=self.DEFAULT_PROVIDER,
                model=self.DEFAULT_MODEL,
            )


            # 调用LLM进行学习分析
            response = await llm_client_singleton.call_llm(llm_request)
            
            # 解析返回结果
            try:
                # 检查response是否已经是字典类型
                if isinstance(response, dict):
                    result = response
                else:
                    # 如果是字符串，则解析为JSON
                    result = json.loads(response)
                result["learning_timestamp"] = datetime.now().isoformat()
                return result
            except (json.JSONDecodeError, TypeError):
                # 如果不是JSON格式，返回基本结构
                logger.warning("LLM返回的学习结果不是有效的JSON格式")
                return {
                    "original_mistake": original_info or "无原始信息",
                    "corrected_information": correction,
                    "mistake_category": "未知类别",
                    "learning_points": [str(response)],
                    "prevention_strategy": "加强相关领域知识验证",
                    "learning_timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"从纠正中学习失败: {e}")
            return {
                "original_mistake": original_info or "无原始信息",
                "corrected_information": correction,
                "mistake_category": "未知类别",
                "learning_points": [f"学习失败: {str(e)}"],
                "prevention_strategy": "加强相关领域知识验证",
                "learning_timestamp": datetime.now().isoformat()
            }

    async def apply_evolution_results(self, evolution_results: Dict[str, Any], session_manager):
        """
        应用自进化结果到系统中
        实现具体的进化手段：
        1. 知识更新 -> 持久化到知识库文件 + 运行时缓存
        2. 行为改进 -> 更新行为配置 + 影响规划器决策
        3. 交互调整 -> 更新交互策略模板
        4. 功能增强 -> 更新功能配置参数
        """
        try:
            applied_count = 0
            
            behavior_improvements = evolution_results.get("behavior_improvements", [])
            if behavior_improvements:
                applied_count += await self._apply_behavior_improvements(behavior_improvements)
            
            knowledge_updates = evolution_results.get("knowledge_updates", [])
            if knowledge_updates:
                applied_count += await self._apply_knowledge_updates(knowledge_updates)
            
            interaction_adjustments = evolution_results.get("interaction_adjustments", [])
            if interaction_adjustments:
                applied_count += await self._apply_interaction_adjustments(interaction_adjustments)
            
            feature_enhancements = evolution_results.get("feature_enhancements", [])
            if feature_enhancements:
                applied_count += await self._apply_feature_enhancements(feature_enhancements)
            
            logger.info(f"自进化应用完成，共应用 {applied_count} 项改进")
            return True
            
        except Exception as e:
            logger.error(f"应用自进化结果失败: {e}")
            return False
    
    async def _apply_behavior_improvements(self, improvements: List) -> int:
        """
        应用行为改进
        """
        applied = 0
        for improvement in improvements:
            try:
                if isinstance(improvement, dict):
                    key = improvement.get("category", f"behavior_{datetime.now().timestamp()}")
                    value = improvement
                else:
                    key = f"behavior_{datetime.now().timestamp()}"
                    value = {"description": str(improvement), "active": True}
                
                self._runtime_behavior[key] = value
                self.storage.append_to_list(BEHAVIOR_FILE, {
                    "type": "behavior_improvement",
                    "key": key,
                    "value": value
                })
                applied += 1
                logger.info(f"应用行为改进: {key}")
            except Exception as e:
                logger.warning(f"应用行为改进失败: {e}")
        
        self.storage.save_json(BEHAVIOR_FILE, self._runtime_behavior)
        return applied
    
    async def _apply_knowledge_updates(self, updates: List) -> int:
        """
        应用知识更新
        """
        applied = 0
        for update in updates:
            try:
                if isinstance(update, dict):
                    key = update.get("topic") or update.get("key", f"knowledge_{datetime.now().timestamp()}")
                    value = update.get("content") or update.get("value", str(update))
                else:
                    key = f"knowledge_{datetime.now().timestamp()}"
                    value = str(update)
                
                self._runtime_knowledge[key] = value
                self.storage.append_to_list(KNOWLEDGE_FILE, {
                    "type": "knowledge_update",
                    "key": key,
                    "value": value
                })
                applied += 1
                logger.info(f"应用知识更新: {key}")
            except Exception as e:
                logger.warning(f"应用知识更新失败: {e}")
        
        self.storage.save_json(KNOWLEDGE_FILE, self._runtime_knowledge)
        return applied
    
    async def _apply_interaction_adjustments(self, adjustments: List) -> int:
        """
        应用交互调整
        """
        applied = 0
        for adjustment in adjustments:
            try:
                if isinstance(adjustment, dict):
                    scenario = adjustment.get("scenario", "general")
                    strategy = adjustment.get("strategy", adjustment)
                else:
                    scenario = "general"
                    strategy = str(adjustment)
                
                if scenario not in self._runtime_interaction:
                    self._runtime_interaction[scenario] = []
                self._runtime_interaction[scenario].append(strategy)
                
                self.storage.append_to_list(INTERACTION_FILE, {
                    "type": "interaction_adjustment",
                    "scenario": scenario,
                    "strategy": strategy
                })
                applied += 1
                logger.info(f"应用交互调整: {scenario}")
            except Exception as e:
                logger.warning(f"应用交互调整失败: {e}")
        
        self.storage.save_json(INTERACTION_FILE, self._runtime_interaction)
        return applied
    
    async def _apply_feature_enhancements(self, enhancements: List) -> int:
        """
        应用功能增强
        """
        applied = 0
        for enhancement in enhancements:
            try:
                if isinstance(enhancement, dict):
                    feature_name = enhancement.get("feature", "unknown")
                    config = enhancement.get("config", enhancement)
                else:
                    feature_name = "unknown"
                    config = {"description": str(enhancement)}
                
                self.storage.append_to_list(FEATURE_CONFIG_FILE, {
                    "type": "feature_enhancement",
                    "feature": feature_name,
                    "config": config
                })
                applied += 1
                logger.info(f"应用功能增强: {feature_name}")
            except Exception as e:
                logger.warning(f"应用功能增强失败: {e}")
        
        return applied


# 创建全局实例
self_evolution_service = SelfEvolutionService()