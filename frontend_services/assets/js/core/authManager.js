/**
 * Developer: 马赫·马智勇
 * Position: 大模型算法工程师
 * Created: 2026-05-06
 * Copyright (c) 2026. All rights reserved.
 */
const AuthManager = {
    isLoggedIn() {
        const token = this.getAccessToken();
        return !!token;
    },

    getAccessToken() {
        return localStorage.getItem(AppConfig.STORAGE_KEYS.ACCESS_TOKEN);
    },

    getUserInfo() {
        const userInfoStr = localStorage.getItem(AppConfig.STORAGE_KEYS.USER_INFO);
        if (userInfoStr) {
            try {
                return JSON.parse(userInfoStr);
            } catch (e) {
                return null;
            }
        }
        return null;
    },

    saveTokens(accessToken) {
        localStorage.setItem(AppConfig.STORAGE_KEYS.ACCESS_TOKEN, accessToken);
    },

    saveUserInfo(userInfo) {
        localStorage.setItem(AppConfig.STORAGE_KEYS.USER_INFO, JSON.stringify(userInfo));
    },

    async login(phone, code) {
        const response = await AuthApi.loginWithSms(phone, code);
        const token = response.access_token || response.data?.access_token || "";
        if (token) {
            this.saveTokens(token);
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                if (payload.uid) {
                    StateManager.updateIds(String(payload.uid), IdUtils.generateRandomId());
                }
            } catch (e) {}
        }
        return response;
    },

    clearAuth() {
        localStorage.removeItem(AppConfig.STORAGE_KEYS.ACCESS_TOKEN);
        localStorage.removeItem(AppConfig.STORAGE_KEYS.USER_INFO);
    },

    getAuthHeaders() {
        const token = this.getAccessToken();
        const headers = {
            "Content-Type": "application/json"
        };
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }
        return headers;
    },

    devLogin(token) {
        this.saveTokens(token);
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            if (payload.user_id) {
                StateManager.updateIds(String(payload.user_id), IdUtils.generateRandomId());
            }
            if (payload.user_info) {
                this.saveUserInfo(payload.user_info);
            }
        } catch (e) {}
    }
};
