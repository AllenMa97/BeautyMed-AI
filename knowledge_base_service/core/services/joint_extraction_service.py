# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-17
# Copyright (c) 2026. All rights reserved.

"""
实体关系联合抽取服务
符合 NLP 领域命名习惯(Joint Extraction)
基于 LLM 的联合抽取,构建知识图谱
"""

import json
import asyncio
import hashlib
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from core.llm_client import LLMClient
from core.vector_store.embedding_client import EmbeddingClient
from config.settings import get_embedding_dimension

from core.llm_prompts.joint_extraction_prompt import (
    get_joint_extraction_prompt,
)
from api.schemas.joint_extraction_schemas import (
    Entity,
    Relation,
    JointExtractionResult,
    KnowledgeGraphStats
)


class JointExtractionService:
    """实体关系联合抽取服务"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: str = "qwen-flash",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        embedding_dimension: int = None
    ):
        embedding_dimension = embedding_dimension or get_embedding_dimension()
        """
        初始化联合抽取服务
        
        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大 token 数
            embedding_dimension: embedding 维度
        """
        self.client = LLMClient(
            api_key=api_key,
            base_url=base_url,
            default_model=model
        )
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        self.embedding_client = EmbeddingClient(dimension=embedding_dimension)
        
        self.entity_embeddings = {}
        self.relation_embeddings = {}
        
        self.knowledge_graph = {
            "entities": {},
            "relations": [],
            "chunk_to_entities": {},
            "entity_to_chunks": {}
        }
        
        self.storage_path = Path("data/knowledge_graph")
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def _generate_entity_id(self, entity_name: str) -> str:
        """生成实体 ID"""
        return f"entity_{hashlib.md5(entity_name.encode()).hexdigest()[:8]}"
    
    def _find_similar_entity(self, entity_name: str, threshold: float = 0.85) -> Optional[str]:
        """
        查找相似的实体(用于去重)
        
        Args:
            entity_name: 实体名称
            threshold: 相似度阈值
        
        Returns:
            相似实体的 ID,如果没有找到则返回 None
        """
        from difflib import SequenceMatcher
        
        if entity_name in self.knowledge_graph["entities"]:
            return self._generate_entity_id(entity_name)
        
        candidates = []
        for existing_id, existing_entity in self.knowledge_graph["entities"].items():
            similarity = SequenceMatcher(None, entity_name, existing_entity.entity_name).ratio()
            if similarity >= 0.7:
                candidates.append((existing_id, existing_entity.entity_name, similarity))
        
        if not candidates:
            return None
        
        for existing_id, existing_name, similarity in candidates:
            if similarity >= 0.90:
                print(f"  → 实体去重(高相似度): '{entity_name}' → '{existing_name}' (相似度:{similarity:.2f})")
                return existing_id
        
        for existing_id, existing_name, similarity in candidates:
            if 0.80 <= similarity < 0.90:
                if (entity_name in existing_name or existing_name in entity_name):
                    product_suffixes = ['霜', '乳', '液', '精华', '面膜', '水', '油']
                    entity_suffix = next((s for s in product_suffixes if entity_name.endswith(s)), None)
                    existing_suffix = next((s for s in product_suffixes if existing_name.endswith(s)), None)
                    
                    if entity_suffix and existing_suffix and entity_suffix != existing_suffix:
                        print(f"  → 跳过去重(不同产品类型): '{entity_name}' vs '{existing_name}'")
                        continue
                
                print(f"  → 实体去重(包含关系): '{entity_name}' → '{existing_name}' (相似度:{similarity:.2f})")
                return existing_id
        
        return None
    
    def _generate_relation_id(self, source_id: str, target_id: str, relation_type: str) -> str:
        """生成关系 ID"""
        content = f"{source_id}_{target_id}_{relation_type}"
        return f"relation_{hashlib.md5(content.encode()).hexdigest()[:8]}"
    
    async def _call_llm(self, prompt: str, max_retries: int = 3, validate_fields: bool = True) -> Dict[str, Any]:
        """
        调用 LLM(支持重试机制)
        
        Args:
            prompt: Prompt 字符串
            max_retries: 最大重试次数,默认 3 次
            validate_fields: 是否验证返回字段,默认 True
        
        Returns:
            LLM 返回的 JSON 结果
        """
        for attempt in range(max_retries):
            try:
                content = await self.client.chat(
                    messages=[
                        {"role": "system", "content": "你是一个专业的知识图谱构建专家,擅长从文本中提取实体和关系。请严格按照 JSON 格式返回结果,不要包含任何其他文字。"},
                        {"role": "user", "content": prompt}
                    ],
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    response_format={"type": "json_object"}
                )
                
                try:
                    result = json.loads(content)
                    
                    if not isinstance(result, dict):
                        raise ValueError("返回结果不是 JSON 对象")
                    
                    if validate_fields:
                        if "entities" not in result or "relations" not in result:
                            raise ValueError("返回结果缺少 entities 或 relations 字段")
                    
                    return result
                    
                except json.JSONDecodeError as e:
                    print(f"JSON 解析失败 (尝试 {attempt+1}/{max_retries}): {e}")
                    print(f"原始内容前 200 字符:{content[:200]}...")
                    
                    fixed_content = self._try_fix_json(content)
                    if fixed_content:
                        try:
                            result = json.loads(fixed_content)
                            print(f"✓ JSON 修复成功")
                            return result
                        except Exception as fix_error:
                            print(f"✗ JSON 修复失败:{fix_error}")
                    
                    if attempt < max_retries - 1:
                        print(f"→ 重试调用 LLM...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        print(f"✗ JSON 解析最终失败,返回空结果")
                        if validate_fields:
                            return {"entities": [], "relations": []}
                        else:
                            return {}
                
            except Exception as e:
                print(f"LLM 调用失败 (尝试 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    if validate_fields:
                        return {"entities": [], "relations": []}
                    else:
                        return {}
        
        if validate_fields:
            return {"entities": [], "relations": []}
        else:
            return {}
    
    def _try_fix_json(self, content: str) -> Optional[str]:
        """尝试修复常见的 JSON 错误"""
        original = content
        
        content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'^```\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'```$', '', content, flags=re.MULTILINE)
        
        content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        content = re.sub(r',\s*}', '}', content)
        content = re.sub(r',\s*]', ']', content)
        
        content = re.sub(r'"([^"]*)$', r'"\1"', content)
        
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)
        
        content = content.replace('"', '"').replace('"', '"')
        content = content.replace('"', '"').replace('"', '"')
        
        def escape_newlines_in_strings(match):
            key = match.group(1)
            value = match.group(2)
            value = value.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
            return f'"{key}": "{value}"'
        
        content = re.sub(r'"([^"]+)":\s*"([^"]*[\n\r][^"]*)"', escape_newlines_in_strings, content)
        
        content = content.strip()
        if not content.startswith('{') and not content.startswith('['):
            start = min(content.find('{'), content.find('['))
            if start != -1:
                content = content[start:]
        
        last_brace = max(content.rfind('}'), content.rfind(']'))
        if last_brace != -1 and last_brace < len(content) - 1:
            content = content[:last_brace + 1]
        
        def fix_description_field(match):
            key = match.group(1)
            value = match.group(2)
            value = value.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
            return f'"{key}": "{value}"'
        
        long_text_fields = ['description', 'summary', 'reason', 'original_relation']
        for field in long_text_fields:
            content = re.sub(
                rf'"{field}":\s*"([^"]*[\n\r][^"]*)"',
                fix_description_field,
                content
            )
        
        return content if content != original else None
    
    async def joint_extract(
        self,
        text: str,
        chunk_id: str,
        document_id: Optional[str] = None,
        domain: str = "medical_aesthetics",
        max_entities: int = 20,
        max_relations: int = 30
    ) -> JointExtractionResult:
        """
        从文本中联合抽取实体和关系
        
        Args:
            text: 待提取的文本
            chunk_id: Chunk ID
            document_id: 文档 ID(可选)
            domain: 领域
            max_entities: 最大实体数量
            max_relations: 最大关系数量
        
        Returns:
            JointExtractionResult 对象
        """
        try:
            prompt = get_joint_extraction_prompt(
                text=text,
                domain=domain,
                max_entities=max_entities,
                max_relations=max_relations,
                chunk_id=chunk_id
            )
            
            result = await self._call_llm(prompt)
            
            entities = []
            entity_name_to_id = {}
            
            for entity_data in result.get("entities", []):
                entity_name = entity_data.get("entity_name", "")
                entity_id = self._generate_entity_id(entity_name)
                
                entity = Entity(
                    entity_id=entity_id,
                    entity_name=entity_name,
                    entity_type=entity_data.get("entity_type", "unknown"),
                    confidence=entity_data.get("confidence", 1.0),
                    metadata=entity_data.get("metadata", {})
                )
                
                entities.append(entity)
                entity_name_to_id[entity_name] = entity_id
            
            relations = []
            for relation_data in result.get("relations", []):
                source_name = relation_data.get("source_entity", "")
                target_name = relation_data.get("target_entity", "")
                
                if source_name in entity_name_to_id and target_name in entity_name_to_id:
                    source_id = entity_name_to_id[source_name]
                    target_id = entity_name_to_id[target_name]
                    
                    relation = Relation(
                        relation_id=self._generate_relation_id(
                            source_id, target_id, relation_data.get("relation_type", "")
                        ),
                        source_entity_id=source_id,
                        target_entity_id=target_id,
                        relation_type=relation_data.get("relation_type", "unknown"),
                        confidence=relation_data.get("confidence", 1.0),
                        metadata=relation_data.get("metadata", {})
                    )
                    
                    relations.append(relation)
            
            extraction = JointExtractionResult(
                chunk_id=chunk_id,
                entities=entities,
                relations=relations,
                extraction_time=datetime.now().isoformat(),
                model_name=self.model
            )
            
            if entities or relations:
                await self._update_knowledge_graph(extraction, document_id)
            
            return extraction
            
        except Exception as e:
            print(f"joint_extract 失败 (chunk_id={chunk_id}): {e}")
            return JointExtractionResult(
                chunk_id=chunk_id,
                entities=[],
                relations=[],
                extraction_time=datetime.now().isoformat(),
                model_name=self.model
            )
    
    async def _update_knowledge_graph(
        self,
        extraction: JointExtractionResult,
        document_id: Optional[str] = None
    ):
        """更新知识图谱(支持实体去重)"""
        chunk_id = extraction.chunk_id
        
        old_to_new_id_map = {}
        
        for entity in extraction.entities:
            if entity.entity_id in self.knowledge_graph["entities"]:
                old_to_new_id_map[entity.entity_id] = entity.entity_id
                
                if entity.entity_id not in self.knowledge_graph["entity_to_chunks"]:
                    self.knowledge_graph["entity_to_chunks"][entity.entity_id] = []
                if chunk_id not in self.knowledge_graph["entity_to_chunks"][entity.entity_id]:
                    self.knowledge_graph["entity_to_chunks"][entity.entity_id].append(chunk_id)
                
                continue
            
            similar_entity_id = self._find_similar_entity(entity.entity_name, threshold=0.85)
            
            if similar_entity_id:
                old_to_new_id_map[entity.entity_id] = similar_entity_id
                
                existing_entity = self.knowledge_graph["entities"][similar_entity_id]
                
                if similar_entity_id not in self.knowledge_graph["entity_to_chunks"]:
                    self.knowledge_graph["entity_to_chunks"][similar_entity_id] = []
                if chunk_id not in self.knowledge_graph["entity_to_chunks"][similar_entity_id]:
                    self.knowledge_graph["entity_to_chunks"][similar_entity_id].append(chunk_id)
                
                print(f"  → 实体去重:'{entity.entity_name}' → '{existing_entity.entity_name}'")
            else:
                self.knowledge_graph["entities"][entity.entity_id] = entity
                
                if entity.entity_id not in self.knowledge_graph["entity_to_chunks"]:
                    self.knowledge_graph["entity_to_chunks"][entity.entity_id] = []
                
                if chunk_id not in self.knowledge_graph["entity_to_chunks"][entity.entity_id]:
                    self.knowledge_graph["entity_to_chunks"][entity.entity_id].append(chunk_id)
        
        for relation in extraction.relations:
            new_source_id = old_to_new_id_map.get(relation.source_entity_id, relation.source_entity_id)
            new_target_id = old_to_new_id_map.get(relation.target_entity_id, relation.target_entity_id)
            
            updated_relation = Relation(
                relation_id=self._generate_relation_id(new_source_id, new_target_id, relation.relation_type),
                source_entity_id=new_source_id,
                target_entity_id=new_target_id,
                relation_type=relation.relation_type,
                confidence=relation.confidence,
                metadata=relation.metadata
            )
            
            self.knowledge_graph["relations"].append(updated_relation)
        
        self.knowledge_graph["chunk_to_entities"][chunk_id] = [
            old_to_new_id_map.get(e.entity_id, e.entity_id) for e in extraction.entities
        ]
        
        await self._save_knowledge_graph()
        
        if len(self.knowledge_graph["entities"]) % 500 == 0:
            print(f"\n  🔄 实体数量达到 {len(self.knowledge_graph['entities'])},执行 Embedding 去重...")
            await self._embedding_based_deduplication()
    
    async def _embedding_based_deduplication(self, threshold: float = 0.85):
        """基于 Embedding 的实体去重"""
        if not self.entity_embeddings:
            await self._compute_entity_embeddings()
        
        entity_ids = list(self.knowledge_graph["entities"].keys())
        merge_pairs = []
        
        for i, entity_id_1 in enumerate(entity_ids):
            for entity_id_2 in entity_ids[i+1:]:
                if entity_id_1 not in self.entity_embeddings or entity_id_2 not in self.entity_embeddings:
                    continue
                
                emb1 = self.entity_embeddings[entity_id_1]
                emb2 = self.entity_embeddings[entity_id_2]
                
                similarity = self._cosine_similarity(emb1, emb2)
                
                if similarity >= threshold:
                    merge_pairs.append((entity_id_1, entity_id_2, similarity))
        
        merged_count = 0
        for entity_id_1, entity_id_2, similarity in merge_pairs:
            if entity_id_1 not in self.knowledge_graph["entities"] or entity_id_2 not in self.knowledge_graph["entities"]:
                continue
            
            entity_1 = self.knowledge_graph["entities"][entity_id_1]
            entity_2 = self.knowledge_graph["entities"][entity_id_2]
            
            if len(entity_1.entity_name) <= len(entity_2.entity_name):
                keep_id, remove_id = entity_id_1, entity_id_2
            else:
                keep_id, remove_id = entity_id_2, entity_id_1
            
            if remove_id in self.knowledge_graph["entity_to_chunks"]:
                if keep_id not in self.knowledge_graph["entity_to_chunks"]:
                    self.knowledge_graph["entity_to_chunks"][keep_id] = []
                self.knowledge_graph["entity_to_chunks"][keep_id].extend(
                    self.knowledge_graph["entity_to_chunks"][remove_id]
                )
                del self.knowledge_graph["entity_to_chunks"][remove_id]
            
            for relation in self.knowledge_graph["relations"]:
                if relation.source_entity_id == remove_id:
                    relation.source_entity_id = keep_id
                if relation.target_entity_id == remove_id:
                    relation.target_entity_id = keep_id
            
            del self.knowledge_graph["entities"][remove_id]
            if remove_id in self.entity_embeddings:
                del self.entity_embeddings[remove_id]
            
            merged_count += 1
            print(f"    → Embedding 去重:'{entity_1.entity_name}' + '{entity_2.entity_name}' (相似度:{similarity:.2f})")
        
        if merged_count > 0:
            print(f"  ✓ Embedding 去重完成,合并了 {merged_count} 对实体")
            await self._save_knowledge_graph()
    
    async def save_knowledge_graph(self, output_file: str = None):
        """保存知识图谱到指定文件"""
        if output_file:
            try:
                graph_data = {
                    "entities": {
                        eid: e.dict() for eid, e in self.knowledge_graph["entities"].items()
                    },
                    "relations": [r.dict() for r in self.knowledge_graph["relations"]],
                    "chunk_to_entities": self.knowledge_graph["chunk_to_entities"],
                    "entity_to_chunks": self.knowledge_graph["entity_to_chunks"]
                }
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(graph_data, f, ensure_ascii=False, indent=2)
                    
            except Exception as e:
                print(f"保存知识图谱失败:{e}")
                raise
        else:
            await self._save_knowledge_graph()
    
    async def _save_knowledge_graph(self):
        """保存知识图谱到文件"""
        try:
            graph_file = self.storage_path / "knowledge_graph.json"
            
            serializable_graph = {
                "entities": {
                    eid: e.dict() for eid, e in self.knowledge_graph["entities"].items()
                },
                "relations": [r.dict() for r in self.knowledge_graph["relations"]],
                "chunk_to_entities": self.knowledge_graph["chunk_to_entities"],
                "entity_to_chunks": self.knowledge_graph["entity_to_chunks"]
            }
            
            with open(graph_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_graph, f, ensure_ascii=False, indent=2)
            
            if not self.entity_embeddings and self.knowledge_graph["entities"]:
                print("计算实体 Embedding...")
                await self._compute_entity_embeddings()
            
            if not self.relation_embeddings and self.knowledge_graph["relations"]:
                print("计算关系 Embedding...")
                await self._compute_relation_embeddings()
            
            embeddings_file = self.storage_path / "embeddings.json"
            embeddings_data = {
                "entity_embeddings": self.entity_embeddings,
                "relation_embeddings": self.relation_embeddings
            }
            with open(embeddings_file, 'w', encoding='utf-8') as f:
                json.dump(embeddings_data, f)
            
            print(f"Embedding 已保存:{len(self.entity_embeddings)} 个实体,{len(self.relation_embeddings)} 个关系")
                
        except Exception as e:
            print(f"保存知识图谱失败:{e}")
    
    async def load_knowledge_graph(self):
        """从文件加载知识图谱"""
        try:
            graph_file = self.storage_path / "knowledge_graph.json"
            
            if graph_file.exists():
                with open(graph_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.knowledge_graph["entities"] = {
                    eid: Entity(**e) for eid, e in data.get("entities", {}).items()
                }
                self.knowledge_graph["relations"] = [
                    Relation(**r) for r in data.get("relations", [])
                ]
                self.knowledge_graph["chunk_to_entities"] = data.get("chunk_to_entities", {})
                self.knowledge_graph["entity_to_chunks"] = data.get("entity_to_chunks", {})
                
                print(f"知识图谱加载成功:{len(self.knowledge_graph['entities'])} 个实体,"
                      f"{len(self.knowledge_graph['relations'])} 个关系")
                
                embeddings_file = self.storage_path / "embeddings.json"
                if embeddings_file.exists():
                    with open(embeddings_file, 'r', encoding='utf-8') as f:
                        embeddings_data = json.load(f)
                    self.entity_embeddings = embeddings_data.get("entity_embeddings", {})
                    self.relation_embeddings = embeddings_data.get("relation_embeddings", {})
                    print(f"Embedding 加载成功:{len(self.entity_embeddings)} 个实体,"
                          f"{len(self.relation_embeddings)} 个关系")
                else:
                    print("Embedding 文件不存在,将在首次查询时计算...")
                
        except Exception as e:
            print(f"加载知识图谱失败:{e}")
    
    async def _compute_entity_embeddings(self):
        """预先计算所有实体的 embedding"""
        if not self.knowledge_graph["entities"]:
            return
        
        entity_names = []
        entity_ids = []
        for entity_id, entity in self.knowledge_graph["entities"].items():
            entity_names.append(entity.entity_name)
            entity_ids.append(entity_id)
        
        embeddings = await self.embedding_client.embed_batch(entity_names)
        
        self.entity_embeddings = {
            entity_id: embedding
            for entity_id, embedding in zip(entity_ids, embeddings)
        }
    
    async def _compute_relation_embeddings(self):
        """预先计算所有关系的 embedding"""
        if not self.knowledge_graph["relations"]:
            return
        
        relation_types = []
        relation_ids = []
        for idx, relation in enumerate(self.knowledge_graph["relations"]):
            relation_types.append(relation.relation_type)
            relation_ids.append(f"relation_{idx}")
        
        embeddings = await self.embedding_client.embed_batch(relation_types)
        
        self.relation_embeddings = {
            relation_id: embedding
            for relation_id, embedding in zip(relation_ids, embeddings)
        }
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    async def get_knowledge_graph_stats(self) -> KnowledgeGraphStats:
        """获取知识图谱统计信息"""
        entity_types = {}
        for entity in self.knowledge_graph["entities"].values():
            etype = entity.entity_type
            entity_types[etype] = entity_types.get(etype, 0) + 1
        
        relation_types = {}
        for relation in self.knowledge_graph["relations"]:
            rtype = relation.relation_type
            relation_types[rtype] = relation_types.get(rtype, 0) + 1
        
        stats = KnowledgeGraphStats(
            total_entities=len(self.knowledge_graph["entities"]),
            total_relations=len(self.knowledge_graph["relations"]),
            entity_types=entity_types,
            relation_types=relation_types,
            chunks_with_entities=len(self.knowledge_graph["chunk_to_entities"])
        )
        
        return stats
    
    async def batch_joint_extract(
        self,
        chunks: List[Dict[str, Any]],
        domain: str = "medical_aesthetics",
        max_entities_per_chunk: int = 50,
        max_relations_per_chunk: int = 100,
        max_concurrent: int = 10
    ) -> List[JointExtractionResult]:
        """批量联合抽取实体和关系(支持并行处理)"""
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_chunk_with_semaphore(chunk: Dict[str, Any], index: int):
            async with semaphore:
                try:
                    result = await self.joint_extract(
                        text=chunk.get("text", ""),
                        chunk_id=chunk.get("chunk_id", ""),
                        document_id=chunk.get("document_id"),
                        domain=domain,
                        max_entities=max_entities_per_chunk,
                        max_relations=max_relations_per_chunk
                    )
                    return result
                except Exception as e:
                    print(f"Chunk {chunk.get('chunk_id', f'#{index}')} 抽取失败:{e}")
                    return JointExtractionResult(
                        chunk_id=chunk.get("chunk_id", f"chunk_{index}"),
                        entities=[],
                        relations=[],
                        extraction_time=datetime.now().isoformat(),
                        model_name=self.model
                    )
        
        tasks = [
            process_chunk_with_semaphore(chunk, i)
            for i, chunk in enumerate(chunks)
        ]
        
        results = await asyncio.gather(*tasks)
        
        return list(results)
