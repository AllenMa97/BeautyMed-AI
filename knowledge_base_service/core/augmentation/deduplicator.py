# Developer: 椹但路椹櫤鍕?
# Position: 澶фā鍨嬬畻娉曞伐绋嬪笀
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from typing import List, Dict, Any, Set, Tuple
import logging
import re

logger = logging.getLogger(__name__)


class SemanticDeduplicator:
    def __init__(
        self,
        similarity_threshold: float = 0.85,
        min_hash_permutations: int = 128,
        use_minhash: bool = True,
    ):
        self.similarity_threshold = similarity_threshold
        self.min_hash_permutations = min_hash_permutations
        self.use_minhash = use_minhash
        
        self._hash_functions = None
    
    def deduplicate(
        self,
        chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not chunks:
            return []
        
        if self.use_minhash:
            return self._minhash_dedup(chunks)
        else:
            return self._simple_dedup(chunks)
    
    def _simple_dedup(
        self,
        chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        seen_hashes: Set[int] = set()
        unique_chunks = []
        
        for chunk in chunks:
            content = chunk.get("content", "")
            content_hash = hash(self._normalize_text(content))
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_chunks.append(chunk)
        
        return unique_chunks
    
    def _minhash_dedup(
        self,
        chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        try:
            from datasketch import MinHash, MinHashLSH
            return self._datasketch_dedup(chunks)
        except ImportError:
            logger.warning("datasketch not installed, falling back to simple dedup")
            return self._simple_dedup(chunks)
    
    def _datasketch_dedup(
        self,
        chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        from datasketch import MinHash, MinHashLSH
        
        lsh = MinHashLSH(
            threshold=self.similarity_threshold,
            num_perm=self.min_hash_permutations,
        )
        
        unique_chunks = []
        
        for idx, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            tokens = self._tokenize(content)
            
            mh = MinHash(num_perm=self.min_hash_permutations)
            for token in tokens:
                mh.update(token.encode("utf-8"))
            
            key = f"chunk_{idx}"
            
            if not lsh.query(mh):
                lsh.insert(key, mh)
                unique_chunks.append(chunk)
        
        return unique_chunks
    
    def _normalize_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s\u4e00-\u9fff]", "", text)
        return text.strip()
    
    def _tokenize(self, text: str) -> List[str]:
        text = self._normalize_text(text)
        
        tokens = []
        words = re.findall(r"\w+|[\u4e00-\u9fff]+", text)
        
        for word in words:
            if all(ord(c) >= 0x4E00 for c in word):
                tokens.extend(list(word))
            else:
                tokens.append(word)
        
        shingles = []
        for i in range(len(tokens) - 2):
            shingles.append("".join(tokens[i:i + 3]))
        
        return shingles if shingles else tokens
    
    def find_duplicates(
        self,
        chunks: List[Dict[str, Any]],
    ) -> List[Tuple[int, int, float]]:
        duplicates = []
        
        for i, chunk1 in enumerate(chunks):
            for j, chunk2 in enumerate(chunks[i + 1:], i + 1):
                similarity = self._calculate_similarity(
                    chunk1.get("content", ""),
                    chunk2.get("content", ""),
                )
                
                if similarity >= self.similarity_threshold:
                    duplicates.append((i, j, similarity))
        
        return duplicates
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        tokens1 = set(self._tokenize(text1))
        tokens2 = set(self._tokenize(text2))
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        return len(intersection) / len(union)
