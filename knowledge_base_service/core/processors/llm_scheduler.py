# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import asyncio
import os
from typing import List, Dict
from core.llm_client import LLMClient
import dotenv
import json

# 导入模块(移除行内导入)
from core.llm_prompts.generate_search_queries_prompt import get_generate_search_queries_prompt
from core.llm_prompts.extract_information_prompt import get_extract_information_prompt
from core.llm_prompts.extract_document_information_prompt import get_extract_document_information_prompt
from core.llm_prompts.extract_html_content_prompt import get_extract_html_content_prompt
from core.llm_prompts.content_verification_prompt import get_content_verification_prompt

# 导入logger
from utils.logger import get_logger

# 初始化日志记录器
logger = get_logger(__name__)

# Load environment variables
dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "LLM_API.env"))

class LLMScheduler:
    def __init__(self):
        # Initialize OpenAI client (using aliYun-compatible endpoint)
        api_key = os.getenv("ALIYUN_API_KEY", "sk-ea096597b73444198ba32d267f7d5fc2")
        api_base = os.getenv("ALIYUN_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
        
        self.client = LLMClient(
            api_key=api_key,
            base_url=api_base.replace("/chat/completions", ""),
            default_model=self.default_model
        )
        self.default_model = os.getenv("ALIYUN_DEFAULT_MODEL", "qwen-plus")
        
        # Define specialized models for different tasks
        self.task_models = {
            'general': os.getenv("ALIYUN_DEFAULT_MODEL", "qwen-plus"),  # Fast and efficient for general tasks
            'ocr': os.getenv("ALIYUN_OCR_MODEL", "qwen-vl-ocr"),  # Vision-language model for OCR tasks
            'research': os.getenv("ALIYUN_RESEARCH_MODEL", "qwen-plus"),  # Deep research model for complex analysis (fallback to plus if deep-research not available)
            'detailed': os.getenv("ALIYUN_DETAILED_MODEL", "qwen-plus"),  # More detailed responses
            'fast': os.getenv("ALIYUN_FAST_MODEL", "qwen-turbo"),  # Fast responses for quick tasks
        }
    
    def get_model_for_task(self, task_type: str = 'general'):
        """Get the appropriate model for a specific task type"""
        model = self.task_models.get(task_type, self.default_model)
        return model
    
    async def _validate_model(self, model: str) -> bool:
        """Validate if a model is supported by the API"""
        try:
            # Try a minimal request to check if the model is supported
            content = await self.client.chat(
                model=model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            # Check if it's a model not supported error
            if "model_not_supported" in str(e) or "Unsupported model" in str(e):
                return False
            return True  # If it's another type of error, assume model is valid
    
    async def get_valid_model_for_task(self, task_type: str = 'general'):
        """Get a valid model for a specific task type, with fallback if model is not supported"""
        primary_model = self.task_models.get(task_type, self.default_model)
        
        # Check if the primary model is supported
        if await self._validate_model(primary_model):
            return primary_model
        
        # If not supported, fall back to default model
        logger.warning(f"模型 {primary_model} 不受支持,回退到默认模型 {self.default_model}")
        return self.default_model
    
    async def generate_search_queries(self, topic: str, requirements: str, num_queries: int = 5) -> List[str]:
        """
        Generate search queries based on topic and requirements using LLM
        """
        
        # Get the prompt using the new Python module
        prompt = get_generate_search_queries_prompt(topic, requirements, num_queries)
        
        # Use research model for generating search queries as it requires deeper analysis
        model = await self.get_valid_model_for_task('research')
        
        try:
            content = await self.client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=32768
            )
            
            content = content.strip()
            
            # Parse the response to extract search queries
            
            # Simple parsing - in a real implementation, you'd want more robust JSON parsing
            try:
                # Try to parse as JSON first
                queries = json.loads(content)
                if isinstance(queries, list):
                    return queries[:num_queries]  # Limit to requested number of queries
            except json.JSONDecodeError:
                # If not valid JSON, try to extract as a list from text
                lines = content.split('\n')
                queries = []
                for line in lines:
                    # Look for numbered items or bullet points
                    clean_line = line.strip()
                    if clean_line.startswith(('"', "'")) and clean_line.endswith(('"', "'")):
                        queries.append(clean_line.strip('"\''))
                    elif clean_line.startswith(tuple(str(i) + '.' for i in range(1, num_queries + 1))):
                        # Extract text after the number
                        parts = clean_line.split('.', 1)
                        if len(parts) > 1:
                            query = parts[1].strip().strip('"\'')
                            queries.append(query)
                
                return queries[:num_queries]  # Limit to requested number of queries
            
        except Exception as e:
            logger.error(f"Error generating search queries: {str(e)}")
            # Fallback: return simple queries
            return [f"{topic} {requirements}", f"{topic} overview", f"{topic} details"][:num_queries]
    
    async def extract_information(self, content: str, topic: str, requirements: str) -> Dict:
        """
        Extract relevant information from content using LLM
        """
        
        # Get the prompt using the new Python module
        prompt = get_extract_information_prompt(topic, requirements, content)
        
        # Use detailed model for extracting information as it requires thorough analysis
        model = await self.get_valid_model_for_task('detailed')
        
        try:
            content = await self.client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            content_response = content.strip()
            
            try:
                result = json.loads(content_response)
                # Ensure result is a dictionary with proper structure
                if isinstance(result, dict):
                    return {
                        'content': result.get('content', ''),
                        'tags': result.get('tags', [])
                    }
                else:
                    # If result is not a dict, try to handle it as a list or other type
                    logger.warning(f"Warning: LLM returned unexpected type: {type(result)}, value: {result}")
                    return {
                        'content': str(result) if result is not None else '',
                        'tags': [topic]
                    }
            except json.JSONDecodeError:
                # Fallback: return the raw content
                logger.warning(f"Warning: Could not parse LLM response as JSON: {content_response[:200]}...")
                return {
                    'content': content_response,
                    'tags': [topic]
                }
                
        except Exception as e:
            logger.error(f"Error extracting information: {str(e)}")
            return {
                'content': content[:500],  # Return first 500 chars as fallback
                'tags': [topic]
            }
    
    async def extract_information_from_document(self, content: str, filename: str) -> Dict:
        """
        Extract key information from a document using LLM
        """
        
        # Get the prompt using the new Python module
        prompt = get_extract_document_information_prompt(filename, content)
        
        # Use detailed model for document analysis as it requires thorough understanding
        model = await self.get_valid_model_for_task('detailed')
        
        try:
            content = await self.client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            content_response = content.strip()
            
            try:
                result = json.loads(content_response)
                return {
                    'content': result.get('content', ''),
                    'tags': result.get('tags', [])
                }
            except json.JSONDecodeError:
                # Fallback: return the raw content
                return {
                    'content': content_response,
                    'tags': [filename.split('.')[0]]
                }
                
        except Exception as e:
            logger.error(f"Error extracting document information: {str(e)}")
            return {
                'content': content[:500],  # Return first 500 chars as fallback
                'tags': [filename.split('.')[0]]
            }
    
    async def extract_content_from_html(self, html_content: str, topic: str) -> Dict:
        """
        Extract meaningful content from HTML using LLM
        """
        
        # Get the prompt using the new Python module
        prompt = get_extract_html_content_prompt(html_content, topic)
        
        # Use detailed model for content extraction as it requires thorough understanding
        model = await self.get_valid_model_for_task('detailed')
        
        try:
            content = await self.client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            content_response = content.strip()
            
            try:
                result = json.loads(content_response)
                return {
                    'content': result.get('content', ''),
                    'tags': result.get('tags', [])
                }
            except json.JSONDecodeError:
                # Fallback: return the raw content
                return {
                    'content': content_response,
                    'tags': [topic]
                }
                
        except Exception as e:
            logger.error(f"Error extracting content from HTML: {str(e)}")
            return {
                'content': html_content[:500],  # Return first 500 chars as fallback
                'tags': [topic]
            }
    
    async def verify_content_quality(self, content: str, url: str) -> Dict:
        """
        Verify the quality of the extracted content using LLM
        """
        
        # Get the prompt using the new Python module
        prompt = get_content_verification_prompt(content, url)
        
        # Use general model for content verification
        model = await self.get_valid_model_for_task('general')
        
        try:
            content = await self.client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Low temperature for consistent evaluation
                max_tokens=500
            )
            
            content_response = content.strip()
            
            try:
                result = json.loads(content_response)
                return result
            except json.JSONDecodeError:
                # Fallback: return basic assessment
                return {
                    'is_valid': len(content.strip()) > 100,  # Basic check
                    'quality_score': 50 if len(content.strip()) > 100 else 20,
                    'issues': ['Could not parse LLM response'],
                    'suggestions': ['Retry with different approach']
                }
                
        except Exception as e:
            logger.error(f"Error verifying content quality: {str(e)}")
            return {
                'is_valid': len(content.strip()) > 100,  # Basic check
                'quality_score': 50 if len(content.strip()) > 100 else 20,
                'issues': [str(e)],
                'suggestions': ['Retry with different approach']
            }
    
    async def evaluate_search_results(self, query: str, search_results: List[Dict], target_count: int) -> Dict:
        """
        让LLM评估搜索结果的质量并决定下一步行动
        """
        # 准备搜索结果摘要
        NEWLINE = '\n'
        results_summary = []
        for i, result in enumerate(search_results[:5]):  # 只取前5个结果进行摘要
            results_summary.append(f"{i+1}. 标题: {result.get('title', '无标题')} - URL: {result.get('url', '无URL')}")
        
        prompt = f"""
        请评估以下搜索查询的结果质量,并提供建议:

        搜索查询: {query}
        目标结果数量: {target_count}
        实际结果数量: {len(search_results)}
        结果摘要:
        {NEWLINE.join(results_summary)}

        请按以下JSON格式回复:
        {{
          "summary": "简要总结搜索结果质量",
          "relevance_score": 数字评分(1-100),
          "next_action": "process_results|refine_query|broaden_query|change_approach",
          "refined_query": "如果需要精炼查询,则提供新查询",
          "broadened_query": "如果需要扩展查询,则提供新查询",
          "alternative_queries": ["如果需要改变方法,则提供替代查询列表"],
          "confidence_in_results": "high|medium|low"
        }}
        """
        
        model = await self.get_valid_model_for_task('balanced')
        
        try:
            content = await self.client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=500
            )
            
            content_response = content.strip()
            
            # 尝试解析JSON响应
            try:
                # 查找JSON部分
                json_start = content_response.find('{')
                json_end = content_response.rfind('}') + 1
                
                if json_start != -1 and json_end != 0:
                    json_str = content_response[json_start:json_end]
                    result = json.loads(json_str)
                    return result
                else:
                    # 如果找不到JSON,返回基本结构
                    return {
                        'summary': content_response[:100],
                        'relevance_score': 50,
                        'next_action': 'process_results',
                        'confidence_in_results': 'medium'
                    }
            except json.JSONDecodeError:
                logger.warning(f"Warning: Could not parse LLM response as JSON: {content_response[:200]}...")
                return {
                    'summary': content_response[:100],
                    'relevance_score': 50,
                    'next_action': 'process_results',
                    'confidence_in_results': 'medium'
                }
                
        except Exception as e:
            logger.error(f"Error evaluating search results: {str(e)}")
            return {
                'summary': '评估失败',
                'relevance_score': 30,
                'next_action': 'process_results',
                'confidence_in_results': 'low'
            }
    
    async def decide_next_search_action(self, initial_query: str, collected_results: List[Dict], target_count: int, search_history: List[Dict]) -> Dict:
        """
        让LLM决定是否继续搜索以及如何搜索
        """
        results_info = f"已收集 {len(collected_results)} 个结果,目标 {target_count} 个"
        
        if search_history:
            history_info = f"已进行 {len(search_history)} 次搜索,最近一次找到 {search_history[-1]['results_count']} 个结果"
        else:
            history_info = "首次搜索"
        
        prompt = f"""
        请根据搜索进度决定下一步行动:

        初始查询: {initial_query}
        当前状态: {results_info}
        搜索历史: {history_info}
        
        已收集结果示例(前3个):
        {chr(10).join([f"- {r.get('title', '')[:50]}..." for r in collected_results[:3]])}

        请按以下JSON格式回复:
        {{
          "continue_search": true/false,
          "reason": "继续或停止的原因",
          "new_queries": ["如果继续搜索,则提供新查询列表"],
          "search_strategy": "broaden|narrow|diversify|deepen"
        }}
        """
        
        model = await self.get_valid_model_for_task('balanced')
        
        try:
            content = await self.client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=400
            )
            
            content_response = content.strip()
            
            try:
                # 查找JSON部分
                json_start = content_response.find('{')
                json_end = content_response.rfind('}') + 1
                
                if json_start != -1 and json_end != 0:
                    json_str = content_response[json_start:json_end]
                    result = json.loads(json_str)
                    return result
                else:
                    # 如果找不到JSON,返回基本结构
                    return {
                        'continue_search': len(collected_results) < target_count,
                        'reason': '基于结果数量决定',
                        'search_strategy': 'broaden'
                    }
            except json.JSONDecodeError:
                logger.warning(f"Warning: Could not parse LLM response as JSON: {content_response[:200]}...")
                return {
                    'continue_search': len(collected_results) < target_count,
                    'reason': '基于结果数量决定',
                    'search_strategy': 'broaden'
                }
                
        except Exception as e:
            logger.error(f"Error deciding next search action: {str(e)}")
            return {
                'continue_search': len(collected_results) < target_count,
                'reason': '默认继续直到达到目标数量',
                'search_strategy': 'broaden'
            }
    
    async def verify_content_quality(self, content: str, url: str = "", original_query: str = "") -> Dict:
        """
        验证内容质量及与原始查询的相关性
        """
        prompt = f"""
        请评估以下内容的质量和与原始查询的相关性:

        原始查询: {original_query}
        来源URL: {url}
        内容长度: {len(content)} 字符
        内容预览: {content[:500]}...

        请按以下JSON格式回复:
        {{
          "is_valid": true/false,
          "is_relevant": true/false,
          "quality_score": 数字评分(1-100),
          "relevance_score": 数字评分(1-100),
          "summary": "内容摘要",
          "key_points": ["关键点列表"],
          "issues": ["质量问题列表"],
          "suggestions": ["改进建议列表"]
        }}
        """
        
        model = await self.get_valid_model_for_task('detailed')
        
        try:
            content = await self.client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=600
            )
            
            content_response = content.strip()
            
            try:
                # 查找JSON部分
                json_start = content_response.find('{')
                json_end = content_response.rfind('}') + 1
                
                if json_start != -1 and json_end != 0:
                    json_str = content_response[json_start:json_end]
                    result = json.loads(json_str)
                    return result
                else:
                    # 如果找不到JSON,返回基本结构
                    return {
                        'is_valid': len(content.strip()) > 50,
                        'is_relevant': True,
                        'quality_score': 60 if len(content.strip()) > 100 else 30,
                        'relevance_score': 70,
                        'summary': content[:100] + "..." if len(content) > 100 else content
                    }
            except json.JSONDecodeError:
                logger.warning(f"Warning: Could not parse LLM response as JSON: {content_response[:200]}...")
                return {
                    'is_valid': len(content.strip()) > 50,
                    'is_relevant': True,
                    'quality_score': 60 if len(content.strip()) > 100 else 30,
                    'relevance_score': 70,
                    'summary': content[:100] + "..." if len(content) > 100 else content
                }
                
        except Exception as e:
            logger.error(f"Error verifying content quality: {str(e)}")
            return {
                'is_valid': len(content.strip()) > 50,
                'is_relevant': True,
                'quality_score': 60 if len(content.strip()) > 100 else 30,
                'relevance_score': 70,
                'summary': content[:100] + "..." if len(content) > 100 else content
            }