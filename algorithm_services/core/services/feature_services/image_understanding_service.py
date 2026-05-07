# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.api.schemas.feature_schemas.image_understanding_schemas import (
    ImageUnderstandingRequest, ImageUnderstandingResponse, ImageUnderstandingResponseData
)
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

class ImageUnderstandingService:
    """图片理解服务 - 预留扩展"""

    async def understand(self, request: ImageUnderstandingRequest) -> ImageUnderstandingResponse:
        logger.info(f"图片理解服务收到请求")

        response_data = ImageUnderstandingResponseData(
            description="图片理解服务待实现",
            extracted_info={},
            related_topics=[]
        )

        return ImageUnderstandingResponse(data=response_data)

image_understanding_service = ImageUnderstandingService()
