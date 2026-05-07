/**
 * Developer: 马赫·马智勇
 * Position: 大模型算法工程师
 * Created: 2026-04-16
 * Copyright (c) 2026. All rights reserved.
 */
/**
 * 时间格式化工具类
 * 封装所有时间相关的格式化逻辑
 */
const DateFormat = {
    /**
     * 格式化消息显示时间（HH:MM）
     * @param {Date} date 日期对象
     * @returns {string} 格式化后的时间
     */
    formatMessageTime(date) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    },

    /**
     * 格式化分组时间（今天/昨天/月日 HH:00）
     * @param {Date} date 日期对象
     * @returns {string} 格式化后的分组时间
     */
    formatGroupTime(date) {
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const msgDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());

        if (msgDate.getTime() === today.getTime()) {
            return `今天 ${date.getHours()}:00`;
        } else {
            const yesterday = new Date(today);
            yesterday.setDate(yesterday.getDate() - 1);
            if (msgDate.getTime() === yesterday.getTime()) {
                return `昨天 ${date.getHours()}:00`;
            } else {
                return `${date.getMonth() + 1}月${date.getDate()}日 ${date.getHours()}:00`;
            }
        }
    },

    /**
     * 格式化完整时间（YYYY-MM-DD HH:MM:SS）
     * @param {Date} date 日期对象
     * @returns {string} 格式化后的完整时间
     */
    formatFullTime(date) {
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
};