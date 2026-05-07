# Developer: 椹但路椹櫤鍕?
# Position: 澶фā鍨嬬畻娉曞伐绋嬪笀
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
鍐呭鐩镐技鎬ц瘎浼版彁绀烘ā鏉?
"""

CONTENT_SIMILARITY_PROMPT = """
璇疯瘎浼颁互涓嬩袱娈靛唴瀹瑰湪{layer}灞傜殑鐩镐技鎬э紙0-100鍒嗭級锛?

宸叉湁鍐呭: {existing_content}
鏂板唴瀹? {new_content}

璇锋寜浠ヤ笅JSON鏍煎紡鍥炲:
{{
  "similarity_score": 0-100涔嬮棿鐨勬暟瀛?
}}
"""


def get_content_similarity_prompt(existing_content: str, new_content: str, layer: str = "specific"):
    """
    鑾峰彇鍐呭鐩镐技鎬ц瘎浼扮殑鎻愮ず
    """
    return CONTENT_SIMILARITY_PROMPT.format(
        existing_content=existing_content[:500],
        new_content=new_content[:500],
        layer=layer
    )
