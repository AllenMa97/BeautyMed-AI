# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import asyncio
import threading
import hashlib
import time
import json
import os
import torch
import torch.nn.functional as F
from typing import Dict, Any, List
from datetime import datetime
from algorithm_services.utils.logger import get_logger
from algorithm_services.core.services.self_evolution_service import self_evolution_service
from algorithm_services.session.session_factory import session_manager
from algorithm_services.large_model.llm_factory import get_embedding_client
from algorithm_services.core.managers.knowledge_store import knowledge_manager

logger = get_logger(__name__)


class SelfEvolutionManager:
    """
    Self-evolution manager
    """
    
    def __init__(self):
        self.is_running = False
        self.analysis_interval = 600
        self.knowledge_management_interval = 1800
        self.similarity_threshold = 0.8
        self.last_no_sessions_log = 0
        self.no_sessions_log_interval = 300
        self.thread = None
        self._embedding_client = None
        
        self.knowledge_manager = knowledge_manager
        logger.info(f"SelfEvolutionManager init, knowledge: behavior={len(self.knowledge_manager.get_store('behavior').items)}, feature={len(self.knowledge_manager.get_store('feature').items)}, interaction={len(self.knowledge_manager.get_store('interaction').items)}, correction={len(self.knowledge_manager.get_store('correction').items)}")
    
    def start_periodic_analysis(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._periodic_analysis_worker, daemon=True)
            self.thread.start()
            self.knowledge_management_thread = threading.Thread(target=self._knowledge_management_worker, daemon=True)
            self.knowledge_management_thread.start()
            logger.info("Self-evolution manager started")
    
    def stop_periodic_analysis(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        if hasattr(self, 'knowledge_management_thread') and self.knowledge_management_thread:
            self.knowledge_management_thread.join(timeout=2)
        logger.info("Self-evolution manager stopped")
    
    def _periodic_analysis_worker(self):
        while self.is_running:
            try:
                asyncio.run(self.perform_system_analysis())
                for _ in range(int(self.analysis_interval)):
                    if not self.is_running:
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Analysis worker error: {e}")
                time.sleep(60)
    
    def _knowledge_management_worker(self):
        while self.is_running:
            try:
                asyncio.run(self._perform_knowledge_management())
                for _ in range(int(self.knowledge_management_interval)):
                    if not self.is_running:
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Knowledge management worker error: {e}")
                time.sleep(60)
    
    async def _perform_knowledge_management(self):
        try:
            logger.info(f"Knowledge management start, size: {len(self.knowledge_manager.get_all_knowledge())}")
            removed_count = self._remove_duplicate_knowledge()
            similar_removed_count = await self._remove_similar_knowledge()
            logger.info(f"Knowledge management done: removed={removed_count}, similar_removed={similar_removed_count}, current_size={len(self.knowledge_manager.get_all_knowledge())}")
        except Exception as e:
            logger.error(f"Knowledge management error: {e}")
    
    def _remove_duplicate_knowledge(self) -> int:
        all_knowledge = self.knowledge_manager.get_all_knowledge()
        original_size = len(all_knowledge)
        unique_knowledge = {}
        
        for key, value in all_knowledge.items():
            content_hash = hashlib.md5(str(value.content).encode()).hexdigest()
            if content_hash not in unique_knowledge:
                unique_knowledge[content_hash] = (key, value)
        
        new_knowledge_base = {k: v for k, v in unique_knowledge.values()}
        removed_count = original_size - len(new_knowledge_base)
        return removed_count
    
    async def _remove_similar_knowledge(self) -> int:
        all_knowledge = self.knowledge_manager.get_all_knowledge()
        
        if len(all_knowledge) < 2:
            return 0
        
        try:
            items = list(all_knowledge.items())
            
            embeddings = []
            texts = []
            valid_indices = []
            missing_embedding_keys = []
            
            for i, (key, value) in enumerate(items):
                emb = value.embedding
                if emb is not None:
                    embeddings.append(emb)
                    texts.append(value.content)
                    valid_indices.append(i)
                else:
                    missing_embedding_keys.append((i, key, value))
            
            if missing_embedding_keys:
                logger.info(f"Found {len(missing_embedding_keys)} items without embedding, recalculating...")
                try:
                    embedding_client = get_embedding_client()
                    for i, key, value in missing_embedding_keys:
                        try:
                            new_emb = await embedding_client.get_embedding(
                                type('Req', (), {'text': value.content, 'model': 'text-embedding-v3', 'dimensions': 1024})()
                            )
                            if new_emb:
                                self.knowledge_manager.get_store(value.metadata.type if value.metadata else 'behavior').update_embedding(key, new_emb)
                                embeddings.append(new_emb)
                                texts.append(value.content)
                        except Exception as e:
                            logger.warning(f"Recalculate embedding failed: {key}, {e}")
                except Exception as e:
                    logger.warning(f"Cannot get embedding client: {e}")
            
            if not embeddings:
                logger.warning("No embeddings, skip similarity detection")
                return 0
            
            logger.info(f"Using {len(embeddings)} embeddings for dedup...")
            
            embeddings_tensor = torch.tensor(embeddings, dtype=torch.float32)
            n = len(items)
            
            if n < 500:
                return self._remove_similar_by_cosine(embeddings_tensor, items)
            else:
                return self._remove_similar_by_ann(embeddings_tensor, items)
            
        except Exception as e:
            logger.error(f"Similarity detection error: {e}")
            return 0
    
    def _remove_similar_by_cosine(self, embeddings_tensor: torch.Tensor, items: list) -> int:
        embeddings_norm = F.normalize(embeddings_tensor, p=2, dim=1)
        similarity_matrix = torch.mm(embeddings_norm, embeddings_norm.t())
        
        n = similarity_matrix.size(0)
        to_remove = set()
        
        for i in range(n):
            if i in to_remove:
                continue
            for j in range(i + 1, n):
                if j in to_remove:
                    continue
                if similarity_matrix[i, j].item() > self.similarity_threshold:
                    to_remove.add(j)
        
        for idx in to_remove:
            key = items[idx][0]
            knowledge_type = items[idx][1].metadata.type if items[idx][1].metadata else 'behavior'
            self.knowledge_manager.get_store(knowledge_type).delete(key)
        
        logger.info(f"Cosine dedup removed: {len(to_remove)}")
        return len(to_remove)
    
    def _remove_similar_by_ann(self, embeddings_tensor: torch.Tensor, items: list) -> int:
        return self._remove_similar_by_cosine(embeddings_tensor, items)
    
    async def _add_knowledge_entry(self, key: str, value: str):
        try:
            if self._embedding_client is None:
                self._embedding_client = get_embedding_client()
        except Exception as e:
            logger.warning(f"Cannot get embedding client: {e}")
            self._embedding_client = None
        
        new_embedding = None
        if self._embedding_client:
            try:
                new_embedding = await self._embedding_client.get_embedding(
                    type('EmbeddingRequest', (), {'text': str(value), 'model': 'text-embedding-v3', 'dimensions': 1024})()
                )
            except Exception as e:
                logger.warning(f"Calculate embedding failed: {e}")
        
        if new_embedding is None:
            logger.warning("No embedding, skip similarity detection, add directly")
            self.knowledge_manager.get_store("behavior").add(content=value, source="system")
            return
        
        new_embedding_tensor = torch.tensor(new_embedding, dtype=torch.float32)
        
        all_knowledge = self.knowledge_manager.get_all_knowledge()
        if all_knowledge:
            existing_embeddings = []
            existing_items = []
            for k, v in all_knowledge.items():
                if v.embedding:
                    existing_embeddings.append(v.embedding)
                    existing_items.append((k, v))
            
            if existing_embeddings:
                existing_tensor = torch.tensor(existing_embeddings, dtype=torch.float32)
                existing_norm = F.normalize(existing_tensor, p=2, dim=1)
                new_norm = F.normalize(new_embedding_tensor.unsqueeze(0), p=2, dim=1)
                similarities = torch.mm(new_norm, existing_norm.t()).squeeze()
                
                max_sim, max_idx = similarities.max(0)
                if max_sim.item() > self.similarity_threshold:
                    logger.info(f"Similar knowledge found, skip adding: {max_sim.item()}")
                    return
        
        self.knowledge_manager.get_store("behavior").add(content=value, embedding=new_embedding, source="system")
        logger.info(f"Knowledge added: {value[:50]}")
    
    async def perform_system_analysis(self):
        try:
            sessions = list(session_manager.sessions.values())
            current_time = time.time()
            
            if not sessions:
                if current_time - self.last_no_sessions_log > self.no_sessions_log_interval:
                    logger.info("No active sessions, skip analysis")
                    self.last_no_sessions_log = current_time
                return
            
            logger.info(f"Start system analysis, sessions: {len(sessions)}")
            
            try:
                # 从 session 中提取需要的参数
                user_profile = {}
                error_records = []
                recent_dialogs = []
                
                for session in sessions:
                    if hasattr(session, 'user_profile'):
                        user_profile = session.user_profile or {}
                    if hasattr(session, 'error_records'):
                        error_records = session.error_records or []
                    if hasattr(session, 'turns'):
                        recent_dialogs = [
                            {"user": turn.user_query, "ai": turn.ai_response}
                            for turn in session.turns[-5:]
                            if hasattr(turn, 'user_query') and turn.user_query
                        ]
                
                evolution_results = await self_evolution_service.analyze_system_performance(
                    user_profile=user_profile,
                    error_records=error_records,
                    recent_dialogs=recent_dialogs
                )
                
                if evolution_results:
                    await self._apply_evolution_results(evolution_results)
                    
            except Exception as e:
                logger.error(f"Evolution analysis error: {e}")
                
        except Exception as e:
            logger.error(f"System analysis error: {e}")
    
    async def _apply_evolution_results(self, evolution_results: Dict[str, Any]):
        applied = 0
        
        knowledge_updates = evolution_results.get("knowledge_updates", [])
        for update in knowledge_updates:
            if isinstance(update, dict):
                for k, v in update.items():
                    await self._add_knowledge_entry(k, v)
            elif isinstance(update, str):
                await self._add_knowledge_entry(None, update)
        
        behavior_improvements = evolution_results.get("behavior_improvements", [])
        for improvement in behavior_improvements:
            if isinstance(improvement, dict):
                improvement_key = f"behavior_{hashlib.md5(str(improvement).encode()).hexdigest()[:16]}"
                self.knowledge_manager.get_store("behavior").add(content=str(improvement), source="system_analysis")
            elif isinstance(improvement, str):
                self.knowledge_manager.get_store("behavior").add(content=improvement, source="system_analysis")
            applied += 1
        
        interaction_adjustments = evolution_results.get("interaction_adjustments", [])
        for adjustment in interaction_adjustments:
            if isinstance(adjustment, dict):
                scenario = adjustment.get("scenario", "general")
                strategy = adjustment.get("strategy", str(adjustment))
            else:
                scenario = "general"
                strategy = str(adjustment)
            self.knowledge_manager.get_store("interaction").add(content=strategy, source="system_analysis")
            applied += 1
        
        feature_enhancements = evolution_results.get("feature_enhancements", [])
        for enhancement in feature_enhancements:
            self.knowledge_manager.get_store("feature").add(content=str(enhancement), source="system_analysis")
            applied += 1
        
        logger.info(f"Evolution applied: {applied} items")
    
    async def process_correction_learning(self, user_query: str, ai_response: str, corrected_info: str, session_id: str = None):
        try:
            if self._embedding_client is None:
                self._embedding_client = get_embedding_client()
            
            correction_type = "correction"
            
            self.knowledge_manager.get_store(correction_type).add(
                content=f"User: {user_query}\nAI: {ai_response}\nCorrection: {corrected_info}",
                source="user_correction",
                source_session=session_id
            )
            logger.info(f"Correction learning added: {correction_type}")
            
        except Exception as e:
            logger.error(f"Correction learning error: {e}")
    
    def get_knowledge(self, key: str = None):
        return self.knowledge_manager.get_all_knowledge()
    
    def get_behavior(self):
        return self.knowledge_manager.get_store("behavior").get_all()


self_evolution_manager = SelfEvolutionManager()
