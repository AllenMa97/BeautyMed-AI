"""Embedding存储管理器 - 按C码分文件存储，线程安全"""
import json
import os
import threading
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from algorithm_services.utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class EmbeddingMeta:
    """Embedding元信息"""
    text: str
    embedding: List[float]
    model_name: str
    created_at: str
    updated_at: str
    source: str
    extra_info: Optional[Dict[str, Any]] = None


class EmbeddingStorage:
    """Embedding存储管理器 - 按source分文件存储，线程安全"""

    def __init__(self, storage_path: str = "data/embeddings"):
        self.storage_path = storage_path
        self.embeddings: Dict[str, EmbeddingMeta] = {}
        self._lock = threading.Lock()
        self._dirty_sources: set = set()
        self._load_all_embeddings()

    def _get_source_file(self, source: str) -> str:
        """获取某个source对应的JSON文件路径"""
        safe_name = source.replace("/", "_").replace("\\", "_").replace(" ", "_")
        return os.path.join(self.storage_path, f"{safe_name}.json")

    def _load_all_embeddings(self):
        """加载所有已存储的embeddings（支持分割文件）"""
        os.makedirs(self.storage_path, exist_ok=True)

        if not os.path.exists(self.storage_path):
            return

        total_loaded = 0
        
        # 收集所有基础文件名（处理分割文件）
        file_groups = {}
        for filename in os.listdir(self.storage_path):
            if not filename.endswith(".json"):
                continue
            
            # 跳过 manifest 文件
            if filename == "manifest.json":
                continue
            
            # 处理分割文件：question_bank_C35_part1.json, question_bank_C35_part2.json
            # 以及普通文件：question_bank_C35.json
            if "_part" in filename:
                # 分割文件：提取基础名
                base_name = filename.rsplit("_part", 1)[0]
                if base_name not in file_groups:
                    file_groups[base_name] = []
                file_groups[base_name].append(filename)
            else:
                # 普通文件
                base_name = filename[:-5]  # 去掉 .json
                if base_name not in file_groups:
                    file_groups[base_name] = []
                file_groups[base_name].append(filename)
        
        # 按组加载文件
        for base_name, filenames in file_groups.items():
            # 对分割文件按序号排序
            if len(filenames) > 1:
                filenames.sort()
            
            for filename in filenames:
                filepath = os.path.join(self.storage_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    count = 0
                    for text, meta_data in data.items():
                        if not isinstance(meta_data, dict):
                            continue
                        try:
                            self.embeddings[text] = EmbeddingMeta(**meta_data)
                            count += 1
                        except Exception:
                            continue

                    total_loaded += count
                    if count > 0:
                        logger.info(f"[Embedding存储] 从 {filename} 加载了 {count} 个embeddings")

                except json.JSONDecodeError as e:
                    logger.warning(f"[Embedding存储] 文件 {filename} JSON解析失败: {e}，跳过")
                except Exception as e:
                    logger.warning(f"[Embedding存储] 加载文件 {filename} 失败: {e}，跳过")

        logger.info(f"[Embedding存储] 总计加载了 {total_loaded} 个embeddings")

    def _save_source(self, source: str):
        """保存某个source的embeddings到对应文件（原子写入）"""
        os.makedirs(self.storage_path, exist_ok=True)

        filepath = self._get_source_file(source)
        with self._lock:
            data = {}
            for text, meta in self.embeddings.items():
                if meta.source == source:
                    data[text] = asdict(meta)

        tmp_filepath = filepath + ".tmp"
        with open(tmp_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp_filepath, filepath)

    def _save_manifest(self):
        """保存manifest汇总文件"""
        os.makedirs(self.storage_path, exist_ok=True)

        with self._lock:
            source_stats = {}
            for meta in self.embeddings.values():
                if meta.source not in source_stats:
                    source_stats[meta.source] = {
                        "count": 0,
                        "model": meta.model_name,
                        "file": os.path.basename(self._get_source_file(meta.source))
                    }
                source_stats[meta.source]["count"] += 1

            manifest = {
                "total_embeddings": len(self.embeddings),
                "total_sources": len(source_stats),
                "last_updated": datetime.now().isoformat(),
                "sources": source_stats
            }

        manifest_path = os.path.join(self.storage_path, "manifest.json")
        tmp_path = manifest_path + ".tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, manifest_path)

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本的embedding"""
        with self._lock:
            if text in self.embeddings:
                return self.embeddings[text].embedding
            return None

    def add_embedding(self, text: str, embedding: List[float],
                      model_name: str = "text-embedding-v3",
                      source: str = "unknown",
                      extra_info: Optional[Dict[str, Any]] = None) -> bool:
        """添加embedding（线程安全）"""
        current_time = datetime.now().isoformat()

        with self._lock:
            if text in self.embeddings:
                self.embeddings[text].updated_at = current_time
                self.embeddings[text].embedding = embedding
            else:
                self.embeddings[text] = EmbeddingMeta(
                    text=text,
                    embedding=embedding,
                    model_name=model_name,
                    created_at=current_time,
                    updated_at=current_time,
                    source=source,
                    extra_info=extra_info
                )
            self._dirty_sources.add(source)

        return True

    def flush(self):
        """将所有脏数据写入磁盘"""
        with self._lock:
            sources_to_save = list(self._dirty_sources)
            self._dirty_sources.clear()

        for source in sources_to_save:
            try:
                self._save_source(source)
                count = sum(1 for m in self.embeddings.values() if m.source == source)
                logger.info(f"[Embedding存储] 保存 {source}: {count} 个embeddings")
            except Exception as e:
                logger.warning(f"[Embedding存储] 保存 {source} 失败: {e}")

        if sources_to_save:
            try:
                self._save_manifest()
            except Exception as e:
                logger.warning(f"[Embedding存储] 保存manifest失败: {e}")

    def batch_add_embeddings(self, embeddings_data: List[Dict[str, Any]]) -> int:
        """批量添加embeddings（线程安全，最后统一flush）"""
        current_time = datetime.now().isoformat()
        added_count = 0

        with self._lock:
            for data in embeddings_data:
                text = data['text']
                embedding = data['embedding']
                model_name = data.get('model_name', 'text-embedding-v3')
                source = data.get('source', 'unknown')
                extra_info = data.get('extra_info')

                if text in self.embeddings:
                    self.embeddings[text].updated_at = current_time
                    self.embeddings[text].embedding = embedding
                else:
                    self.embeddings[text] = EmbeddingMeta(
                        text=text,
                        embedding=embedding,
                        model_name=model_name,
                        created_at=current_time,
                        updated_at=current_time,
                        source=source,
                        extra_info=extra_info
                    )
                    added_count += 1
                self._dirty_sources.add(source)

        self.flush()
        logger.info(f"[Embedding存储] 批量添加了 {added_count} 个新embeddings")
        return added_count

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            if not self.embeddings:
                return {
                    'total_embeddings': 0,
                    'model_distribution': {},
                    'source_distribution': {}
                }

            model_dist = {}
            source_dist = {}

            for meta in self.embeddings.values():
                model_dist[meta.model_name] = model_dist.get(meta.model_name, 0) + 1
                source_dist[meta.source] = source_dist.get(meta.source, 0) + 1

            return {
                'total_embeddings': len(self.embeddings),
                'model_distribution': model_dist,
                'source_distribution': source_dist,
            }

    def export_to_json(self, export_path: str):
        """导出embeddings到指定路径"""
        with self._lock:
            data = {}
            for text, meta in self.embeddings.items():
                data[text] = asdict(meta)

        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

        logger.info(f"[Embedding存储] 导出embeddings到: {export_path}")


_embedding_storage = None


def get_embedding_storage() -> EmbeddingStorage:
    """获取Embedding存储单例"""
    global _embedding_storage
    if _embedding_storage is None:
        _embedding_storage = EmbeddingStorage()
    return _embedding_storage
