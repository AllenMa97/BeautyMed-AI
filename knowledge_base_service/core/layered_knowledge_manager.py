# Developer: 马赫·马智明
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import asyncio
import hashlib
from typing import List, Dict, Optional, Literal
from pathlib import Path
from datetime import datetime
import re

from utils.logger import get_logger
from core.processors.llm_scheduler import LLMScheduler
from core.llm_utils import LLMUtils
from core.llm_prompts import (
    get_knowledge_classification_prompt,
    get_content_similarity_prompt,
    get_credibility_evaluation_prompt
)

logger = get_logger(__name__)

KnowledgeLayer = Literal["domain_background", "specific", "associative"]


class LayeredKnowledgeManager:
    """
    分层知识库管理器
    支持领域背景知识、具体知识和关联知识三个层级
    使用Markdown文件存储
    """

    def __init__(self, storage_path: str = "layered_knowledge_base"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)

        self.domain_bg_path = self.storage_path / "domain_background"
        self.specific_path = self.storage_path / "specific"
        self.associative_path = self.storage_path / "associative"

        for path in [self.domain_bg_path, self.specific_path, self.associative_path]:
            path.mkdir(exist_ok=True)

        self.llm = LLMScheduler()
        self.llm_utils = LLMUtils()

    def _calculate_content_hash(self, content: str) -> str:
        """计算内容哈希值,用于去重"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    async def _classify_knowledge_layer(self, content: str, query: str = "") -> KnowledgeLayer:
        """
        使用LLM对知识进行分层分类
        """
        try:
            prompt = get_knowledge_classification_prompt(content, query)
            model = await self.llm.get_valid_model_for_task('balanced')
            content_response = await self.llm.client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )

            result = self.llm_utils.parse_json_response(content_response)

            layer = result.get('layer', 'specific')
            if layer in ['domain_background', 'specific', 'associative']:
                return layer
            else:
                return 'specific'

        except Exception as e:
            logger.error(f"知识分层时出错: {e}")
            return 'specific'

    async def _check_duplicate(self, content: str, layer: KnowledgeLayer, similarity_threshold: float = 0.8) -> bool:
        """
        检查内容在指定层级中是否重复
        """
        content_hash = self._calculate_content_hash(content)
        layer_path = getattr(self, f'{layer.replace("-", "_")}_path')

        for md_file in layer_path.glob("*.md"):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()

                content_match = re.search(r'## 内容\s*\n(.+?)(?=\n## |\Z)', file_content, re.DOTALL)
                if content_match:
                    existing_content = content_match.group(1).strip()
                    existing_hash = self._calculate_content_hash(existing_content)

                    if existing_hash == content_hash:
                        logger.info(f"在{layer}层发现重复内容")
                        return True

            except Exception as e:
                logger.error(f"读取文件 {md_file} 时出错: {e}")

        recent_entries = self.get_recent_entries(layer, limit=5)

        for entry in recent_entries:
            existing_content = entry.get('content', '')

            try:
                prompt = get_content_similarity_prompt(existing_content, content, layer)
                model = await self.llm.get_valid_model_for_task('balanced')
                content_response = await self.llm.client.chat(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=100
                )

                result = self.llm_utils.parse_json_response(content_response)
                similarity_score = result.get('similarity_score', 0)

                if similarity_score >= similarity_threshold * 100:
                    logger.info(f"在{layer}层发现相似内容,相似度: {similarity_score}%")
                    return True

            except Exception as e:
                logger.error(f"评估内容相似性时出错: {e}")

        return False

    async def _validate_content_credibility(self, content: str, source_url: str = "", layer: KnowledgeLayer = "specific") -> Dict:
        """
        验证内容的可信度,不同层级有不同的评估标准
        """
        try:
            prompt = get_credibility_evaluation_prompt(content, source_url, layer)
            model = await self.llm.get_valid_model_for_task('detailed')
            content_response = await self.llm.client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=600
            )

            result = self.llm_utils.parse_json_response(content_response)

            if result:
                return result
            else:
                return self.llm_utils.create_default_credibility_score()

        except Exception as e:
            logger.error(f"验证内容可信度时出错: {e}")
            return self.llm_utils.create_error_credibility_score(str(e))

    async def add_knowledge(self, title: str, content: str, layer: Optional[KnowledgeLayer] = None,
                           source_url: str = "", query_used: str = "", tags: List[str] = None) -> bool:
        """
        添加知识到指定层级的Markdown文件
        """
        if layer is None:
            layer = await self._classify_knowledge_layer(content, query_used)

        logger.info(f"尝试添加知识到{layer}层: {title[:50]}...")

        if await self._check_duplicate(content, layer):
            logger.info(f"内容在{layer}层已存在或高度相似,跳过添加: {title[:50]}...")
            return False

        credibility_info = await self._validate_content_credibility(content, source_url, layer)

        min_score = 45 if layer == "associative" else 50
        if credibility_info.get('credibility_score', 0) < min_score:
            logger.warning(f"{layer}层内容可信度不足,跳过添加: {title[:50]}... 评分: {credibility_info.get('credibility_score', 0)}")
            return False

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{layer}_{timestamp}_{abs(hash(title)) % 10000}.md"

        layer_path = getattr(self, f'{layer.replace("-", "_")}_path')
        filepath = layer_path / filename

        if layer == "specific":
            md_content = f"""# {title}

**来源URL:** {source_url}
**标签:** {', '.join(tags or []) if tags else '无'}
**添加日期:** {datetime.now().isoformat()}

## 内容

{content}

---
"""
        else:
            md_content = f"""# {title}

**来源URL:** {source_url}
**标签:** {', '.join(tags or []) if tags else '无'}
**添加日期:** {datetime.now().isoformat()}
**质量评分:** {credibility_info.get('credibility_score', 0)}/100

## 内容

{content}

## 可信度评估

- 专业性: {credibility_info.get('professional_score', 0)}/100
- 权威性: {credibility_info.get('authority_score', 0)}/100
- 逻辑性: {credibility_info.get('logic_score', 0)}/100
- 时效性: {credibility_info.get('timeliness_score', 0)}/100
- 客观性: {credibility_info.get('objectivity_score', 0)}/100
- 适用性: {credibility_info.get('applicability_score', 0)}/100

---
"""

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md_content)

            logger.info(f"成功添加{layer}层知识到文件: {filename}, 评分: {credibility_info.get('credibility_score', 0)}")
            return True

        except Exception as e:
            logger.error(f"写入知识条目文件时出错: {e}")
            return False

    def get_entries_by_layer(self, layer: KnowledgeLayer, limit: int = 100) -> List[Dict]:
        """获取指定层级的知识条目"""
        layer_path = getattr(self, f'{layer.replace("-", "_")}_path')
        md_files = list(layer_path.glob("*.md"))

        md_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        results = []
        count = 0

        for md_file in md_files:
            if count >= limit:
                break

            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                entry = self._parse_markdown_content(content, str(md_file))
                if entry:
                    results.append(entry)
                    count += 1
            except Exception as e:
                logger.error(f"读取文件 {md_file} 时出错: {e}")

        return results

    def _parse_markdown_content(self, content: str, filepath: str) -> Dict:
        """解析Markdown文件内容为字典格式"""
        try:
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else "未知标题"

            source_match = re.search(r'\*\*来源URL:\*\*\s+(.+)$', content, re.MULTILINE)
            source_url = source_match.group(1) if source_match else ""

            tags_match = re.search(r'\*\*标签:\*\*\s+(.+)$', content, re.MULTILINE)
            tags_str = tags_match.group(1) if tags_match else ""
            tags = [tag.strip() for tag in tags_str.split(',')] if tags_str != '无' else []

            date_match = re.search(r'\*\*添加日期:\*\*\s+(.+)$', content, re.MULTILINE)
            added_date = date_match.group(1) if date_match else ""

            content_match = re.search(r'## 内容\s*\n(.+?)(?=\n## |\n---|\Z)', content, re.DOTALL)
            extracted_content = content_match.group(1).strip() if content_match else ""

            result = {
                'title': title,
                'content': extracted_content,
                'source_url': source_url,
                'tags': tags,
                'added_date': added_date,
                'filepath': filepath
            }

            score_match = re.search(r'\*\*质量评分:\*\*\s+([\d.]+)/100', content, re.MULTILINE)
            if score_match:
                result['quality_score'] = float(score_match.group(1))

            credibility_info = {}
            professional_match = re.search(r'- 专业性: ([\d.]+)', content)
            if professional_match:
                credibility_info['professional_score'] = float(professional_match.group(1))

            authority_match = re.search(r'- 权威性: ([\d.]+)', content)
            if authority_match:
                credibility_info['authority_score'] = float(authority_match.group(1))

            logic_match = re.search(r'- 逻辑性: ([\d.]+)', content)
            if logic_match:
                credibility_info['logic_score'] = float(logic_match.group(1))

            timeliness_match = re.search(r'- 时效性: ([\d.]+)', content)
            if timeliness_match:
                credibility_info['timeliness_score'] = float(timeliness_match.group(1))

            objectivity_match = re.search(r'- 客观性: ([\d.]+)', content)
            if objectivity_match:
                credibility_info['objectivity_score'] = float(objectivity_match.group(1))

            applicability_match = re.search(r'- 适用性: ([\d.]+)', content)
            if applicability_match:
                credibility_info['applicability_score'] = float(applicability_match.group(1))

            if credibility_info:
                result['credibility_info'] = credibility_info

            return result
        except Exception as e:
            logger.error(f"解析Markdown内容时出错: {e}")
            return None

    def get_recent_entries(self, layer: KnowledgeLayer, limit: int = 10) -> List[Dict]:
        """获取指定层级的最新知识条目"""
        layer_path = getattr(self, f'{layer.replace("-", "_")}_path')
        md_files = list(layer_path.glob("*.md"))

        md_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        results = []

        for md_file in md_files[:limit]:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                entry = self._parse_markdown_content(content, str(md_file))
                if entry:
                    results.append(entry)
            except Exception as e:
                logger.error(f"读取文件 {md_file} 时出错: {e}")

        return results

    def search_knowledge(self, query: str, layers: List[KnowledgeLayer] = None, limit: int = 20) -> List[Dict]:
        """在指定层级中搜索知识"""
        if layers is None:
            layers = ["specific", "domain_background", "associative"]

        results = []
        query_lower = query.lower()

        for layer in layers:
            entries = self.get_entries_by_layer(layer, limit=limit)

            for entry in entries:
                title = entry.get('title', '').lower()
                content = entry.get('content', '').lower()
                tags = ' '.join(entry.get('tags', [])).lower()

                if query_lower in title or query_lower in content or query_lower in tags:
                    results.append(entry)

        results.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
        return results[:limit]

    def get_statistics(self) -> Dict:
        """获取知识库统计信息"""
        stats = {
            'specific': len(list(self.specific_path.glob("*.md"))),
            'domain_background': len(list(self.domain_bg_path.glob("*.md"))),
            'associative': len(list(self.associative_path.glob("*.md"))),
            'total': 0
        }
        stats['total'] = stats['specific'] + stats['domain_background'] + stats['associative']
        return stats
