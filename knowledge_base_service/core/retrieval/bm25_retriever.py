# Developer: 椹但路椹櫤鍕?
# Position: 澶фā鍨嬬畻娉曞伐绋嬪笀
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import json
import math
import re
from typing import List, Dict, Any
from pathlib import Path
import logging
from collections import defaultdict

from .base_retriever import BaseRetriever, RetrievalQuery, RetrievalResult

logger = logging.getLogger(__name__)


class BM25Retriever(BaseRetriever):
    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        index_path: str = None,
    ):
        super().__init__(name="bm25")
        self.k1 = k1
        self.b = b
        self.index_path = Path(index_path) if index_path else None
        
        self.documents: Dict[str, str] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.avg_doc_length: float = 0.0
        self.inverted_index: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.doc_freqs: Dict[str, int] = defaultdict(int)
        self.N: int = 0
    
    def tokenize(self, text: str) -> List[str]:
        text = text.lower()
        tokens = re.findall(r"\w+|[\u4e00-\u9fff]+", text)
        
        result = []
        for token in tokens:
            if len(token) == 1 and ord(token[0]) >= 0x4E00:
                result.append(token)
            elif len(token) > 1:
                if all(ord(c) >= 0x4E00 for c in token):
                    result.extend(list(token))
                else:
                    result.append(token)
        
        return result
    
    def add_document(self, doc_id: str, content: str):
        self.documents[doc_id] = content
        tokens = self.tokenize(content)
        self.doc_lengths[doc_id] = len(tokens)
        
        term_freqs: Dict[str, int] = defaultdict(int)
        for token in tokens:
            term_freqs[token] += 1
        
        for term, freq in term_freqs.items():
            self.inverted_index[term][doc_id] = freq
            self.doc_freqs[term] += 1
        
        self.N = len(self.documents)
        self.avg_doc_length = sum(self.doc_lengths.values()) / self.N if self.N > 0 else 0
    
    def add_documents(self, docs: Dict[str, str]):
        for doc_id, content in docs.items():
            self.add_document(doc_id, content)
    
    def calculate_idf(self, term: str) -> float:
        df = self.doc_freqs.get(term, 0)
        if df == 0:
            return 0.0
        return math.log((self.N - df + 0.5) / (df + 0.5) + 1)
    
    def calculate_bm25_score(
        self,
        query_tokens: List[str],
        doc_id: str,
    ) -> float:
        score = 0.0
        doc_length = self.doc_lengths.get(doc_id, 0)
        
        if doc_length == 0 or self.avg_doc_length == 0:
            return 0.0
        
        for term in query_tokens:
            if term not in self.inverted_index:
                continue
            
            tf = self.inverted_index[term].get(doc_id, 0)
            if tf == 0:
                continue
            
            idf = self.calculate_idf(term)
            
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
            
            score += idf * numerator / denominator
        
        return score
    
    async def retrieve(
        self,
        query: RetrievalQuery,
        top_k: int = 20,
    ) -> List[RetrievalResult]:
        if not self.documents:
            logger.warning("No documents indexed for BM25 retrieval")
            return []
        
        query_tokens = self.tokenize(query.query)
        
        if not query_tokens:
            return []
        
        candidate_docs = set()
        for token in query_tokens:
            if token in self.inverted_index:
                candidate_docs.update(self.inverted_index[token].keys())
        
        if not candidate_docs:
            return []
        
        scores = []
        for doc_id in candidate_docs:
            score = self.calculate_bm25_score(query_tokens, doc_id)
            if score > 0:
                scores.append((doc_id, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, (doc_id, score) in enumerate(scores[:top_k]):
            results.append(RetrievalResult(
                id=doc_id,
                content=self.documents.get(doc_id, ""),
                score=score,
                source="bm25",
                rank=idx + 1,
            ))
        
        return self._normalize_scores(results)
    
    def save_index(self, path: str = None):
        save_path = Path(path) if path else self.index_path
        if not save_path:
            return
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "documents": self.documents,
            "doc_lengths": self.doc_lengths,
            "inverted_index": {k: dict(v) for k, v in self.inverted_index.items()},
            "doc_freqs": dict(self.doc_freqs),
            "N": self.N,
            "avg_doc_length": self.avg_doc_length,
            "k1": self.k1,
            "b": self.b,
        }
        
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_index(self, path: str = None):
        load_path = Path(path) if path else self.index_path
        if not load_path or not load_path.exists():
            return
        
        with open(load_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.documents = data.get("documents", {})
        self.doc_lengths = data.get("doc_lengths", {})
        self.inverted_index = defaultdict(lambda: defaultdict(int))
        for term, docs in data.get("inverted_index", {}).items():
            for doc_id, freq in docs.items():
                self.inverted_index[term][doc_id] = freq
        self.doc_freqs = defaultdict(int, data.get("doc_freqs", {}))
        self.N = data.get("N", 0)
        self.avg_doc_length = data.get("avg_doc_length", 0.0)
        self.k1 = data.get("k1", self.k1)
        self.b = data.get("b", self.b)
