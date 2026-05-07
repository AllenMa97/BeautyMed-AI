# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class TokenBudgetManager:
    def __init__(
        self,
        max_tokens: int = 4000,
        reserved_tokens: int = 500,
        chars_per_token: float = 4.0,
    ):
        self.max_tokens = max_tokens
        self.reserved_tokens = reserved_tokens
        self.chars_per_token = chars_per_token
    
    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        
        char_count = len(text)
        chinese_chars = sum(1 for c in text if ord(c) >= 0x4E00)
        other_chars = char_count - chinese_chars
        
        token_estimate = int(chinese_chars / 2 + other_chars / self.chars_per_token)
        
        return max(1, token_estimate)
    
    def apply_budget(
        self,
        chunks: List[Dict[str, Any]],
        max_tokens: int = None,
    ) -> List[Dict[str, Any]]:
        if not chunks:
            return []
        
        budget = max_tokens or (self.max_tokens - self.reserved_tokens)
        
        selected = []
        total_tokens = 0
        
        for chunk in chunks:
            content = chunk.get("content", "")
            chunk_tokens = self.count_tokens(content)
            
            if total_tokens + chunk_tokens <= budget:
                selected.append(chunk)
                total_tokens += chunk_tokens
            else:
                remaining = budget - total_tokens
                
                if remaining > 50:
                    truncated = self._truncate_chunk(chunk, remaining)
                    if truncated:
                        selected.append(truncated)
                break
        
        logger.debug(f"Token budget: {budget}, used: {total_tokens}, chunks: {len(selected)}")
        
        return selected
    
    def _truncate_chunk(
        self,
        chunk: Dict[str, Any],
        max_tokens: int,
    ) -> Dict[str, Any]:
        content = chunk.get("content", "")
        
        max_chars = int(max_tokens * self.chars_per_token)
        
        if len(content) <= max_chars:
            return chunk
        
        truncated_content = content[:max_chars]
        
        last_period = truncated_content.rfind("。")
        last_newline = truncated_content.rfind("\n")
        
        split_point = max(last_period, last_newline)
        
        if split_point > max_chars * 0.5:
            truncated_content = truncated_content[:split_point + 1]
        
        truncated_chunk = chunk.copy()
        truncated_chunk["content"] = truncated_content + "..."
        truncated_chunk["truncated"] = True
        
        return truncated_chunk
    
    def estimate_total_tokens(
        self,
        chunks: List[Dict[str, Any]],
    ) -> int:
        return sum(self.count_tokens(c.get("content", "")) for c in chunks)
    
    def get_budget_info(
        self,
        chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        total_tokens = self.estimate_total_tokens(chunks)
        budget = self.max_tokens - self.reserved_tokens
        
        return {
            "total_tokens": total_tokens,
            "max_tokens": self.max_tokens,
            "reserved_tokens": self.reserved_tokens,
            "available_budget": budget,
            "within_budget": total_tokens <= budget,
            "utilization": min(1.0, total_tokens / budget) if budget > 0 else 0,
        }
