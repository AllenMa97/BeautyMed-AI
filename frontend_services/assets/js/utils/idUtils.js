/**
 * Developer: 马赫·马智勇
 * Position: 大模型算法工程师
 * Created: 2026-04-16
 * Copyright (c) 2026. All rights reserved.
 */
/**
 * ID生成工具类 - 生成/管理user_id和session_id
 */
const IdUtils = {
    /**
     * 生成随机ID（32位UUID格式）
     * @returns {string} 随机ID
     */
    generateRandomId() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    },

    /**
     * 保存ID到本地存储
     * @param {string} userId
     * @param {string} sessionId
     */
    saveIdsToStorage(userId, sessionId) {
        localStorage.setItem('current_user_id', userId);
        localStorage.setItem('current_session_id', sessionId);
    },

    /**
     * 从本地存储获取ID
     * @returns {Object} {userId, sessionId}
     */
    getIdsFromStorage() {
        return {
            userId: localStorage.getItem('current_user_id') || this.generateRandomId(),
            sessionId: localStorage.getItem('current_session_id') || this.generateRandomId()
        };
    }
};