/**
 * Developer: 马赫·马智勇
 * Position: 大模型算法工程师
 * Created: 2026-05-06
 * Copyright (c) 2026. All rights reserved.
 */
const AuthApi = {
    async sendSmsCode(phone) {
        const url = `${AppConfig.API_BASE_URL}${AppConfig.AUTH.SEND_CODE_PATH}`;
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ phone })
        });
        const data = await response.json();
        if (response.status === 429) {
            throw new Error("请求过于频繁，请稍后再试");
        }
        if (!response.ok && !(data.success === true)) {
            throw new Error(data.message || data.msg || "发送验证码失败");
        }
        return data;
    },

    async loginWithSms(phone, code) {
        const url = `${AppConfig.API_BASE_URL}${AppConfig.AUTH.LOGIN_PATH}`;
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ phone, code })
        });
        const data = await response.json();
        if (response.status === 429) {
            throw new Error("请求过于频繁，请稍后再试");
        }
        if (!response.ok && !(data.success === true)) {
            throw new Error(data.message || data.msg || "登录失败");
        }
        return data;
    },

    async registerWithSms(realName, idCard, phone, code) {
        const url = `${AppConfig.API_BASE_URL}${AppConfig.AUTH.LOGIN_PATH}`;
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ real_name: realName, id_card: idCard, phone, code })
        });
        const data = await response.json();
        if (response.status === 429) {
            throw new Error("请求过于频繁，请稍后再试");
        }
        if (!response.ok && !(data.success === true)) {
            throw new Error(data.message || data.msg || "注册失败");
        }
        return data;
    }
};
