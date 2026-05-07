/**
 * Developer: 马赫·马智勇
 * Position: 大模型算法工程师
 * Created: 2026-05-06
 * Copyright (c) 2026. All rights reserved.
 */
const LoginView = {
    els: {
        container: null,
        phoneInput: null,
        codeInput: null,
        sendCodeBtn: null,
        loginBtn: null,
        errorMsg: null
    },

    countdown: 0,
    countdownTimer: null,
    captchaAnswer: 0,

    init() {
        this.initElements();
        this.bindEvents();
        this.generateCaptcha();
        this.checkLoginStatus();
    },

    initElements() {
        this.els.container = document.getElementById("loginContainer");
        this.els.phoneInput = document.getElementById("phoneInput");
        this.els.codeInput = document.getElementById("codeInput");
        this.els.sendCodeBtn = document.getElementById("sendCodeBtn");
        this.els.loginBtn = document.getElementById("loginBtn");
        this.els.errorMsg = document.getElementById("loginErrorMsg");
        this.els.captchaInput = document.getElementById("captchaInput");
        this.els.captchaCanvas = document.getElementById("captchaCanvas");
        this.els.refreshCaptchaBtn = document.getElementById("refreshCaptchaBtn");
    },

    bindEvents() {
        if (this.els.sendCodeBtn) {
            this.els.sendCodeBtn.addEventListener("click", () => this.handleSendCode());
        }
        if (this.els.loginBtn) {
            this.els.loginBtn.addEventListener("click", () => this.handleLogin());
        }
        if (this.els.phoneInput) {
            this.els.phoneInput.addEventListener("keypress", (e) => {
                if (e.key === "Enter") {
                    this.els.codeInput?.focus();
                }
            });
        }
        if (this.els.codeInput) {
            this.els.codeInput.addEventListener("keypress", (e) => {
                if (e.key === "Enter") {
                    this.handleLogin();
                }
            });
        }
        if (this.els.refreshCaptchaBtn) {
            this.els.refreshCaptchaBtn.addEventListener("click", () => this.generateCaptcha());
        }
        if (this.els.captchaCanvas) {
            this.els.captchaCanvas.addEventListener("click", () => this.generateCaptcha());
        }
        document.addEventListener("keydown", (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === "D") {
                e.preventDefault();
                this.toggleDevPanel();
            }
        });
    },

    toggleDevPanel() {
        const panel = document.getElementById("devPanel");
        if (panel) {
            panel.style.display = panel.style.display === "none" ? "block" : "none";
        }
    },

    handleDevLogin() {
        const tokenInput = document.getElementById("devTokenInput");
        const val = tokenInput?.value?.trim();
        if (val !== "pass") {
            this.showError("口令错误");
            return;
        }
        AuthManager.saveTokens("dev_pass_token_" + Date.now());
        StateManager.updateIds("dev_user", IdUtils.generateRandomId());
        StateManager.update({ isLoggedIn: true, userInfo: null });
        this.hide();
        const chatContainer = document.getElementById("chatMainContainer");
        if (chatContainer) {
            chatContainer.style.display = "flex";
        }
        ChatView.init();
    },

    checkLoginStatus() {
        if (AuthManager.isLoggedIn()) {
            const token = AuthManager.getAccessToken();
            if (token) {
                try {
                    const payload = JSON.parse(atob(token.split('.')[1]));
                    if (payload.exp && payload.exp * 1000 < Date.now()) {
                        AuthManager.clearAuth();
                        this.show();
                        return;
                    }
                } catch (e) {
                    AuthManager.clearAuth();
                    this.show();
                    return;
                }
            }
            this.hide();
            const chatContainer = document.getElementById("chatMainContainer");
            if (chatContainer) {
                chatContainer.style.display = "flex";
            }
            ChatView.init();
        } else {
            this.show();
        }
    },

    show() {
        if (this.els.container) {
            this.els.container.classList.remove("hidden");
        }
    },

    hide() {
        if (this.els.container) {
            this.els.container.classList.add("hidden");
        }
    },

    showError(message) {
        if (this.els.errorMsg) {
            this.els.errorMsg.textContent = message;
        }
    },

    clearError() {
        if (this.els.errorMsg) {
            this.els.errorMsg.textContent = "";
        }
    },

    generateCaptcha() {
        const canvas = this.els.captchaCanvas;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;

        const a = Math.floor(Math.random() * 20) + 1;
        const b = Math.floor(Math.random() * 20) + 1;
        const ops = ['+', '-', '×'];
        const op = ops[Math.floor(Math.random() * ops.length)];
        let answer;
        if (op === '+') answer = a + b;
        else if (op === '-') { const tmp = Math.max(a, b); const tmp2 = Math.min(a, b); answer = tmp - tmp2; }
        else answer = a * b;
        this.captchaAnswer = answer;

        ctx.fillStyle = '#f0f0f0';
        ctx.fillRect(0, 0, w, h);

        for (let i = 0; i < 4; i++) {
            ctx.beginPath();
            ctx.moveTo(Math.random() * w, Math.random() * h);
            ctx.lineTo(Math.random() * w, Math.random() * h);
            ctx.strokeStyle = `rgba(${Math.random()*150},${Math.random()*150},${Math.random()*150},0.5)`;
            ctx.stroke();
        }

        for (let i = 0; i < 30; i++) {
            ctx.fillStyle = `rgba(${Math.random()*200},${Math.random()*200},${Math.random()*200},0.6)`;
            ctx.fillRect(Math.random() * w, Math.random() * h, 2, 2);
        }

        const text = `${a} ${op} ${b} = ?`;
        ctx.font = 'bold 20px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#e67e22'];
        for (let i = 0; i < text.length; i++) {
            ctx.fillStyle = colors[Math.floor(Math.random() * colors.length)];
            ctx.save();
            ctx.translate(20 + i * 14, h / 2 + (Math.random() - 0.5) * 8);
            ctx.rotate((Math.random() - 0.5) * 0.4);
            ctx.fillText(text[i], 0, 0);
            ctx.restore();
        }
    },

    validatePhone(phone) {
        const phoneRegex = /^1[3-9]\d{9}$/;
        return phoneRegex.test(phone);
    },

    async handleSendCode() {
        this.clearError();
        const phone = this.els.phoneInput?.value?.trim();
        if (!phone) {
            this.showError("请输入手机号");
            return;
        }
        if (!this.validatePhone(phone)) {
            this.showError("请输入正确的手机号");
            return;
        }
        const captchaVal = this.els.captchaInput?.value?.trim();
        if (!captchaVal) {
            this.showError("请输入图形验证码");
            return;
        }
        if (parseInt(captchaVal) !== this.captchaAnswer) {
            this.showError("图形验证码错误");
            this.generateCaptcha();
            if (this.els.captchaInput) this.els.captchaInput.value = "";
            return;
        }
        try {
            this.els.sendCodeBtn.disabled = true;
            this.els.sendCodeBtn.textContent = "发送中...";
            await AuthApi.sendSmsCode(phone);
            this.startCountdown(60);
        } catch (error) {
            this.showError(error.message || "发送验证码失败");
            this.els.sendCodeBtn.disabled = false;
            this.els.sendCodeBtn.textContent = "获取验证码";
        }
    },

    startCountdown(seconds) {
        this.countdown = seconds;
        this.els.sendCodeBtn.disabled = true;
        this.updateCountdownText();
        this.countdownTimer = setInterval(() => {
            this.countdown--;
            if (this.countdown <= 0) {
                this.stopCountdown();
                this.els.sendCodeBtn.disabled = false;
                this.els.sendCodeBtn.textContent = "获取验证码";
            } else {
                this.updateCountdownText();
            }
        }, 1000);
    },

    updateCountdownText() {
        if (this.els.sendCodeBtn) {
            this.els.sendCodeBtn.textContent = `${this.countdown}s后重发`;
        }
    },

    stopCountdown() {
        if (this.countdownTimer) {
            clearInterval(this.countdownTimer);
            this.countdownTimer = null;
        }
    },

    async handleLogin() {
        this.clearError();
        const phone = this.els.phoneInput?.value?.trim();
        const code = this.els.codeInput?.value?.trim();
        if (!phone) {
            this.showError("请输入手机号");
            return;
        }
        if (!this.validatePhone(phone)) {
            this.showError("请输入正确的手机号");
            return;
        }
        if (!code) {
            this.showError("请输入验证码");
            return;
        }
        try {
            this.els.loginBtn.disabled = true;
            this.els.loginBtn.textContent = "登录中...";
            await AuthManager.login(phone, code);
            StateManager.update({
                isLoggedIn: true,
                userInfo: AuthManager.getUserInfo()
            });
            this.hide();
            const chatContainer = document.getElementById("chatMainContainer");
            if (chatContainer) {
                chatContainer.style.display = "flex";
            }
            ChatView.init();
        } catch (error) {
            this.showError(error.message || "登录失败");
            this.els.loginBtn.disabled = false;
            this.els.loginBtn.textContent = "登录";
        }
    },

    reset() {
        this.stopCountdown();
        if (this.els.phoneInput) this.els.phoneInput.value = "";
        if (this.els.codeInput) this.els.codeInput.value = "";
        if (this.els.captchaInput) this.els.captchaInput.value = "";
        if (this.els.sendCodeBtn) {
            this.els.sendCodeBtn.disabled = false;
            this.els.sendCodeBtn.textContent = "获取验证码";
        }
        if (this.els.loginBtn) {
            this.els.loginBtn.disabled = false;
            this.els.loginBtn.textContent = "登录";
        }
        this.clearError();
        this.generateCaptcha();
    },

    showRegister() {
        const loginBox = document.querySelector('#loginContainer .login-box');
        const registerBox = document.getElementById('registerBox');
        if (loginBox) loginBox.style.display = 'none';
        if (registerBox) registerBox.style.display = 'block';
    },

    showLogin() {
        const loginBox = document.querySelector('#loginContainer .login-box');
        const registerBox = document.getElementById('registerBox');
        if (registerBox) registerBox.style.display = 'none';
        if (loginBox) loginBox.style.display = 'block';
        this.stopRegCountdown();
    },

    validateIdCard(idCard) {
        const reg = /^[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$/;
        return reg.test(idCard);
    },

    regCountdown: 0,
    regCountdownTimer: null,

    stopRegCountdown() {
        if (this.regCountdownTimer) {
            clearInterval(this.regCountdownTimer);
            this.regCountdownTimer = null;
        }
        this.regCountdown = 0;
        const btn = document.getElementById('regSendCodeBtn');
        if (btn) {
            btn.disabled = false;
            btn.textContent = '获取验证码';
        }
    },

    async handleRegSendCode() {
        const phone = document.getElementById('regPhone')?.value?.trim();
        const errorEl = document.getElementById('registerErrorMsg');
        if (errorEl) errorEl.textContent = '';

        if (!phone) { if (errorEl) errorEl.textContent = '请输入手机号'; return; }
        if (!this.validatePhone(phone)) { if (errorEl) errorEl.textContent = '手机号格式不正确'; return; }

        const btn = document.getElementById('regSendCodeBtn');
        if (btn) btn.disabled = true;

        try {
            await AuthApi.sendSmsCode(phone);
            this.regCountdown = 60;
            if (btn) btn.textContent = `${this.regCountdown}s`;
            this.regCountdownTimer = setInterval(() => {
                this.regCountdown--;
                if (this.regCountdown <= 0) {
                    this.stopRegCountdown();
                } else if (btn) {
                    btn.textContent = `${this.regCountdown}s`;
                }
            }, 1000);
        } catch (err) {
            if (errorEl) errorEl.textContent = err.message || '发送验证码失败';
            if (btn) btn.disabled = false;
        }
    },

    async handleRegister() {
        const name = document.getElementById('regName')?.value?.trim();
        const idCard = document.getElementById('regIdCard')?.value?.trim();
        const phone = document.getElementById('regPhone')?.value?.trim();
        const code = document.getElementById('regCode')?.value?.trim();
        const errorEl = document.getElementById('registerErrorMsg');

        const showError = (msg) => {
            if (errorEl) errorEl.textContent = msg;
        };
        showError('');

        if (!name) { showError('请输入姓名'); return; }
        if (!idCard) { showError('请输入身份证号'); return; }
        if (!this.validateIdCard(idCard)) { showError('身份证号格式不正确'); return; }
        if (!phone) { showError('请输入手机号'); return; }
        if (!this.validatePhone(phone)) { showError('手机号格式不正确'); return; }
        if (!code) { showError('请输入验证码'); return; }

        try {
            const regResponse = await AuthApi.registerWithSms(name, idCard, phone, code);
            const regToken = regResponse.access_token || regResponse.data?.access_token || "";
            if (regToken) {
                AuthManager.saveTokens(regToken);
                try {
                    const payload = JSON.parse(atob(regToken.split('.')[1]));
                    if (payload.uid) {
                        StateManager.updateIds(String(payload.uid), IdUtils.generateRandomId());
                    }
                } catch (e) {}
            } else {
                await AuthManager.login(phone, code);
            }
            StateManager.update({
                isLoggedIn: true,
                userInfo: AuthManager.getUserInfo()
            });
            this.hide();
            this.stopRegCountdown();
            const chatContainer = document.getElementById("chatMainContainer");
            if (chatContainer) {
                chatContainer.style.display = "flex";
            }
            ChatView.init();
        } catch (err) {
            showError(err.message || '注册失败，请稍后重试');
        }
    }
};
