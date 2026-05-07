"""用户知识图谱服务 - 用于User Knowledge Graph冷启动和增量更新"""
import asyncio
import json
import os
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from algorithm_services.utils.logger import get_logger
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.api.schemas.feature_schemas.user_knowledge_graph_schema import (
    KGEntity,
    KGRelationship,
    UserKnowledgeGraph,
    KGFusionRequest,
    KGFusionResponse,
    KGQueryRequest,
    KGQueryResult,
    SimulatedKGData,
)


logger = get_logger(__name__)

USER_KG_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "knowledge")
USER_KG_FILE = os.path.join(USER_KG_DATA_DIR, "user_knowledge_graphs.json")


class UserKnowledgeGraphService:
    """
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

    用户知识图谱服务
    
    功能：
    - 管理用户的知识图谱（实体和关系）
    - 从对话中提取实体和关系
    - 融合外部知识（从模拟服务或外部API）
    - 查询知识图谱获取上下文
    
    与其他服务的关系：
    - 与用户画像服务互补：画像关注兴趣，图谱关注实体关系
    - 与用户风格服务互补：风格关注语言，图谱关注知识
    - 与LLM搜索服务协同：搜索结果可融合到图谱
    
    冷启动：
    - 使用模拟服务生成初始图谱数据
    - 逐步从真实对话中补充
    """
    
    def __init__(self):
        self.default_provider = "aliyun"
        self.default_model = "qwen-plus-0112"
        self._kg_cache: Dict[str, UserKnowledgeGraph] = {}
        self._ensure_data_dir()
        self._load_persisted_kgs()
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(USER_KG_DATA_DIR, exist_ok=True)
    
    def _load_persisted_kgs(self):
        """从文件加载持久化的用户知识图谱"""
        if os.path.exists(USER_KG_FILE):
            try:
                with open(USER_KG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    kgs_data = data.get("user_knowledge_graphs", {})
                    for user_id, kg_dict in kgs_data.items():
                        entities = [KGEntity(**e) for e in kg_dict.get("entities", [])]
                        relationships = [KGRelationship(**r) for r in kg_dict.get("relationships", [])]
                        self._kg_cache[user_id] = UserKnowledgeGraph(
                            user_id=user_id,
                            entities=entities,
                            relationships=relationships,
                            last_updated=kg_dict.get("last_updated", "")
                        )
                    logger.info(f"从持久化文件加载用户知识图谱: {len(self._kg_cache)} 个用户")
            except Exception as e:
                logger.warning(f"加载用户知识图谱持久化数据失败: {e}")
    
    def _save_persisted_kgs(self):
        """保存用户知识图谱到文件"""
        try:
            kgs_data = {}
            for user_id, kg in self._kg_cache.items():
                kgs_data[user_id] = {
                    "user_id": kg.user_id,
                    "entities": [
                        {
                            "id": e.id,
                            "name": e.name,
                            "entity_type": e.entity_type,
                            "description": e.description,
                            "source": e.source,
                            "properties": e.properties
                        }
                        for e in kg.entities
                    ],
                    "relationships": [
                        {
                            "id": r.id,
                            "source_entity": r.source_entity,
                            "target_entity": r.target_entity,
                            "relationship_type": r.relationship_type,
                            "description": r.description,
                            "source": r.source
                        }
                        for r in kg.relationships
                    ],
                    "last_updated": kg.last_updated
                }
            data = {
                "knowledge_type": "user_knowledge_graphs",
                "updated_at": datetime.now().isoformat(),
                "user_knowledge_graphs": kgs_data
            }
            with open(USER_KG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"用户知识图谱已持久化: {len(self._kg_cache)} 个用户")
        except Exception as e:
            logger.warning(f"保存用户知识图谱持久化数据失败: {e}")
    
    def _get_cache_key(self, user_id: str) -> str:
        return f"user_kg_{user_id}"
    
    async def get_user_kg(self, user_id: str) -> Optional[UserKnowledgeGraph]:
        """获取用户知识图谱"""
        cache_key = self._get_cache_key(user_id)
        if cache_key in self._kg_cache:
            logger.debug(f"[知识图谱] 从缓存获取: {user_id}")
            return self._kg_cache[cache_key]
        
        logger.debug(f"[知识图谱] 缓存中无数据: {user_id}")
        return None
    
    async def set_user_kg(self, user_id: str, kg: UserKnowledgeGraph):
        """保存用户知识图谱"""
        cache_key = self._get_cache_key(user_id)
        self._kg_cache[cache_key] = kg
        self._save_persisted_kgs()
        logger.info(f"[知识图谱] 保存用户图谱: {user_id}, 实体数: {len(kg.entities)}, 关系数: {len(kg.relationships)}")
    
    async def extract_from_conversation(self, user_id: str, user_input: str, 
                                        ai_response: str) -> UserKnowledgeGraph:
        """从对话中提取实体和关系"""
        try:
            system_prompt = """你是一个知识图谱提取专家。从对话中提取实体和关系。
要求：
1. 提取有意义的实体（人物、地点、事件、概念、话题、物品等）
2. 建立实体间的关系
3. 以JSON格式返回"""

            user_prompt = f"""从以下对话中提取知识图谱：

用户: {user_input}
AI: {ai_response}

请生成JSON格式数据，包含:
- entities: 实体列表，每个实体包含 name, type, description
- relationships: 关系列表，每个关系包含 source(源实体名), target(目标实体名), type

注意：
- type可选值: person, location, event, concept, topic, object
- relationship_type可选值: interested_in, related_to, mentions, owns, uses, follows

请生成JSON格式数据。"""

            llm_request = LLMRequest(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=1024,
                provider=self.default_provider,
                model=self.default_model
            )
            
            response = await llm_client_singleton.call_llm(llm_request)
            
            if isinstance(response, dict):
                text = response.get("text", "").strip()
            else:
                text = str(response)
            
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            data = json.loads(text.strip())
            
            entities = [
                KGEntity(
                    id=str(uuid.uuid4()),
                    name=e["name"],
                    entity_type=e.get("type", "concept"),
                    description=e.get("description", "")
                )
                for e in data.get("entities", [])
            ]
            
            relationships = []
            for r in data.get("relationships", []):
                source_name = r.get("source", "")
                target_name = r.get("target", "")
                source_id = next((e.id for e in entities if e.name == source_name), str(uuid.uuid4()))
                target_id = next((e.id for e in entities if e.name == target_name), str(uuid.uuid4()))
                
                relationships.append(KGRelationship(
                    id=str(uuid.uuid4()),
                    source_entity=source_id,
                    target_entity=target_id,
                    relationship_type=r.get("type", "related_to"),
                    description=r.get("description", "")
                ))
            
            kg = UserKnowledgeGraph(
                user_id=user_id,
                entities=entities,
                relationships=relationships,
                last_updated=datetime.now().isoformat()
            )
            
            await self.set_user_kg(user_id, kg)
            logger.info(f"[知识图谱] 从对话提取完成: {user_id}, 实体: {len(entities)}, 关系: {len(relationships)}")
            return kg
            
        except Exception as e:
            logger.error(f"[知识图谱] 从对话提取失败: {e}")
            return UserKnowledgeGraph(user_id=user_id)
    
    async def merge_external_knowledge(self, request: KGFusionRequest) -> KGFusionResponse:
        """融合外部知识到用户图谱"""
        try:
            existing_kg = await self.get_user_kg(request.user_id)
            
            if existing_kg is None:
                existing_kg = UserKnowledgeGraph(user_id=request.user_id)
            
            new_entities = []
            updated_entities = []
            
            for ext_entity in request.external_entities:
                ext_name = ext_entity.get("name", "")
                existing = next((e for e in existing_kg.entities if e.name == ext_name), None)
                
                if existing is None:
                    new_entity = KGEntity(
                        id=str(uuid.uuid4()),
                        name=ext_name,
                        entity_type=ext_entity.get("type", "concept"),
                        description=ext_entity.get("description", ""),
                        source="external"
                    )
                    existing_kg.entities.append(new_entity)
                    new_entities.append(ext_name)
                else:
                    if request.merge_strategy == "weighted":
                        existing.properties["external_data"] = ext_entity.get("properties", {})
                    updated_entities.append(ext_name)
            
            for ext_rel in request.external_relationships:
                source_name = ext_rel.get("source", "")
                target_name = ext_rel.get("target", "")
                
                source_id = next((e.id for e in existing_kg.entities if e.name == source_name), None)
                target_id = next((e.id for e in existing_kg.entities if e.name == target_name), None)
                
                if source_id and target_id:
                    new_rel = KGRelationship(
                        id=str(uuid.uuid4()),
                        source_entity=source_id,
                        target_entity=target_id,
                        relationship_type=ext_rel.get("type", "related_to"),
                        description=ext_rel.get("description", ""),
                        source="external"
                    )
                    existing_kg.relationships.append(new_rel)
            
            existing_kg.last_updated = datetime.now().isoformat()
            await self.set_user_kg(request.user_id, existing_kg)
            
            return KGFusionResponse(
                success=True,
                user_id=request.user_id,
                merged_entities_count=len(new_entities) + len(updated_entities),
                merged_relationships_count=len(request.external_relationships),
                new_entities=new_entities,
                updated_entities=updated_entities,
                message=f"成功融合{len(new_entities)}个新实体"
            )
            
        except Exception as e:
            logger.error(f"[知识图谱] 融合外部知识失败: {e}")
            return KGFusionResponse(
                success=False,
                user_id=request.user_id,
                merged_entities_count=0,
                merged_relationships_count=0,
                message=str(e)
            )
    
    async def query_kg(self, request: KGQueryRequest) -> KGQueryResult:
        """查询知识图谱"""
        try:
            kg = await self.get_user_kg(request.user_id)
            
            if kg is None:
                return KGQueryResult()
            
            entities = kg.entities
            if request.entity_types:
                entities = [e for e in entities if e.entity_type in request.entity_types]
            
            entities = entities[:request.max_results]
            
            if not entities:
                return KGQueryResult(entities=[], relationships=[])
            
            entity_ids = {e.id for e in entities}
            relationships = [r for r in kg.relationships 
                          if r.source_entity in entity_ids or r.target_entity in entity_ids]
            
            context = self._build_context(entities, relationships)
            
            return KGQueryResult(
                entities=entities,
                relationships=relationships,
                context=context
            )
            
        except Exception as e:
            logger.error(f"[知识图谱] 查询失败: {e}")
            return KGQueryResult()
    
    def _build_context(self, entities: List[KGEntity], relationships: List[KGRelationship]) -> str:
        """构建查询上下文"""
        if not entities:
            return ""
        
        entity_texts = [f"{e.name}({e.entity_type})" for e in entities[:5]]
        context = f"用户关注的实体: {', '.join(entity_texts)}"
        
        if relationships:
            rel_texts = []
            for r in relationships[:3]:
                source = next((e.name for e in entities if e.id == r.source_entity), "")
                target = next((e.name for e in entities if e.id == r.target_entity), "")
                if source and target:
                    rel_texts.append(f"{source}-{r.relationship_type}-{target}")
            if rel_texts:
                context += f"\n关系: {', '.join(rel_texts)}"
        
        return context
    
    async def load_simulated_kg(self, simulated_data: SimulatedKGData) -> UserKnowledgeGraph:
        """加载模拟知识图谱数据（冷启动用）"""
        try:
            entities = [
                KGEntity(
                    id=str(uuid.uuid4()),
                    name=e["name"],
                    entity_type=e.get("type", "concept"),
                    description=e.get("description", ""),
                    source="simulation"
                )
                for e in simulated_data.entities
            ]
            
            entity_map = {e.name: e.id for e in entities}
            
            relationships = []
            for r in simulated_data.relationships:
                source_id = entity_map.get(r.get("source", ""))
                target_id = entity_map.get(r.get("target", ""))
                
                if source_id and target_id:
                    relationships.append(KGRelationship(
                        id=str(uuid.uuid4()),
                        source_entity=source_id,
                        target_entity=target_id,
                        relationship_type=r.get("type", "related_to"),
                        description=r.get("description", ""),
                        source="simulation"
                    ))
            
            kg = UserKnowledgeGraph(
                user_id=simulated_data.user_id,
                entities=entities,
                relationships=relationships,
                last_updated=datetime.now().isoformat()
            )
            
            await self.set_user_kg(simulated_data.user_id, kg)
            logger.info(f"[知识图谱] 加载模拟数据完成: {simulated_data.user_id}")
            return kg
            
        except Exception as e:
            logger.error(f"[知识图谱] 加载模拟数据失败: {e}")
            return UserKnowledgeGraph(user_id=simulated_data.user_id)
    
    async def get_kg_context_for_chat(self, user_id: str) -> str:
        """获取用于对话的知识图谱上下文"""
        try:
            kg_result = await self.query_kg(KGQueryRequest(
                user_id=user_id,
                query="用户兴趣和话题",
                max_results=5
            ))
            
            return kg_result.context
            
        except Exception as e:
            logger.warning(f"[知识图谱] 获取对话上下文失败: {e}")
            return ""


user_knowledge_graph_service = UserKnowledgeGraphService()
