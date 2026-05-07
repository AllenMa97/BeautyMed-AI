"""题库管理器 - 定期合并拦截query到题库"""
import json
import os
import shutil
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from algorithm_services.utils.logger import get_logger


logger = get_logger(__name__)


class QuestionBankManager:
    """题库管理器 - 负责定期合并拦截query到题库"""
    
    def __init__(self):
        self.candidates_file = "data/blocked_queries/question_bank_candidates.json"
        self.backup_dir = "data/blocked_queries/backups"
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def review_candidates(self, min_similarity: float = 0.9, 
                       min_frequency: int = 5, days_old: int = 7) -> List[Dict[str, Any]]:
        """审核候选问题"""
        if not os.path.exists(self.candidates_file):
            logger.warning(f"[题库管理器] 候选文件不存在: {self.candidates_file}")
            return []
        
        try:
            with open(self.candidates_file, 'r', encoding='utf-8') as f:
                candidates = json.load(f)
            
            cutoff_date = datetime.now() - timedelta(days=days_old)
            qualified_candidates = []
            
            for candidate in candidates:
                similarity = candidate.get('similarity', 0)
                frequency = candidate.get('frequency', 0)
                timestamp_str = candidate.get('timestamp', '')
                
                if similarity >= min_similarity and frequency >= min_frequency:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                        if timestamp <= cutoff_date:
                            qualified_candidates.append(candidate)
                    except:
                        continue
            
            logger.info(f"[题库管理器] 找到 {len(qualified_candidates)} 个符合条件的候选问题")
            return qualified_candidates
            
        except Exception as e:
            logger.warning(f"[题库管理器] 审核候选问题失败: {e}")
            return []
    
    def approve_candidates(self, candidate_indices: List[int]) -> int:
        """批准指定的候选问题"""
        if not os.path.exists(self.candidates_file):
            logger.warning(f"[题库管理器] 候选文件不存在: {self.candidates_file}")
            return 0
        
        try:
            with open(self.candidates_file, 'r', encoding='utf-8') as f:
                candidates = json.load(f)
            
            approved_count = 0
            for index in candidate_indices:
                if 0 <= index < len(candidates):
                    candidates[index]['approved'] = True
                    candidates[index]['review_count'] = candidates[index].get('review_count', 0) + 1
                    approved_count += 1
            
            with open(self.candidates_file, 'w', encoding='utf-8') as f:
                json.dump(candidates, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[题库管理器] 批准了 {approved_count} 个候选问题")
            return approved_count
            
        except Exception as e:
            logger.warning(f"[题库管理器] 批准候选问题失败: {e}")
            return 0
    
    def auto_approve_high_quality(self, min_similarity: float = 0.95, 
                                min_frequency: int = 10) -> int:
        """自动批准高质量候选问题"""
        if not os.path.exists(self.candidates_file):
            logger.warning(f"[题库管理器] 候选文件不存在: {self.candidates_file}")
            return 0
        
        try:
            with open(self.candidates_file, 'r', encoding='utf-8') as f:
                candidates = json.load(f)
            
            approved_count = 0
            for candidate in candidates:
                if candidate.get('approved', False):
                    continue
                
                similarity = candidate.get('similarity', 0)
                frequency = candidate.get('frequency', 0)
                
                if similarity >= min_similarity and frequency >= min_frequency:
                    candidate['approved'] = True
                    candidate['review_count'] = candidate.get('review_count', 0) + 1
                    approved_count += 1
            
            with open(self.candidates_file, 'w', encoding='utf-8') as f:
                json.dump(candidates, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[题库管理器] 自动批准了 {approved_count} 个高质量候选问题")
            return approved_count
            
        except Exception as e:
            logger.warning(f"[题库管理器] 自动批准候选问题失败: {e}")
            return 0
    
    def merge_to_question_bank(self, min_similarity: float = 0.9, 
                           min_frequency: int = 5) -> int:
        """合并已批准的候选问题到题库"""
        try:
            detector = get_question_bank_detector()
            
            added_count = detector.merge_candidates_to_question_bank(
                self.candidates_file, min_similarity, min_frequency
            )
            
            if added_count > 0:
                self._backup_candidates()
                self._clean_approved_candidates()
            
            return added_count
            
        except Exception as e:
            logger.warning(f"[题库管理器] 合并候选问题到题库失败: {e}")
            return 0
    
    def _backup_candidates(self):
        """备份候选文件"""
        if not os.path.exists(self.candidates_file):
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(self.backup_dir, f"question_bank_candidates_{timestamp}.json")
        
        import shutil
        shutil.copy2(self.candidates_file, backup_file)
        
        logger.info(f"[题库管理器] 备份候选文件到: {backup_file}")
    
    def _clean_approved_candidates(self):
        """清理已合并的候选问题"""
        if not os.path.exists(self.candidates_file):
            return
        
        try:
            with open(self.candidates_file, 'r', encoding='utf-8') as f:
                candidates = json.load(f)
            
            remaining_candidates = [
                candidate for candidate in candidates 
                if not candidate.get('approved', False)
            ]
            
            with open(self.candidates_file, 'w', encoding='utf-8') as f:
                json.dump(remaining_candidates, f, ensure_ascii=False, indent=2)
            
            removed_count = len(candidates) - len(remaining_candidates)
            logger.info(f"[题库管理器] 清理了 {removed_count} 个已合并的候选问题")
            
        except Exception as e:
            logger.warning(f"[题库管理器] 清理候选问题失败: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not os.path.exists(self.candidates_file):
            return {
                'total_candidates': 0,
                'approved_candidates': 0,
                'pending_candidates': 0
            }
        
        try:
            with open(self.candidates_file, 'r', encoding='utf-8') as f:
                candidates = json.load(f)
            
            approved_count = sum(1 for c in candidates if c.get('approved', False))
            pending_count = len(candidates) - approved_count
            
            return {
                'total_candidates': len(candidates),
                'approved_candidates': approved_count,
                'pending_candidates': pending_count,
                'candidates_file': self.candidates_file,
                'backup_dir': self.backup_dir
            }
            
        except Exception as e:
            logger.warning(f"[题库管理器] 获取统计信息失败: {e}")
            return {
                'total_candidates': 0,
                'approved_candidates': 0,
                'pending_candidates': 0
            }


_question_bank_manager = None


def get_question_bank_manager() -> QuestionBankManager:
    """获取题库管理器单例"""
    global _question_bank_manager
    if _question_bank_manager is None:
        _question_bank_manager = QuestionBankManager()
    return _question_bank_manager
