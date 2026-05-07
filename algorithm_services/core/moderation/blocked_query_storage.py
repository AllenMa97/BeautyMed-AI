"""拦截Query存储管理器 - 按C码分文件存储，支持增量学习，线程安全"""
import json
import os
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from algorithm_services.utils.logger import get_logger
from algorithm_services.core.moderation.embedding_storage import get_embedding_storage


logger = get_logger(__name__)


@dataclass
class BlockedQuery:
    """被拦截的Query数据"""
    query: str
    detection_level: str
    detection_reason: str
    timestamp: str = ""
    extra_info: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class BlockedQueryStorage:
    """拦截Query存储管理器 - 按C码分文件存储"""

    def __init__(self, storage_path: str = "data/blocked_queries"):
        self.storage_path = storage_path
        self.blocked_queries: List[BlockedQuery] = []
        self._lock = threading.Lock()
        self._load_all_blocked_queries()

    def _get_level_file(self, level: str) -> str:
        safe_name = level.replace(" ", "_")
        return os.path.join(self.storage_path, f"{safe_name}.json")

    def _load_all_blocked_queries(self):
        os.makedirs(self.storage_path, exist_ok=True)

        if not os.path.exists(self.storage_path):
            return

        total_loaded = 0
        for filename in os.listdir(self.storage_path):
            if not filename.endswith(".json") or filename == "manifest.json":
                continue

            filepath = os.path.join(self.storage_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                count = 0
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    try:
                        self.blocked_queries.append(BlockedQuery(**item))
                        count += 1
                    except Exception:
                        continue

                total_loaded += count
                if count > 0:
                    logger.info(f"[拦截Query存储] 从 {filename} 加载了 {count} 条记录")

            except json.JSONDecodeError as e:
                logger.warning(f"[拦截Query存储] 文件 {filename} JSON解析失败: {e}，跳过")
            except Exception as e:
                logger.warning(f"[拦截Query存储] 加载文件 {filename} 失败: {e}，跳过")

        logger.info(f"[拦截Query存储] 总计加载了 {total_loaded} 条拦截记录")

    def _save_level(self, level: str):
        os.makedirs(self.storage_path, exist_ok=True)

        filepath = self._get_level_file(level)
        data = [asdict(q) for q in self.blocked_queries if q.detection_level == level]

        tmp_filepath = filepath + ".tmp"
        with open(tmp_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp_filepath, filepath)

    def _save_manifest(self):
        os.makedirs(self.storage_path, exist_ok=True)

        level_stats = {}
        for q in self.blocked_queries:
            level_stats[q.detection_level] = level_stats.get(q.detection_level, 0) + 1

        manifest = {
            "total_blocked_queries": len(self.blocked_queries),
            "total_levels": len(level_stats),
            "last_updated": datetime.now().isoformat(),
            "levels": level_stats
        }

        manifest_path = os.path.join(self.storage_path, "manifest.json")
        tmp_path = manifest_path + ".tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, manifest_path)

    def add_blocked_query(self, query: str, detection_level: str, detection_reason: str,
                          embedding: Optional[List[float]] = None,
                          similarity: Optional[float] = None,
                          matched_question: Optional[str] = None,
                          risk_subclass: Optional[str] = None,
                          extra_info: Optional[Dict[str, Any]] = None) -> bool:
        with self._lock:
            for existing in self.blocked_queries:
                if existing.query == query:
                    logger.debug(f"[拦截Query存储] 重复拦截，跳过: {query[:50]}...")
                    return False

            blocked_query = BlockedQuery(
                query=query,
                detection_level=detection_level,
                detection_reason=detection_reason,
                extra_info={
                    'similarity': similarity,
                    'matched_question': matched_question,
                    'risk_subclass': risk_subclass,
                    **(extra_info or {})
                }
            )
            self.blocked_queries.append(blocked_query)

        try:
            self._save_level(detection_level)
            self._save_manifest()
        except Exception as e:
            logger.warning(f"[拦截Query存储] 保存失败: {e}")

        if embedding:
            try:
                storage = get_embedding_storage()
                storage.add_embedding(
                    text=query,
                    embedding=embedding,
                    model_name="text-embedding-v3",
                    source=f"blocked_{detection_level}",
                    extra_info={'detection_level': detection_level, 'risk_subclass': risk_subclass}
                )
                storage.flush()
            except Exception as e:
                logger.warning(f"[拦截Query存储] 保存embedding失败: {e}")

        logger.info(f"[拦截Query存储] 添加拦截query ({detection_level}): {query[:50]}...")
        return True

    def add_to_question_bank_candidates(self, query: str, embedding: List[float],
                                        detection_level: str, detection_reason: str,
                                        similarity: Optional[float] = None,
                                        matched_question: Optional[str] = None,
                                        risk_subclass: Optional[str] = None) -> bool:
        candidate = {
            'query': query,
            'embedding': embedding,
            'detection_level': detection_level,
            'detection_reason': detection_reason,
            'similarity': similarity,
            'matched_question': matched_question,
            'risk_subclass': risk_subclass,
            'timestamp': datetime.now().isoformat(),
            'approved': False,
            'review_count': 0
        }

        candidates_file = os.path.join(self.storage_path, "question_bank_candidates.json")

        candidates = []
        if os.path.exists(candidates_file):
            try:
                with open(candidates_file, 'r', encoding='utf-8') as f:
                    candidates = json.load(f)
            except Exception as e:
                logger.warning(f"[拦截Query存储] 加载候选列表失败: {e}")

        candidates.append(candidate)

        with open(candidates_file, 'w', encoding='utf-8') as f:
            json.dump(candidates, f, ensure_ascii=False, indent=2)

        logger.info(f"[拦截Query存储] 添加题库候选: {query[:50]}...")
        return True

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            if not self.blocked_queries:
                return {
                    'total_blocked_queries': 0,
                    'level_distribution': {},
                    'recent_queries': []
                }

            level_dist = {}
            for query in self.blocked_queries:
                level_dist[query.detection_level] = level_dist.get(query.detection_level, 0) + 1

            recent_queries = [
                {
                    'query': q.query[:50] + '...' if len(q.query) > 50 else q.query,
                    'level': q.detection_level,
                    'timestamp': q.timestamp
                }
                for q in self.blocked_queries[-10:]
            ]

            return {
                'total_blocked_queries': len(self.blocked_queries),
                'level_distribution': level_dist,
                'recent_queries': recent_queries,
            }


_blocked_query_storage = None


def get_blocked_query_storage() -> BlockedQueryStorage:
    global _blocked_query_storage
    if _blocked_query_storage is None:
        _blocked_query_storage = BlockedQueryStorage()
    return _blocked_query_storage
