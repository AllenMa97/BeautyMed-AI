"""
医美术语智能查询构建器
解决"不知道搜哪些字段"的问题
"""
from typing import List, Dict, Optional
from knowledge_base_service.utils.logger import get_logger
from knowledge_base_service.core.processors.llm_scheduler import LLMScheduler

logger = get_logger(__name__)


class MedicalAestheticsQueryBuilder:
    """
    医美术语智能查询构建器
    
    功能：
    1. 医美术语中英文映射
    2. 自动生成多维度搜索查询
    3. 支持学术文献和新闻动态两种场景
    """
    
    MEDICAL_AESTHETICS_TERMS = {
        "抗衰": {
            "en": ["anti-aging", "skin aging", "photoaging", "senescence", "longevity"],
            "related": ["胶原蛋白", "弹性蛋白", "皱纹", "光老化"],
            "mechanisms": ["oxidative stress", "telomere", "mitochondrial dysfunction"],
            "treatments": ["retinol", "peptide", "growth factor", "stem cell therapy"],
        },
        "玻尿酸": {
            "en": ["hyaluronic acid", "HA", "hyaluronan"],
            "related": ["透明质酸", "填充剂", "保湿"],
            "mechanisms": ["extracellular matrix", "water binding", "viscoelasticity"],
            "treatments": ["dermal filler", "cross-linked HA", "injection technique"],
        },
        "肉毒素": {
            "en": ["botulinum toxin", "Botox", "BTX", "onabotulinumtoxinA"],
            "related": ["除皱", "瘦脸", "动态纹"],
            "mechanisms": ["acetylcholine release", "neuromuscular junction", "muscle paralysis"],
            "treatments": ["intramuscular injection", "cosmetic use", "therapeutic use"],
        },
        "激光": {
            "en": ["laser therapy", "laser resurfacing", "fractional laser", "CO2 laser"],
            "related": ["光子嫩肤", "点阵激光", "祛斑"],
            "mechanisms": ["selective photothermolysis", "thermal damage", "collagen remodeling"],
            "treatments": ["ablative laser", "non-ablative laser", "IPL"],
        },
        "射频": {
            "en": ["radiofrequency", "RF therapy", "thermal therapy"],
            "related": ["热玛吉", "紧致", "提拉"],
            "mechanisms": ["thermal injury", "collagen contraction", "neocollagenesis"],
            "treatments": ["monopolar RF", "bipolar RF", "fractional RF"],
        },
        "超声": {
            "en": ["ultrasound therapy", "HIFU", "high-intensity focused ultrasound"],
            "related": ["超声刀", "提拉", "紧致"],
            "mechanisms": ["thermal coagulation", "SMAS layer", "mechanical effect"],
            "treatments": ["micro-focused ultrasound", "ultrasound imaging"],
        },
        "美白": {
            "en": ["skin whitening", "skin lightening", "hyperpigmentation", "melasma"],
            "related": ["淡斑", "提亮", "色素沉着"],
            "mechanisms": ["melanin synthesis", "tyrosinase inhibition", "melanosome transfer"],
            "treatments": ["hydroquinone", "arbutin", "vitamin C", "niacinamide", "laser toning"],
        },
        "祛痘": {
            "en": ["acne treatment", "acne vulgaris", "comedone", "pimple"],
            "related": ["痤疮", "粉刺", "痘痘肌"],
            "mechanisms": ["sebum production", "P. acnes", "follicular hyperkeratinization", "inflammation"],
            "treatments": ["isotretinoin", "benzoyl peroxide", "antibiotics", "chemical peel", "photodynamic therapy"],
        },
        "敏感肌": {
            "en": ["sensitive skin", "skin barrier", "irritant contact dermatitis"],
            "related": ["皮肤屏障", "红血丝", "过敏"],
            "mechanisms": ["skin barrier dysfunction", "neurogenic inflammation", "immune response"],
            "treatments": ["barrier repair", "anti-inflammatory", "gentle skincare"],
        },
        "毛孔": {
            "en": ["pore size", "enlarged pores", "sebaceous gland"],
            "related": ["毛孔粗大", "控油", "黑头"],
            "mechanisms": ["sebum secretion", "follicular size", "skin elasticity"],
            "treatments": ["chemical peel", "laser treatment", "topical retinoids"],
        },
        "眼周": {
            "en": ["periorbital area", "eye bag", "dark circle", "crow's feet"],
            "related": ["眼袋", "黑眼圈", "鱼尾纹"],
            "mechanisms": ["fat herniation", "vascular congestion", "skin laxity"],
            "treatments": ["blepharoplasty", "filler injection", "laser resurfacing"],
        },
        "脂肪": {
            "en": ["lipolysis", "fat reduction", "adipose tissue", "body contouring"],
            "related": ["溶脂", "瘦身", "塑形"],
            "mechanisms": ["adipocyte apoptosis", "lipid metabolism", "thermal injury"],
            "treatments": ["cryolipolysis", "laser lipolysis", "injection lipolysis", "liposuction"],
        },
        "疤痕": {
            "en": ["scar treatment", "keloid", "hypertrophic scar", "atrophic scar"],
            "related": ["痘坑", "疤痕修复", "增生性疤痕"],
            "mechanisms": ["wound healing", "collagen deposition", "fibroblast activity"],
            "treatments": ["laser resurfacing", "microneedling", "silicone gel", "corticosteroid injection"],
        },
        "毛发": {
            "en": ["hair loss", "alopecia", "hair transplantation", "hair growth"],
            "related": ["脱发", "植发", "生发"],
            "mechanisms": ["hair follicle cycle", "androgenetic alopecia", "miniaturization"],
            "treatments": ["minoxidil", "finasteride", "PRP injection", "FUE", "FUT"],
        },
        "私密": {
            "en": ["vaginal rejuvenation", "labiaplasty", "vaginoplasty"],
            "related": ["私密整形", "阴道紧缩"],
            "mechanisms": ["tissue remodeling", "collagen synthesis"],
            "treatments": ["laser vaginal rejuvenation", "RF treatment", "surgical procedure"],
        },
    }
    
    TREATMENT_CATEGORIES = {
        "注射类": ["botulinum toxin", "dermal filler", "PRP", "mesotherapy", "biorevitalization"],
        "光电类": ["laser", "IPL", "radiofrequency", "ultrasound", "LED therapy"],
        "手术类": ["blepharoplasty", "rhinoplasty", "facelift", "liposuction", "hair transplantation"],
        "护肤类": ["chemical peel", "microneedling", "topical treatment", "skincare routine"],
    }
    
    SKIN_CONCERNS = {
        "衰老": ["wrinkle", "sagging", "volume loss", "skin laxity"],
        "色素": ["hyperpigmentation", "melasma", "age spot", "freckle"],
        "痤疮": ["acne", "comedone", "cyst", "scar"],
        "敏感": ["sensitive skin", "rosacea", "erythema", "irritation"],
        "肤质": ["pore", "texture", "oiliness", "dryness"],
    }

    def __init__(self):
        self.llm = LLMScheduler()
    
    async def build_academic_queries(
        self, 
        topic: str, 
        max_queries: int = 15
    ) -> List[Dict[str, str]]:
        """
        为学术文献搜索构建查询
        
        返回格式: [{"query": "...", "type": "...", "language": "..."}]
        """
        queries = []
        
        term_info = self._find_term_info(topic)
        
        if term_info:
            en_terms = term_info.get("en", [])
            for term in en_terms[:3]:
                queries.append({
                    "query": term,
                    "type": "primary_term",
                    "language": "en"
                })
            
            mechanisms = term_info.get("mechanisms", [])
            for mech in mechanisms[:2]:
                queries.append({
                    "query": f"{mech} {en_terms[0] if en_terms else topic}",
                    "type": "mechanism",
                    "language": "en"
                })
            
            treatments = term_info.get("treatments", [])
            for treat in treatments[:2]:
                queries.append({
                    "query": f"{treat} clinical study",
                    "type": "treatment",
                    "language": "en"
                })
            
            related = term_info.get("related", [])
            for rel in related[:2]:
                queries.append({
                    "query": rel,
                    "type": "related_term",
                    "language": "zh"
                })
        
        if len(queries) < max_queries:
            llm_queries = await self._generate_llm_queries(topic, "academic", max_queries - len(queries))
            queries.extend(llm_queries)
        
        return queries[:max_queries]
    
    async def build_news_queries(
        self, 
        topic: str, 
        max_queries: int = 10
    ) -> List[Dict[str, str]]:
        """
        为新闻/动态搜索构建查询
        
        返回格式: [{"query": "...", "type": "...", "language": "..."}]
        """
        queries = []
        
        term_info = self._find_term_info(topic)
        
        if term_info:
            en_terms = term_info.get("en", [])
            zh_related = term_info.get("related", [])
            
            for term in en_terms[:2]:
                queries.append({
                    "query": f"{term} news 2024 2025",
                    "type": "news",
                    "language": "en"
                })
                queries.append({
                    "query": f"{term} latest development",
                    "type": "development",
                    "language": "en"
                })
            
            for rel in zh_related[:2]:
                queries.append({
                    "query": f"{rel} 最新动态",
                    "type": "news",
                    "language": "zh"
                })
                queries.append({
                    "query": f"{rel} 行业资讯",
                    "type": "industry",
                    "language": "zh"
                })
        
        if len(queries) < max_queries:
            llm_queries = await self._generate_llm_queries(topic, "news", max_queries - len(queries))
            queries.extend(llm_queries)
        
        return queries[:max_queries]
    
    def _find_term_info(self, topic: str) -> Optional[Dict]:
        """查找术语信息"""
        for key, info in self.MEDICAL_AESTHETICS_TERMS.items():
            if key in topic or topic in key:
                return info
            for related in info.get("related", []):
                if related in topic or topic in related:
                    return info
        return None
    
    async def _generate_llm_queries(
        self, 
        topic: str, 
        query_type: str, 
        count: int
    ) -> List[Dict[str, str]]:
        """使用LLM生成查询"""
        try:
            if query_type == "academic":
                prompt = f"""为医美主题 '{topic}' 生成 {count} 个学术文献搜索关键词。

要求：
1. 关键词要精确，适合在PubMed、arXiv等学术数据库搜索
2. 包含英文医学术语
3. 涵盖：机制、治疗方法、临床研究、副作用等维度
4. 每个关键词一行，格式：关键词|类型|语言

示例输出：
skin aging mechanism|mechanism|en
retinol clinical trial|treatment|en
抗衰老研究|research|zh"""
            else:
                prompt = f"""为医美主题 '{topic}' 生成 {count} 个新闻/动态搜索关键词。

要求：
1. 关键词要适合搜索引擎搜索最新资讯
2. 包含中英文
3. 涵盖：行业动态、新技术、产品发布、政策法规等
4. 每个关键词一行，格式：关键词|类型|语言

示例输出：
玻尿酸填充 最新技术|technology|zh
hyaluronic acid filler news|news|en
医美行业政策|policy|zh"""
            
            model = await self.llm.get_valid_model_for_task('fast')
            response = await self.llm.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            queries = []
            
            for line in content.split('\n'):
                line = line.strip()
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        queries.append({
                            "query": parts[0].strip(),
                            "type": parts[1].strip(),
                            "language": parts[2].strip()
                        })
            
            return queries
            
        except Exception as e:
            logger.error(f"LLM生成查询失败: {str(e)}")
            return []
    
    def get_all_primary_terms(self) -> List[str]:
        """获取所有主要术语"""
        return list(self.MEDICAL_AESTHETICS_TERMS.keys())
    
    def get_term_mapping(self, term: str) -> Optional[Dict]:
        """获取术语映射"""
        return self._find_term_info(term)
    
    def suggest_related_topics(self, topic: str) -> List[str]:
        """推荐相关主题"""
        suggestions = []
        
        for key, info in self.MEDICAL_AESTHETICS_TERMS.items():
            if key != topic:
                related = info.get("related", [])
                if any(r in topic or topic in r for r in related):
                    suggestions.append(key)
        
        return suggestions[:5]
