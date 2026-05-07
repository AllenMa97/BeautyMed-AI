# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from algorithm_services.api.schemas.feature_schemas.function_planner_schemas import FunctionPlannerRequest, FunctionPlannerResponse
from algorithm_services.core.services.feature_services.function_planner_service import FunctionPlannerService
from algorithm_services.core.services.feature_services.i18n_service import I18N_Get_BCP47_Tag

from algorithm_services.utils.i18n import get_bcp47_tag
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

# 规划器统一入口路由
main_router = APIRouter(
    prefix="/api/v1",
    tags=["功能规划器（Function Planner） - chabot统一入口"]
)

# 初始化规划器Service
planner_service = FunctionPlannerService()

@main_router.post("/entrance")
async def entrance(request: FunctionPlannerRequest):
    # 这段字符串会出现在Swagger页面里面的，会渲染成Markdown，有需要展示可以在这里补充
    """
    # Lansee Chatbot统一入口API
    ## 入参简单说明（可以翻到页面最底下的Schemas框，找"FunctionPlannerRequest"）：
    ``` python
    {

        "session_id":"996", # 代表会话编号的字符串，由后端传入，可为空但是不建议

        "user_id":"996", # 代表用户编号的字符串，由后端传入，可为空但是不建议

        "lang": "zh-CN", # 代表语言类型的字符串，默认 "zh-CN"，可选 zh-CN| en-US，

        "stream_flag": true, # 代表是否进行流式返回的布尔值， 默认true，可选false

        "user_input": "XXXX" # 代表用户输入的字符串， 默认为空串''

        "context": "" # 代表对话上下文的字符串，默认为空串

    }
    ```

    注意，context的原始对象格式如下：
    ``` python
    [

        {"user": "输入1", "response": "回答1"},

        {"user": "输入2", "response": "回答2"},

        ...

    ]
    ```
    请把上述内容转成字符串（主要是引号,换行符等符号）再填入。

    输入1存放的是上一次的 user_input ； 回答1存放的是上一次的 final_result； 以此类推

    ---

    ## 出参状态码说明（code字段）：
    流式响应（SSE）模式下，会返回多种状态码的消息：

    | 状态码 | 含义 | 说明 |
    |--------|------|------|
    | **102** | 处理中 | 表示AI正在思考或处理当前步骤，如"正在加载会话信息"、"正在规划执行步骤"等进度提示 |
    | **300** | 流式片段 | 表示AI正在流式返回内容片段（chunk），data字段包含实际的聊天内容JSON对象 |
    | **500** | 错误 | 表示发生异常或错误，msg字段包含错误信息，data字段可能包含错误详情 |
    | **200** | 完成 | 表示整个请求处理完成，data字段包含最终返回结果（包含chat_response等完整数据） |

    ### 消息流转示例：
    1. `{"code": 102, "msg": "thinking", "data": "🔍 正在加载你的会话信息..."}` - 开始处理
    2. `{"code": 102, "msg": "thinking", "data": "📝 正在规划执行步骤..."}` - 规划中
    3. `{"code": 300, "msg": "chunk", "data": {...}}` - 流式返回内容片段（可能出现多次）
    4. `{"code": 200, "msg": "success", "data": {"chat_response": "最终回复内容", ...}}` - 完成

    ### data字段最终返回结构（code=200时）：
    ``` python
    {
        "code": 200,  # 代表请求状态的整型
        "msg": "XXXX",  # 代表状态信息的字符串
        "data": { # 代表复合返回信息的字典
            # 后面有空补
        }
    }
    ```

    ---
    """
    logger.info(f"路由入口请求 - session_id: {request.session_id}, minor_mode: {request.minor_mode}, user_input[:50]: {request.user_input[:50]}")
    if "auto-AUTO" in request.lang:
        # user_input_get_bcp47_tag = get_bcp47_tag(request.user_input) # 用函数工具获取bcp47 tag，降低消耗，但灵活性差无法识别复杂内容；
        user_input_get_bcp47_tag = (await I18N_Get_BCP47_Tag(request.user_input))['data'].get('bcp47_tag', "zh-CN")  # 用LLM获取bcp 47 tag;
        request.lang = user_input_get_bcp47_tag

    if request.stream_flag:
        return StreamingResponse(
            content=planner_service.stream_plan(request),  # 直接传入生成器函数（无需加()，StreamingResponse会自动执行）
            media_type="text/event-stream; charset=utf-8",  # 改为SSE格式更通用
            headers={
                "Cache-Control": "no-cache",  # 禁止客户端缓存，确保实时接收
                "Connection": "keep-alive",  # 保持长连接，支撑流式传输
                "X-Accel-Buffering": "no",  # 禁用Nginx等反向代理的缓冲（关键！代理层不缓冲才会实时推流）
                "Access-Control-Allow-Origin": "*"  # 跨域支持
            }
        )
    else:
        # 还没实现非流式接口
        pass
        # result = await planner_service.plan(request) # result是一个FunctionPlannerResponse对象
        # logger.info(f"路由入口返回结果：{result}")
        # return result

