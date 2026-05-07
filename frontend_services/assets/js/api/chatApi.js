/**
 * Developer: 马赫·马智勇
 * Position: 大模型算法工程师
 * Created: 2026-04-16
 * Copyright (c) 2026. All rights reserved.
 */
const ChatApi = {
    _abortController: null,

    abort() {
        if (this._abortController) {
            this._abortController.abort();
            this._abortController = null;
        }
    },

    async uploadFile(file, userId = "", sessionId = "") {
        const url = `${AppConfig.API_BASE_URL}${AppConfig.UPLOAD_API_PATH || '/upload'}`;
        const formData = new FormData();
        formData.append('file', file);
        formData.append('user_id', userId);
        formData.append('session_id', sessionId);

        try {
            const response = await fetch(url, {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                throw new Error('文件上传失败');
            }

            const data = await response.json();
            return data.url || `https://example.com/images/${file.name}`;
        } catch (error) {
            console.error("文件上传失败：", error);
            throw error;
        }
    },

    async sendStreamMessage(
        userInput,
        sessionId = "",
        userId = "",
        context = "[]",
        lang = "zh-CN",
        minorMode = false,
        personalize = true,
        onChunk = () => {},
        onComplete = () => {},
        onTyping = () => {},
        onForbidden = () => {},
        onError = () => {}
    ) {
        this.abort();
        this._abortController = new AbortController();
        const signal = this._abortController.signal;

        const url = `${AppConfig.API_BASE_URL}${AppConfig.CHAT_API_PATH}`;
        const requestBody = {
            session_id: sessionId,
            user_id: userId,
            lang: lang,
            data: null,
            stream_flag: true,
            user_input: userInput,
            context: context,
            minor_mode: minorMode,
            personalize: personalize
        };

        try {
            const response = await fetch(url, {
                method: "POST",
                headers: AuthManager.getAuthHeaders(),
                body: JSON.stringify(requestBody),
                signal: signal
            });

            if (response.status === 401) {
                AuthManager.clearAuth();
                onError({ msg: "登录已过期，请重新登录", code: 401 });
                return;
            }

            if (!response.ok) {
                const errorData = await response.json();
                onError(errorData);
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                const lines = buffer.split("\n");
                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.trim()) continue;
                    if (line.startsWith("data: ")) {
                        const jsonStr = line.slice(6).trim();
                        try {
                            const chunk = JSON.parse(jsonStr);
                            console.log('[SSE] 收到数据包, code:', chunk.code);

                            if (chunk.code === 200) {
                                console.log('[SSE] 调用 onComplete (200)');
                                onComplete(chunk);
                                return;
                            } else if (chunk.code === 300) {
                                console.log('[SSE] 调用 onTyping (300)');
                                onTyping(chunk);
                            } else if (chunk.code === 403) {
                                console.log('[SSE] 调用 onForbidden (403)');
                                onForbidden(chunk);
                            } else {
                                console.log('[SSE] 调用 onChunk (102)');
                                onChunk(chunk);
                            }
                        } catch (e) {
                            console.warn("解析流式chunk失败：", e, "原始行：", line);
                        }
                    }
                }
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('[SSE] 请求已被用户中断');
                return;
            }
            console.error("流式请求失败：", error);
            onError(error);
        } finally {
            this._abortController = null;
        }
    }
};
