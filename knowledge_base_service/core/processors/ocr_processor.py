import asyncio
import base64
from typing import Dict
from openai import AsyncOpenAI
import os
import dotenv

# Load environment variables
dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "LLM_API.env"))

class OCRProcessor:
    def __init__(self):
        # Initialize OpenAI client (using aliYun-compatible endpoint)
        api_key = os.getenv("ALIYUN_API_KEY", "sk-614f2e32ce44483892c6fd2ce494d4ac")
        api_base = os.getenv("ALIYUN_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_base.replace("/chat/completions", "")  # Remove the endpoint part
        )
        self.ocr_model = os.getenv("ALIYUN_OCR_MODEL", "qwen-vl-ocr")
    
    async def ocr_from_image(self, image_path: str) -> str:
        """
        Perform OCR on an image using vision-language model
        """
        try:
            # Encode image to base64
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Create message with image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "请对该图像进行OCR识别，提取其中的文字内容。只需要返回识别出的文字，不要其他解释。"
                        }
                    ]
                }
            ]
            
            response = await self.client.chat.completions.create(
                model=self.ocr_model,
                messages=messages,
                temperature=0.1,
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error performing OCR: {str(e)}")
            # Fallback to traditional OCR
            return await self._fallback_ocr(image_path)
    
    async def _fallback_ocr(self, image_path: str) -> str:
        """
        Fallback OCR using traditional pytesseract if vision model fails
        """
        try:
            from PIL import Image
            import pytesseract
            
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')
            return text.strip()
        except Exception as e:
            print(f"Fallback OCR also failed: {str(e)}")
            return ""

# Global instance
ocr_processor = OCRProcessor()

async def perform_ocr(image_path: str) -> str:
    """
    Public function to perform OCR on an image
    """
    return await ocr_processor.ocr_from_image(image_path)