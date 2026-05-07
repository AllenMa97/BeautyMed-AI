/**
 * Developer: 马赫·马智勇
 * Position: 大模型算法工程师
 * Created: 2026-04-16
 * Copyright (c) 2026. All rights reserved.
 */
/**
 * 聊天工具类 - 处理上下文生成
 */
const ChatUtils = {
    /**
     * 从消息列表生成符合要求的context字符串
     * @param {Array} messageList 状态管理器中的消息列表（StateManager.getState().messageList）
     * @returns {string} 可解析为JSON的纯字符串（转义特殊字符）
     */
    generateContextString(messageList) {
        if (!Array.isArray(messageList) || messageList.length === 0) {
            return "[]"; // 空历史返回空数组字符串
        }

        // 1. 过滤并转换消息列表为指定结构（只保留用户+AI的成对消息）
        const contextArray = [];
        let lastUserMsg = null; // 临时存储上一条用户消息

        messageList.forEach(msg => {
            if (msg.sender === "用户") {
                // 记录用户输入，等待匹配AI回复
                lastUserMsg = msg.content;
            } else if (msg.sender === "AI" && lastUserMsg) {
                // 匹配到AI回复，组装成一对
                contextArray.push({
                    user: lastUserMsg,
                    response: msg.content // 对应后端的final_result
                });
                lastUserMsg = null; // 重置，准备下一对
            }
        });

        // 2. 转换为JSON字符串（自动处理引号、换行符等转义）
        try {
            // JSON.stringify会自动转义双引号、换行符(\n)、制表符(\t)等特殊字符
            const contextStr = JSON.stringify(contextArray);
            return contextStr;
        } catch (error) {
            console.error("生成context字符串失败：", error);
            return "[]"; // 异常时返回空数组
        }
    }
};