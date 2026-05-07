"""
记忆召回服务
支持多维度检索：关键词、时间线、实体
预留向量检索接口
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from typing import List

from algorithm_services.api.schemas.feature_schemas.memory_recall_schemas import (
    MemoryRecallRequest, MemoryRecallResponse, MemoryRecallResponseData
)
from algorithm_services.api.schemas.feature_schemas.entity_relation_extraction_schemas import EntityRelationExtractionRequest
from algorithm_services.core.services.feature_services.entity_relation_extraction_service import entity_relation_extraction_service
from algorithm_services.session.session_factory import session_manager
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryRecallService:
    """记忆召回服务"""

    async def recall(self, request: MemoryRecallRequest) -> MemoryRecallResponse:
        logger.info(f"记忆召回服务收到请求: {request.recall_type}")

        try:
            entities = await self._extract_entities(request.user_input)
            memories = await self._recall_memories(
                user_id=request.user_id,
                user_input=request.user_input,
                entities=entities,
                recall_type=request.recall_type,
                max_results=request.max_results
            )

            response_data = MemoryRecallResponseData(
                recalled_memories=memories,
                recall_method=request.recall_type,
                total_count=len(memories)
            )

            return MemoryRecallResponse(data=response_data)

        except Exception as e:
            logger.error(f"记忆召回失败: {e}")
            return MemoryRecallResponse(
                code=500,
                msg=f"记忆召回失败: {str(e)}",
                data=MemoryRecallResponseData(recalled_memories=[], recall_method="error", total_count=0)
            )

    async def _extract_entities(self, user_input: str) -> List[str]:
        """从用户输入中提取实体/关键词"""
        try:
            entity_request = EntityRelationExtractionRequest(
                user_input=user_input,
                context=""
            )
            result = await entity_relation_extraction_service.extract(entity_request)
            if result.code == 200 and result.data:
                entities = result.data.entities or []
                keywords = []
                for entity in entities:
                    if isinstance(entity, dict):
                        name = entity.get("entity_name", "")
                        if name:
                            keywords.append(name)
                    elif hasattr(entity, "entity_name"):
                        keywords.append(entity.entity_name)
                return keywords
        except Exception as e:
            logger.warning(f"实体提取失败: {e}")
        return []

    async def _recall_memories(
        self,
        user_id: str,
        user_input: str,
        entities: List[str],
        recall_type: str,
        max_results: int
    ) -> List[dict]:
        """召回记忆的核心逻辑"""
        all_sessions = await self._get_user_sessions(user_id)
        memories = []

        for session in all_sessions:
            dialog_summary = getattr(session, 'dialog_summary', None)
            if not dialog_summary:
                continue

            session_time = getattr(session, 'updated_at', None)
            session_context = getattr(session, 'context', '')

            score = 0
            matched_method = ""

            if recall_type in ["keyword", "mixed"]:
                keyword_score, keyword_method = self._keyword_match(user_input, dialog_summary, entities)
                score += keyword_score
                matched_method = keyword_method

            if recall_type in ["time", "mixed"]:
                time_score, time_method = self._time_match(user_input, session_time)
                score += time_score
                matched_method = matched_method or time_method

            if recall_type in ["entity", "mixed"]:
                entity_score, entity_method = self._entity_match(entities, dialog_summary)
                score += entity_score
                matched_method = matched_method or entity_method

            if score > 0:
                memories.append({
                    "summary": dialog_summary,
                    "session_id": session.session_id,
                    "timestamp": str(session_time) if session_time else None,
                    "score": score,
                    "method": matched_method,
                    "context": session_context[:200] if session_context else ""
                })

        memories.sort(key=lambda x: x["score"], reverse=True)
        return memories[:max_results]

    def _keyword_match(self, user_input: str, summary: str, entities: List[str]) -> tuple:
        """关键词匹配"""
        score = 0
        method = "keyword"

        user_input_lower = user_input.lower()
        summary_lower = summary.lower()

        for entity in entities:
            if entity.lower() in summary_lower:
                score += 10

        common_keywords = ["上次", "之前", "之前说", "之前提到的", "之前说的"]
        for kw in common_keywords:
            if kw in user_input_lower:
                score += 5

        return score, method if score > 0 else ""

    def _time_match(self, user_input: str, session_time) -> tuple:
        """时间线匹配"""
        score = 0
        method = "time"

        user_input_lower = user_input.lower()

        if "上次" in user_input_lower or "之前" in user_input_lower:
            score += 8
        elif "一开始" in user_input_lower or "最开始" in user_input_lower:
            score += 6
        elif "最近" in user_input_lower or "刚才" in user_input_lower:
            score += 7

        return score, method if score > 0 else ""

    def _entity_match(self, entities: List[str], summary: str) -> tuple:
        """实体匹配"""
        score = 0
        method = "entity"

        summary_lower = summary.lower()
        for entity in entities:
            if entity.lower() in summary_lower:
                score += 15

        return score, method if score > 0 else ""

    async def _get_user_sessions(self, user_id: str) -> List:
        """获取用户所有会话"""
        try:
            sessions = await session_manager.session_store.get_all_sessions()
            return [s for s in sessions if s.user_id == user_id]
        except Exception as e:
            logger.warning(f"获取用户会话失败: {e}")
            return []

    async def _vector_recall(self, query: str, user_id: str, top_k: int = 5) -> List[dict]:
        """
        向量检索接口（预留）
        TODO: 接入本地向量模型后实现
        """
        logger.info(f"向量检索预留接口被调用: query={query}, user_id={user_id}")
        return []


memory_recall_service = MemoryRecallService()
