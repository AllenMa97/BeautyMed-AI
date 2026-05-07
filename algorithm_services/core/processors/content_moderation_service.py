"""内容拦截服务 - C1-C42 全部并行检测，统一返回 ViolationResult"""
import asyncio
import os
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import numpy as np

load_dotenv(os.path.join(os.path.dirname(__file__), "../../config/MODERATION.env"))

from algorithm_services.utils.logger import get_logger
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest, EmbeddingRequest, get_embedding_client
from algorithm_services.core.prompts.features.content_moderation_prompt import get_content_moderation_prompt
from algorithm_services.core.moderation.keyword_detector import get_keyword_detector
from algorithm_services.core.moderation.parallel_keyword_detector import get_parallel_keyword_detector
from algorithm_services.core.moderation.question_bank_detector import get_question_bank_detector
from algorithm_services.core.moderation.blocked_query_storage import get_blocked_query_storage
from algorithm_services.core.moderation.embedding_storage import get_embedding_storage
from algorithm_services.core.prompts.features.moderation.political_moderation_prompt import get_political_moderation_prompt
from algorithm_services.core.prompts.features.moderation.violence_moderation_prompt import get_violence_moderation_prompt
from algorithm_services.core.prompts.features.moderation.pornography_moderation_prompt import get_pornography_moderation_prompt
from algorithm_services.core.prompts.features.moderation.gambling_moderation_prompt import get_gambling_moderation_prompt
from algorithm_services.core.prompts.features.moderation.drug_moderation_prompt import get_drug_moderation_prompt
from algorithm_services.core.prompts.features.moderation.hate_moderation_prompt import get_hate_moderation_prompt
from algorithm_services.core.prompts.features.moderation.fake_moderation_prompt import get_fake_moderation_prompt


logger = get_logger(__name__)

QUESTION_BANK_THRESHOLD_C35 = float(os.getenv("QUESTION_BANK_THRESHOLD_C35", "0.85"))
QUESTION_BANK_THRESHOLD_C36 = float(os.getenv("QUESTION_BANK_THRESHOLD_C36", "0.85"))
QUESTION_BANK_THRESHOLD_C37 = float(os.getenv("QUESTION_BANK_THRESHOLD_C37", "0.85"))
QUESTION_BANK_THRESHOLD_C38 = float(os.getenv("QUESTION_BANK_THRESHOLD_C38", "0.85"))
QUESTION_BANK_THRESHOLD_C39 = float(os.getenv("QUESTION_BANK_THRESHOLD_C39", "0.85"))
LLM_DETECTION_THRESHOLD = float(os.getenv("LLM_DETECTION_THRESHOLD", "0.85"))
BLOCKED_HISTORY_THRESHOLD = float(os.getenv("BLOCKED_HISTORY_THRESHOLD", "0.90"))

QUESTION_BANK_C_THRESHOLDS = {
    "C35": QUESTION_BANK_THRESHOLD_C35,
    "C36": QUESTION_BANK_THRESHOLD_C36,
    "C37": QUESTION_BANK_THRESHOLD_C37,
    "C38": QUESTION_BANK_THRESHOLD_C38,
    "C39": QUESTION_BANK_THRESHOLD_C39,
}

BLOCKLIST_FILE = "data/blocklist.txt"


@dataclass
class ViolationResult:
    """统一的违规检测结果"""
    is_violation: bool
    c_code: str
    reason: str
    keyword: str = ""
    risk_subclass: str = ""
    similarity: float = 0.0
    matched_question: str = ""
    extra: Optional[Dict[str, Any]] = None


@dataclass
class ModerateResult:
    """拦截结果"""
    blocked: bool
    reason: str = ""
    level: str = "pass"
    details: Optional[Dict[str, Any]] = None


@dataclass
class DetailedModerateResult(ModerateResult):
    """细粒度拦截结果"""
    violation_categories: List[str] = field(default_factory=list)
    detection_details: List[Dict[str, Any]] = field(default_factory=list)


class ContentModerationService:
    """内容拦截服务 - C1-C42 全部并行检测"""

    CATEGORIES = ['political', 'violence', 'pornography', 'gambling', 'drug', 'hate', 'fake']

    def __init__(self):
        self.blocklist: List[str] = []
        self.keyword_detector = None
        self.parallel_detector = None
        self.question_bank_detector = None
        self.blocked_query_storage = None
        self._load_blocklist()
        self._init_keyword_detector()
        self._init_parallel_detector()
        self._init_question_bank_detector()
        self._init_blocked_query_storage()

    def _load_blocklist(self):
        try:
            if os.path.exists(BLOCKLIST_FILE):
                with open(BLOCKLIST_FILE, 'r', encoding='utf-8') as f:
                    self.blocklist = [
                        line.strip() for line in f
                        if line.strip() and not line.strip().startswith('#')
                    ]
                logger.info(f"加载违规词表: {len(self.blocklist)} 条")
            else:
                logger.warning(f"违规词表文件不存在: {BLOCKLIST_FILE}")
        except Exception as e:
            logger.error(f"加载违规词表失败: {e}")

    def _init_keyword_detector(self):
        try:
            self.keyword_detector = get_keyword_detector()
            logger.info("关键词检测器初始化成功")
        except Exception as e:
            logger.warning(f"关键词检测器初始化失败: {e}")

    def _init_parallel_detector(self):
        try:
            self.parallel_detector = get_parallel_keyword_detector()
            logger.info("Excel并行检测器初始化成功")
        except Exception as e:
            logger.warning(f"Excel并行检测器初始化失败: {e}")

    def _init_question_bank_detector(self):
        try:
            self.question_bank_detector = get_question_bank_detector()
            logger.info("题库检测器初始化成功")
        except Exception as e:
            logger.warning(f"题库检测器初始化失败: {e}")

    def _init_blocked_query_storage(self):
        try:
            self.blocked_query_storage = get_blocked_query_storage()
            logger.info("拦截Query存储初始化成功")
        except Exception as e:
            logger.warning(f"拦截Query存储初始化失败: {e}")

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        try:
            client = get_embedding_client()
            embeddings = await client.get_embeddings_batch([text], model="text-embedding-v3", dimensions=1024)
            if embeddings and embeddings[0]:
                return embeddings[0]
            return None
        except Exception as e:
            logger.warning(f"[内容检测] 获取embedding失败: {e}")
            return None

    async def _store_blocked_query(self, text: str, detection_level: str, detection_reason: str,
                                    keyword: str = None, risk_subclass: str = None,
                                    similarity: float = None, matched_question: str = None,
                                    extra_info: Dict[str, Any] = None):
        if not self.blocked_query_storage:
            return

        try:
            embedding = await self._get_embedding(text)

            self.blocked_query_storage.add_blocked_query(
                query=text,
                detection_level=detection_level,
                detection_reason=detection_reason,
                embedding=embedding,
                similarity=similarity,
                matched_question=matched_question,
                risk_subclass=risk_subclass,
                extra_info=extra_info
            )

            if detection_level in ("C35", "C36", "C37", "C38", "C39") and similarity and similarity >= 0.9 and embedding:
                self.blocked_query_storage.add_to_question_bank_candidates(
                    query=text,
                    embedding=embedding,
                    detection_level=detection_level,
                    detection_reason=detection_reason,
                    similarity=similarity,
                    matched_question=matched_question,
                    risk_subclass=risk_subclass
                )
        except Exception as e:
            logger.warning(f"[内容检测] 存储拦截query失败: {e}")

    def check_blocklist(self, text: str) -> Optional[ViolationResult]:
        """C1: 通用违规词表检测"""
        if not self.blocklist:
            logger.debug("[内容检测-词表检测] 未加载词表，跳过检测")
            return None

        logger.info(f"[内容检测-词表检测] 开始检测文本: {text[:50]}...")
        text_lower = text.lower()
        for word in self.blocklist:
            if word.lower() in text_lower:
                logger.warning(f"[内容检测-词表检测] 检测到敏感词: {word}，文本: {text[:50]}...")
                return ViolationResult(
                    is_violation=True, c_code="C1",
                    reason=f"包含敏感词: {word}", keyword=word
                )

        logger.info(f"[内容检测-词表检测] 文本通过检测: {text[:50]}...")
        return None

    def check_category_keywords(self, text: str) -> Optional[ViolationResult]:
        """C2-C7: 7类关键词检测"""
        if not self.keyword_detector:
            return None

        logger.info(f"[内容检测-分类关键词] 开始检测文本: {text[:50]}...")
        keyword_results = self.keyword_detector.detect_with_details(text)

        detected_categories = []
        category_keywords = {}
        for category, detail in keyword_results.items():
            if category == 'overall':
                continue
            if detail.get('detected'):
                cat_code = self._category_to_c_code(category)
                detected_categories.append(cat_code)
                category_keywords[cat_code] = detail.get('keywords', [])
                logger.warning(f"[内容检测-分类关键词] 检测到{cat_code}({category})违规，关键词: {detail.get('keywords')}")

        if detected_categories:
            return ViolationResult(
                is_violation=True, c_code=detected_categories[0],
                reason=f"检测到违规类别: {', '.join(detected_categories)}",
                extra={'categories': detected_categories, 'category_keywords': category_keywords}
            )

        logger.info(f"[内容检测-分类关键词] 文本通过检测: {text[:50]}...")
        return None

    def _category_to_c_code(self, category: str) -> str:
        mapping = {
            'political': 'C2', 'violence': 'C3', 'pornography': 'C4',
            'gambling': 'C5', 'drug': 'C6', 'hate': 'C7', 'fake': 'C7'
        }
        return mapping.get(category, 'C2')

    def check_excel_parallel(self, text: str, use_segmentation: bool = False) -> Optional[ViolationResult]:
        """C8-C34: Excel词表检测"""
        if not self.parallel_detector:
            return None

        logger.info(f"[内容检测-Excel并行] 开始检测文本: {text[:50]}...")

        try:
            if use_segmentation:
                result = self.parallel_detector.detect_parallel_with_segmentation(text)
            else:
                result = self.parallel_detector.detect_parallel(text)

            if result.is_violation:
                logger.warning(f"[内容检测-Excel并行] 检测到违规: {result.keyword}, C码: {result.c_code}, 风险子类: {result.risk_subclass}")
                return ViolationResult(
                    is_violation=True, c_code=result.c_code,
                    reason=f"Excel检测到违规: {result.keyword} ({result.risk_subclass})",
                    keyword=result.keyword, risk_subclass=result.risk_subclass
                )

            logger.info(f"[内容检测-Excel并行] 文本通过检测: {text[:50]}...")
            return None

        except Exception as e:
            logger.warning(f"[内容检测-Excel并行] 检测失败: {e}")
            return None

    def check_excel_parallel_dual(self, text: str) -> Optional[ViolationResult]:
        """C8-C34: Excel词表检测+分词辅助"""
        if not self.parallel_detector:
            return None

        logger.info(f"[内容检测-Excel双重并行] 开始检测文本: {text[:50]}...")

        try:
            result = self.parallel_detector.detect_parallel_with_segmentation(text)

            if result.is_violation:
                logger.warning(f"[内容检测-Excel双重并行] 检测到违规: {result.keyword}, C码: {result.c_code}, 风险子类: {result.risk_subclass}")
                return ViolationResult(
                    is_violation=True, c_code=result.c_code,
                    reason=f"Excel检测到违规: {result.keyword} ({result.risk_subclass})",
                    keyword=result.keyword, risk_subclass=result.risk_subclass
                )

            logger.info(f"[内容检测-Excel双重并行] 文本通过检测: {text[:50]}...")
            return None

        except Exception as e:
            logger.warning(f"[内容检测-Excel双重并行] 检测失败: {e}")
            return None

    def check_excel_parallel_direct(self, text: str) -> Optional[ViolationResult]:
        """C8-C34: Excel词表检测"""
        if not self.parallel_detector:
            return None

        logger.info(f"[内容检测-Excel直接匹配] 开始检测文本: {text[:50]}...")

        try:
            result = self.parallel_detector.detect_parallel(text)

            if result.is_violation:
                logger.warning(f"[内容检测-Excel直接匹配] 检测到违规: {result.keyword}, C码: {result.c_code}, 风险子类: {result.risk_subclass}")
                return ViolationResult(
                    is_violation=True, c_code=result.c_code,
                    reason=f"Excel检测到违规: {result.keyword} ({result.risk_subclass})",
                    keyword=result.keyword, risk_subclass=result.risk_subclass
                )

            logger.info(f"[内容检测-Excel直接匹配] 文本通过检测: {text[:50]}...")
            return None

        except Exception as e:
            logger.warning(f"[内容检测-Excel直接匹配] 检测失败: {e}")
            return None

    async def check_question_bank_semantic(self, text: str, c_code: str = None, threshold: float = None) -> Optional[ViolationResult]:
        """C35-C39: 题库匹配检测"""
        if threshold is None and c_code is not None:
            threshold = QUESTION_BANK_C_THRESHOLDS.get(c_code, 0.85)

        if not self.question_bank_detector:
            return None

        logger.info(f"[内容检测-题库匹配] 开始检测文本: {text[:50]}..., threshold={threshold}")

        try:
            result = await self.question_bank_detector.detect_semantic_violation(text, threshold)

            if result and result.get('is_violation'):
                logger.warning(f"[内容检测-题库匹配] 检测到语义违规: 相似度={result['similarity']:.3f}, 问题={result['matched_question'][:50]}...")
                return ViolationResult(
                    is_violation=True, c_code=result['c_code'],
                    reason=f"题库匹配检测到违规: {result['matched_question'][:50]}... (相似度: {result['similarity']:.3f})",
                    matched_question=result['matched_question'],
                    similarity=result['similarity'],
                    risk_subclass=result.get('risk_subclass', ''),
                    extra={'threshold': result.get('threshold')}
                )

            logger.info(f"[内容检测-题库匹配] 文本通过检测: {text[:50]}...")

        except Exception as e:
            logger.warning(f"[内容检测-题库匹配] 检测失败: {e}")

        return None

    async def check_public_api(self, text: str) -> Optional[ViolationResult]:
        """C40: 第三方API检测（预留）"""
        logger.info(f"[内容检测-公共API检测] 开始检测文本: {text[:50]}...")
        logger.info(f"[内容检测-公共API检测] 文本通过检测: {text[:50]}...")
        return None

    async def check_blocked_history(self, text: str, threshold: float = None) -> Optional[ViolationResult]:
        """C42: 历史违规库匹配检测"""
        if threshold is None:
            threshold = BLOCKED_HISTORY_THRESHOLD

        if not self.blocked_query_storage or not self.blocked_query_storage.blocked_queries:
            return None

        logger.info(f"[内容检测-历史违规库] 开始检测文本: {text[:50]}..., threshold={threshold}")

        try:
            embedding = await self._get_embedding(text)
            if not embedding:
                return None

            text_embedding = np.array(embedding)

            storage = get_embedding_storage()

            blocked_embeddings = {}
            for q in self.blocked_query_storage.blocked_queries:
                cached = storage.get_embedding(q.query)
                if cached:
                    blocked_embeddings[q.query] = (np.array(cached), q)

            if not blocked_embeddings:
                logger.info(f"[内容检测-历史违规库] 无可用embedding缓存，跳过检测")
                return None

            queries = list(blocked_embeddings.keys())
            emb_matrix = np.array([blocked_embeddings[q][0] for q in queries])
            similarities = np.dot(text_embedding, emb_matrix.T)

            max_idx = np.argmax(similarities)
            max_similarity = float(similarities[max_idx])
            best_query = queries[max_idx]
            best_meta = blocked_embeddings[best_query][1]

            if max_similarity >= threshold:
                logger.warning(f"[内容检测-历史违规库] 检测到违规: 相似度={max_similarity:.3f}, 匹配: {best_query[:50]}...")
                return ViolationResult(
                    is_violation=True, c_code="C42",
                    reason=f"历史违规库匹配: {best_query[:50]}... (相似度: {max_similarity:.3f})",
                    matched_question=best_query,
                    similarity=max_similarity,
                    extra={'original_level': best_meta.detection_level, 'threshold': threshold}
                )

            logger.info(f"[内容检测-历史违规库] 文本通过检测: {text[:50]}...")
            return None

        except Exception as e:
            logger.warning(f"[内容检测-历史违规库] 检测失败: {e}")
            return None

    async def check_llm_fast(self, text: str) -> Optional[ViolationResult]:
        """C41: 大模型检测-快速检测"""
        try:
            logger.info(f"[内容检测-LLM快速检测] 开始分析文本: {text[:50]}...")
            prompt = get_content_moderation_prompt(user_input=text)

            llm_request = LLMRequest(
                system_prompt=prompt["system_prompt"],
                user_prompt=prompt["user_prompt"],
                temperature=0.1,
                max_tokens=10,
                provider="aliyun",
                model="qwen-flash",
                source="content_moderation",
                enable_context_cache=True
            )

            result = await llm_client_singleton.call_llm(llm_request)

            if isinstance(result, dict):
                response_text = result.get("text", "").strip()
                if response_text == "1":
                    logger.info(f"[内容检测-LLM快速检测] 文本通过检测: {text[:50]}...")
                    return None
                elif response_text == "0":
                    logger.warning(f"[内容检测-LLM快速检测] 检测到违规内容: {text[:50]}...")
                    return ViolationResult(
                        is_violation=True, c_code="C41",
                        reason="大模型检测判定违规"
                    )

            logger.info(f"[内容检测-LLM快速检测] 文本通过检测 (无明确结果): {text[:50]}...")
            return None

        except Exception as e:
            logger.warning(f"[内容检测-LLM快速检测] 语义分析失败: {e}，文本: {text[:50]}...")
            return None

    async def check_llm_category(self, text: str) -> List[Dict[str, Any]]:
        """C41: 大模型检测-细粒度分类检测"""
        category_prompts = {
            'political': get_political_moderation_prompt,
            'violence': get_violence_moderation_prompt,
            'pornography': get_pornography_moderation_prompt,
            'gambling': get_gambling_moderation_prompt,
            'drug': get_drug_moderation_prompt,
            'hate': get_hate_moderation_prompt,
            'fake': get_fake_moderation_prompt,
        }

        async def check_single_category(category, prompt_func):
            try:
                prompt = prompt_func(user_input=text)
                llm_request = LLMRequest(
                    system_prompt=prompt["system_prompt"],
                    user_prompt=prompt["user_prompt"],
                    temperature=0.1,
                    max_tokens=10,
                    provider="aliyun",
                    model="qwen-flash",
                    source="content_moderation_category",
                    enable_context_cache=True
                )
                result = await llm_client_singleton.call_llm(llm_request)
                if isinstance(result, dict):
                    response_text = result.get("text", "").strip()
                    if response_text == "0":
                        return {'category': category, 'method': 'llm', 'confidence': LLM_DETECTION_THRESHOLD}
            except Exception as e:
                logger.warning(f"[内容检测-LLM分类] {category}检测失败: {e}")
            return None

        tasks = [check_single_category(cat, func) for cat, func in category_prompts.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        detected = []
        for r in results:
            if isinstance(r, dict):
                detected.append(r)

        if detected:
            logger.warning(f"[内容检测-LLM分类] 检测到违规类别: {[d['category'] for d in detected]}")

        return detected

    async def moderate(self, user_input: str, detailed: bool = False, use_excel_parallel: bool = True, use_segmentation: bool = False) -> ModerateResult:
        """
        综合内容拦截检查 - C1-C42 全部并行，任一命中即返回

        所有检测方法统一返回 ViolationResult，此处统一处理
        """
        logger.info(f"[内容检测-综合检测] 开始检测用户输入: {user_input[:50]}..., detailed={detailed}, use_excel_parallel={use_excel_parallel}")

        loop = asyncio.get_event_loop()

        def run_c1():
            return self.check_blocklist(user_input)

        def run_c2_c7():
            return self.check_category_keywords(user_input)

        def run_c8_c34():
            if use_excel_parallel:
                return self.check_excel_parallel_direct(user_input)
            return None

        with ThreadPoolExecutor(max_workers=3) as executor:
            task_c1 = loop.run_in_executor(executor, run_c1)
            task_c2_c7 = loop.run_in_executor(executor, run_c2_c7)
            task_c8_c34 = loop.run_in_executor(executor, run_c8_c34) if use_excel_parallel else None

            task_c35_c39 = asyncio.create_task(self.check_question_bank_semantic(user_input))
            task_c40 = asyncio.create_task(self.check_public_api(user_input))
            task_c42 = asyncio.create_task(self.check_blocked_history(user_input))
            task_c41 = asyncio.create_task(self.check_llm_fast(user_input))

            all_tasks = [task_c1, task_c2_c7, task_c8_c34, task_c35_c39, task_c40, task_c42, task_c41]
            if not use_excel_parallel:
                all_tasks.remove(task_c8_c34)

            remaining = set(all_tasks)

            while remaining:
                done, pending = await asyncio.wait(
                    remaining,
                    return_when=asyncio.FIRST_COMPLETED
                )

                for task in done:
                    try:
                        result = task.result()
                    except Exception:
                        continue

                    if not result or not isinstance(result, ViolationResult) or not result.is_violation:
                        continue

                    c_code = result.c_code
                    reason = result.reason

                    logger.warning(f"[内容检测-综合检测] {c_code} 检测发现违规: {reason}")

                    asyncio.create_task(self._store_blocked_query(
                        user_input, c_code, reason,
                        keyword=result.keyword,
                        risk_subclass=result.risk_subclass,
                        similarity=result.similarity,
                        matched_question=result.matched_question,
                        extra_info=result.extra
                    ))

                    for p in pending:
                        p.cancel()

                    if detailed and result.extra and result.extra.get('categories'):
                        return DetailedModerateResult(
                            blocked=True,
                            reason=reason,
                            level=c_code,
                            violation_categories=result.extra['categories'],
                            detection_details=[{'c_code': c_code, 'reason': reason, 'keyword': result.keyword, 'risk_subclass': result.risk_subclass}]
                        )

                    return ModerateResult(blocked=True, reason=reason, level=c_code)

                remaining = pending

        logger.info(f"[内容检测-综合检测] 文本通过所有检测: {user_input[:50]}...")
        return ModerateResult(blocked=False, level="pass")


content_moderation_service = ContentModerationService()
