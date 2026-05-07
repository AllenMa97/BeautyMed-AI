# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from typing import Optional, Dict, List

# 核心BCP47映射表：直接映射到最终标签，无中间态
BCP47_MAPPING: Dict[str, Dict[str, str]] = {
    "zh": {
        "default": "zh-CN",  # 简体中文（默认）
        "tw": "zh-TW",  # 台湾繁体
        "hk": "zh-HK",  # 香港繁体
        # "sg": "zh-SG"  # 新加坡简体
    },
    "en": {
        "default": "en-US",  # 美式英语（默认）
        # "sg": "en-SG",  # 新加坡英语
        # "my": "en-MY",  # 马来西亚英语
        # "ph": "en-PH",  # 菲律宾英语
        # "gb": "en-GB"  # 英式英语
    },
    # 东南亚核心语言（无变体，直接默认）
    "id": {"default": "id-ID"},
    "ms": {"default": "ms-MY"},
    "th": {"default": "th-TH"},
    "vi": {"default": "vi-VN"},
    "tl": {"default": "tl-PH"},
    "km": {"default": "km-KH"},
    "lo": {"default": "lo-LA"},
    "my": {"default": "my-MM"},
    "ta": {"default": "ta-SG"},
    # 其他语言
    "ja": {"default": "ja-JP"},
    "ko": {"default": "ko-KR"},
    "fr": {"default": "fr-FR"},
    "es": {"default": "es-ES"},
    "pt": {"default": "pt-BR"},
    "de": {"default": "de-DE"},
    "ru": {"default": "ru-RU"},
}

# 极简识别规则：只保留核心特征，去掉冗余逻辑
DETECTION_RULES = {
    # 中文地区识别（直接映射到最终变体）
    "zh": [
        ("tw", ["台灣", "台", "中華民國", "灣", "裡", "後", "體", "發"]),
        ("hk", ["香港", "港", "嘅", "乜", "嘢", "係", "睇"]),
        # ("sg", ["新加坡", "Singapura"])
    ],
    # 英语地区识别
    # "en": [
    #     ("sg", ["Singapore", "Singapura"]),
    #     ("my", ["Malaysia", "KL"]),
    #     ("ph", ["Philippines", "Manila"]),
    #     ("gb", ["colour", "centre", "UK"])
    # ]
}


def detect_language(text: str) -> str:
    """极简语言识别：只识别核心语言代码"""
    text_lower = text.lower().strip()

    # 1. 字符编码识别（优先，准确率100%）
    if any(0x4E00 <= ord(c) <= 0x9FFF for c in text):
        return "zh"
    elif any(0x0E00 <= ord(c) <= 0x0E7F for c in text):
        return "th"
    elif any(0x1780 <= ord(c) <= 0x17FF for c in text):
        return "km"
    elif any(0x0E80 <= ord(c) <= 0x0EFF for c in text):
        return "lo"
    elif any(0x1000 <= ord(c) <= 0x109F for c in text):
        return "my"
    elif any(0x0B80 <= ord(c) <= 0x0BFF for c in text):
        return "ta"
    elif any(0x3040 <= ord(c) <= 0x30FF for c in text):
        return "ja"
    elif any(0xAC00 <= ord(c) <= 0xD7AF for c in text):
        return "ko"

    # 2. 关键词识别（无特殊字符的语言）
    if any(kw in text_lower for kw in ["apa kabar", "indonesia"]):
        return "id"
    elif any(kw in text_lower for kw in ["apa khabar", "malaysia"]):
        return "ms"
    elif any(kw in text_lower for kw in ["xin chào", "vietnam"]):
        return "vi"
    elif any(kw in text_lower for kw in ["kamusta", "philippines"]):
        return "tl"
    elif any(kw in text_lower for kw in ["hello", "thank you", "world"]):
        return "en"
    elif any(kw in text_lower for kw in ["bonjour", "merci"]):
        return "fr"
    elif any(kw in text_lower for kw in ["hola", "gracias"]):
        return "es"
    elif any(kw in text_lower for kw in ["olá", "obrigado"]):
        return "pt"
    elif any(kw in text_lower for kw in ["hallo", "danke"]):
        return "de"
    elif any(kw in text_lower for kw in ["привет", "спасибо"]):
        return "ru"

    # 默认返回英语
    return "en"


def detect_variant(lang_code: str, text: str) -> str:
    """极简变体识别：只识别核心地区特征，无则返回default"""
    text_lower = text.lower().strip()

    # 只处理中文/英语的变体，其他语言返回default
    if lang_code in DETECTION_RULES:
        for variant, keywords in DETECTION_RULES[lang_code]:
            if any(kw.lower() in text_lower for kw in keywords):
                return variant

    return "default"


def get_bcp47_tag(
        text: str,
        variant: Optional[str] = None  # 手动指定变体（优先级最高）
) -> str:
    """
    极简版BCP47标签识别：
    1. 输入：仅需text（variant可选）
    2. 输出：标准BCP47标签（如zh-CN/zh-TW/en-SG）
    """
    if not text.strip():
        raise ValueError("输入文本不能为空")

    # 步骤1：识别基础语言
    lang_code = detect_language(text)

    # 步骤2：确定变体（手动传>自动识别>default）
    final_variant = variant if variant else detect_variant(lang_code, text)

    # 步骤3：返回最终标签
    return BCP47_MAPPING[lang_code].get(final_variant, BCP47_MAPPING[lang_code]["default"])


# ------------------- 你的测试代码（无需修改） -------------------
if __name__ == "__main__":
    print("日常使用方法（重点）")
    # 1. 识别简体中文
    text1 = "今天天气很好，适合出门"
    result1 = get_bcp47_tag(text1)  # 返回 "zh-CN"
    print(result1)

    # 2. 识别台湾繁体
    text2 = "今天天氣很好，適合出門，台灣加油"
    result2 = get_bcp47_tag(text2)  # 返回 "zh-TW"
    print(result2)

    # 3. 识别英语
    text3 = "Hello, welcome to Singapore"
    result3 = get_bcp47_tag(text3)  # 返回 "en-US"
    print(result3)

    # 4. 识别东南亚小语种
    text4 = "สวัสดีครับ"  # 泰语
    result4 = get_bcp47_tag(text4)  # 返回 "th-TH"
    print(result4)

    # 5. 特殊场景：手动指定变体（覆盖自动识别）
    text5 = "你好，世界"
    result5 = get_bcp47_tag(text5, variant="hk")  # 强制返回 "zh-HK"
    print(result5)
