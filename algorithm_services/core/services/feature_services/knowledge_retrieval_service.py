# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.api.schemas.feature_schemas.knowledge_retrieval_schemas import (
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResponse,
    KnowledgeRetrievalData,
    ProductItem,
    KnowledgeEntry,
)
from algorithm_services.api.schemas.feature_schemas.entity_relation_extraction_schemas import (
    EntityRelationExtractionRequest,
)
from algorithm_services.core.services.feature_services.entity_relation_extraction_service import (
    entity_relation_extraction_service,
)
from algorithm_services.core.services.knowledge_base_client import knowledge_base_client
from algorithm_services.session.session_factory import session_manager
from algorithm_services.utils.logger import get_logger
from algorithm_services.utils.performance_monitor import monitor_async

logger = get_logger(__name__)


class KnowledgeRetrievalService:
    description = "知识检索，从知识库检索相关产品和知识条目"

    async def _ensure_entities_and_relations(
        self, request: KnowledgeRetrievalRequest
    ) -> tuple:
        entities = request.entities
        relations = request.relations

        if entities and relations:
            logger.info("使用请求中已有的实体和关系，跳过联合抽取的服务")
            return entities, relations

        session_data = getattr(request, "session_data", None)
        if session_data and isinstance(session_data, dict):
            session_entities = session_data.get("entities")
            session_relations = session_data.get("relations")
            if session_entities and session_relations:
                logger.info("从 session.session_data 中获取到实体和关系，跳过联合抽取的服务调用")
                return session_entities, session_relations

        logger.info("session 中也无实体关系数据，调用联合抽取服务")
        extraction_request = EntityRelationExtractionRequest(
            user_input=request.user_input,
            context="",
        )
        extraction_result = await entity_relation_extraction_service.extract(
            extraction_request
        )

        if extraction_result.code != 200:
            logger.warning(
                f"联合抽取失败: {extraction_result.msg}，将以空实体列表与空关系关系列表继续检索"
            )
            return [], []

        extracted_entities = []
        for entity in extraction_result.data.entities:
            extracted_entities.append(
                {
                    "entity_value": entity.entity_name,
                    "entity_type": entity.entity_type,
                    "confidence": entity.confidence,
                }
            )

        extracted_relations = []
        for relation in extraction_result.data.relations:
            extracted_relations.append(
                {
                    "subject": relation.subject,
                    "subject_type": relation.subject_type,
                    "predicate": relation.predicate,
                    "object": relation.object,
                    "object_type": relation.object_type,
                    "confidence": relation.confidence,
                }
            )

        logger.info(
            f"联合抽取完成，提取到 {len(extracted_entities)} 个实体、"
            f"{len(extracted_relations)} 个关系"
        )

        await self._update_session_with_extraction_result(
            request.session_id, extracted_entities, extracted_relations
        )

        return extracted_entities, extracted_relations

    async def _update_session_with_extraction_result(
        self, session_id: str, entities: list, relations: list
    ):
        try:
            session = await session_manager.get_session(session_id)
            if not session:
                logger.warning(f"session {session_id} 不存在，跳过实体关系回写")
                return

            if session.session_data is None:
                session.session_data = {}

            session.session_data["entities"] = entities
            session.session_data["relations"] = relations

            for entity in entities:
                if isinstance(entity, dict):
                    entity_type = entity.get("entity_type", "unknown")
                    entity_name = entity.get("entity_value", "")
                else:
                    continue
                if entity_type and entity_name:
                    if entity_type not in session.user_profile:
                        session.user_profile[entity_type] = []
                    if entity_name not in session.user_profile[entity_type]:
                        session.user_profile[entity_type].append(entity_name)

            await session_manager.update_session(
                session_id,
                session_data=session.session_data,
                user_profile=session.user_profile,
            )
            logger.info(
                f"联合抽取结果已回写 session {session_id}，"
                f"entities={len(entities)}, relations={len(relations)}"
            )
        except Exception as e:
            logger.warning(f"联合抽取结果回写 session 失败: {e}")

    @monitor_async(name="knowledge_retrieval_retrieve", log_threshold=1.0)
    async def retrieve(self, request: KnowledgeRetrievalRequest) -> KnowledgeRetrievalResponse:
        try:
            entities, relations = await self._ensure_entities_and_relations(request)

            if entities:
                entities = [
                    {"entity_value": e, "entity_type": "unknown"}
                    if isinstance(e, str)
                    else e
                    for e in entities
                ]

            search_type = "entries" if not request.personalize else request.search_type
            search_threshold = 0.2 if not request.personalize else 0.3
            search_top_k = request.top_k * 2 if not request.personalize else request.top_k

            result = await knowledge_base_client.search_knowledge(
                query=request.user_input,
                top_k=search_top_k,
                search_mode="hybrid",
                use_ann=True,
                threshold=search_threshold,
                search_type=search_type,
                entities=entities,
                relations=relations,
            )

            if result.code != 200:
                logger.warning(f"知识检索失败: {result.msg}")
                return KnowledgeRetrievalResponse(
                    code=500,
                    msg=result.msg,
                    data=KnowledgeRetrievalData(
                        products=[],
                        entries=[],
                        total_products=0,
                        total_entries=0,
                        query=request.user_input,
                    ),
                )

            products = [
                ProductItem(
                    id=p.id or "",
                    type="product",
                    name=p.name or "",
                    brand=p.brand,
                    category=p.category,
                    reference_price=p.reference_price,
                    description=p.description,
                    efficacy=p.efficacy,
                    applicable_skin=p.applicable_skin,
                    score=p.score,
                )
                for p in result.products
            ]

            entries = [
                KnowledgeEntry(
                    id=e.id or "",
                    type="entry",
                    title=e.title or "",
                    topic=e.topic,
                    content=e.content,
                    source_url=e.source_url,
                    score=e.score,
                )
                for e in result.entries
            ]

            logger.info(f"知识检索完成: search_type={search_type}, products={len(products)}, entries={len(entries)}, personalize={request.personalize}")
            for p in products[:3]:
                logger.info(f"  产品: {p.name} ({p.brand}), score={p.score}")
            for e in entries[:3]:
                logger.info(f"  知识: {e.title}, score={e.score}")

            return KnowledgeRetrievalResponse(
                code=200,
                msg="知识检索成功",
                data=KnowledgeRetrievalData(
                    products=products,
                    entries=entries,
                    total_products=len(products),
                    total_entries=len(entries),
                    query=request.user_input,
                ),
            )
        except Exception as e:
            logger.error(f"知识检索异常: {e}")
            return KnowledgeRetrievalResponse(
                code=500,
                msg=f"知识检索异常: {str(e)}",
                data=KnowledgeRetrievalData(
                    products=[],
                    entries=[],
                    total_products=0,
                    total_entries=0,
                    query=request.user_input,
                ),
            )


knowledge_retrieval_service = KnowledgeRetrievalService()
