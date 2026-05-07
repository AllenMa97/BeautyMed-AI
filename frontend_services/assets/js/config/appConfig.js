/**
 * Developer: 马赫·马智勇
 * Position: 大模型算法工程师
 * Created: 2026-04-16
 * Copyright (c) 2026. All rights reserved.
 */
/**
 * 全局配置文件
 * 集中管理所有可配置项，便于维护
 */
const AppConfig = {
    API_BASE_URL: window.location.origin + "/chat",
    CHAT_API_PATH: "/api/v1/entrance",
    DEBOUNCE_TIME: 500,
    EMOTICONS: ["😊", "😂", "🤔", "👍", "👋", "😎", "🤩", "💡"],
    STORAGE_KEYS: {
        DARK_MODE: "darkMode",
        MESSAGE_HISTORY: "messageHistory",
        API_CONFIG: "apiConfig",
        ACCESS_TOKEN: "accessToken",
        USER_INFO: "userInfo"
    },
    AUTH: {
        SEND_CODE_PATH: "/api/auth/sms/send",
        LOGIN_PATH: "/api/auth/sms/login"
    }
};