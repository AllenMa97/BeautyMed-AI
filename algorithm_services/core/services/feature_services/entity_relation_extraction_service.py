# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.api.schemas.feature_schemas.entity_relation_extraction_schemas import (
    EntityRelationExtractionRequest, EntityRelationExtractionResponseData,
    EntityRelationExtractionResponse, RecognizedEntity, ExtractedRelation
)
from algorithm_services.core.prompts.features.entity_relation_extraction_prompt import get_entity_relation_extraction_prompt
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_PROVIDER = "aliyun"
DEFAULT_MODEL = "qwen-flash"
LLM_REQUEST_MAX_TOKENS = int(2048)
LLM_REQUEST_TEMPERATURE = float(0.2)


class EntityRelationExtractionService:
    """实体与关系联合抽取Service（Joint Entity and Relation Extraction）"""
    description = "实体与关系联合抽取，提取用户输入中的关键实体及实体间关系"

    async def extract(self, request: EntityRelationExtractionRequest) -> EntityRelationExtractionResponse:
        prompt = get_entity_relation_extraction_prompt(
            user_input=request.user_input,
            context=request.context,
        )

        llm_request = LLMRequest(
            system_prompt=prompt["system_prompt"],
            user_prompt=prompt["user_prompt"],
            temperature=LLM_REQUEST_TEMPERATURE,
            max_tokens=LLM_REQUEST_MAX_TOKENS,
            response_format={"type": "json_object"},
            provider=DEFAULT_PROVIDER,
            model=DEFAULT_MODEL,
            enable_context_cache=True
        )
        try:
            llm_result = await llm_client_singleton.call_llm(llm_request)
            logger.info(f"实体与关系联合抽取LLM返回结果：{llm_result}")

            entities_list = []
            raw_entities = llm_result.get("entities", [])
            for item in raw_entities:
                try:
                    entity = RecognizedEntity(
                        entity_name=item.get("entity_name", ""),
                        entity_type=item.get("entity_type", ""),
                        confidence=float(item.get("confidence", 0.0))
                    )
                    entities_list.append(entity)
                except Exception as e:
                    logger.warning(f"单个实体解析失败：{str(e)}，跳过该实体")
                    continue

            relations_list = []
            raw_relations = llm_result.get("relations", [])
            for item in raw_relations:
                try:
                    relation = ExtractedRelation(
                        subject=item.get("subject", ""),
                        subject_type=item.get("subject_type", ""),
                        predicate=item.get("predicate", ""),
                        object=item.get("object", ""),
                        object_type=item.get("object_type", ""),
                        confidence=float(item.get("confidence", 0.0))
                    )
                    relations_list.append(relation)
                except Exception as e:
                    logger.warning(f"单个关系解析失败：{str(e)}，跳过该关系")
                    continue

            response_data = EntityRelationExtractionResponseData(
                entities=entities_list,
                relations=relations_list
            )

            return EntityRelationExtractionResponse(
                code=200,
                msg="entity and relation extraction success",
                data=response_data
            )

        except Exception as e:
            logger.error(f"实体与关系联合抽取结果解析失败：{str(e)}")
            tmp_data = EntityRelationExtractionResponseData(
                entities=[], relations=[], entity_count=0, relation_count=0
            )
            return EntityRelationExtractionResponse(
                code=500,
                msg=f"实体与关系联合抽取结果解析失败：{str(e)}",
                data=tmp_data
            )


entity_relation_extraction_service = EntityRelationExtractionService()
