/**
 * Developer: 马赫·马智勇
 * Position: 大模型算法工程师
 * Created: 2026-04-16
 * Copyright (c) 2026. All rights reserved.
 */
/**
 * 聊天页面核心逻辑 - Markdown渲染+渲染切换
 */
const ChatView = {
    els: {
        chatContent: null,
        emptyTip: null,
        msgInput: null,
        sendBtn: null,
        themeSwitch: null,
        themeSelect: null,
        fileInput: null,
        uploadPreview: null,
        productCarousel: null,
        carouselSlides: null,
        carouselPrev: null,
        carouselNext: null,
        carouselIndicators: null,
        body: document.body,
        userIdInput: null,
        sessionIdInput: null,
        resetIdBtn: null,
        messageContainer: null
    },

    // 轮播图数据
    carouselData: [
        {
            image: "assets/images/carousel/carousel1.png",
            title: "医美产品系列",
            description: "远想生物专业医美产品线"
        },
        {
            image: "assets/images/carousel/carousel2.png",
            title: "医疗设备",
            description: "先进的医疗设备与技术"
        },
        {
            image: "assets/images/carousel/carousel3.png",
            title: "医美诊所",
            description: "舒适优雅的医美诊所环境"
        },
        {
            image: "assets/images/carousel/carousel4.png",
            title: "专业团队",
            description: "经验丰富的医疗团队"
        },
        {
            image: "assets/images/carousel/carousel5.png",
            title: "客户关怀",
            description: "贴心的客户服务体验"
        }
    ],
    // 当前轮播图索引
    currentSlide: 0,
    // 轮播图自动播放定时器
    carouselTimer: null,

    // 上传文件列表
    uploadedFiles: [],
    // 最大上传文件数
    maxFiles: 5,
    // 渲染状态缓存
    renderState: new Map(), // key: messageId, value: true(渲染)/false(原始)

    /**
     * 初始化页面
     */
    init() {
        // 初始化DOM元素引用（必须和HTML里的ID/类名对应）
        this.els = {};
        this.initElements();
        StateManager.init();
        this.initTheme();
        this.initLanguage();
        this.initMinorMode();
        this.initPersonalize();
        this.initIdManager();
        this.initCarousel();
        this.bindEvents();
        this.addWelcomeMessage();
        this.showAiDisclaimer();
        setTimeout(() => {
            this.els.msgInput.focus();
            this.autoScrollToBottom();
        }, 500);

    },

    /**
     * 初始化语言设置
     */
    initLanguage() {
        const savedLanguage = localStorage.getItem('currentLanguage');
        if (savedLanguage && this.els.langSelect) {
            this.els.langSelect.value = savedLanguage;
        } else if (this.els.langSelect) {
            this.els.langSelect.value = 'auto-AUTO';
        }
    },

    initMinorMode() {
        const savedMinorMode = localStorage.getItem('minorMode') === "true";
        StateManager.update({ minorMode: savedMinorMode });
        if (this.els.minorModeBtn) {
            this.els.minorModeBtn.classList.toggle('active', savedMinorMode);
            const textEl = this.els.minorModeBtn.querySelector('.mode-text');
            if (textEl) {
                textEl.textContent = savedMinorMode ? '未成年人模式：开' : '未成年人模式：关';
            }
        }
    },

    toggleMinorMode() {
        const currentState = StateManager.getState().minorMode;
        const newState = !currentState;
        StateManager.update({ minorMode: newState });
        localStorage.setItem('minorMode', String(newState));
        if (this.els.minorModeBtn) {
            this.els.minorModeBtn.classList.toggle('active', newState);
            const textEl = this.els.minorModeBtn.querySelector('.mode-text');
            if (textEl) {
                textEl.textContent = newState ? '未成年人模式：开' : '未成年人模式：关';
            }
        }
    },

    initPersonalize() {
        const saved = localStorage.getItem('personalize') !== 'false';
        StateManager.update({ personalize: saved });
        if (this.els.personalizeBtn) {
            this.els.personalizeBtn.classList.toggle('active', saved);
            const textEl = this.els.personalizeBtn.querySelector('.mode-text');
            if (textEl) {
                textEl.textContent = saved ? '个性化推荐：开' : '个性化推荐：关';
            }
        }
    },

    togglePersonalize() {
        const currentState = StateManager.getState().personalize;
        const newState = !currentState;
        StateManager.update({ personalize: newState });
        localStorage.setItem('personalize', String(newState));
        if (this.els.personalizeBtn) {
            this.els.personalizeBtn.classList.toggle('active', newState);
            const textEl = this.els.personalizeBtn.querySelector('.mode-text');
            if (textEl) {
                textEl.textContent = newState ? '个性化推荐：开' : '个性化推荐：关';
            }
        }
    },

    handleLogout() {
        AuthManager.clearAuth();
        localStorage.removeItem('aiDisclaimerAccepted');
        localStorage.removeItem('minorMode');
        localStorage.removeItem('personalize');
        const chatContainer = document.getElementById("chatMainContainer");
        if (chatContainer) {
            chatContainer.style.display = "none";
        }
        const loginContainer = document.getElementById("loginContainer");
        if (loginContainer) {
            loginContainer.classList.remove("hidden");
        }
        LoginView.reset();
        LoginView.show();
    },

    showAiDisclaimer(forceShow) {
        if (!forceShow && localStorage.getItem('aiDisclaimerAccepted') === 'true') {
            return;
        }
        if (document.getElementById('aiDisclaimerOverlay')) {
            document.body.removeChild(document.getElementById('aiDisclaimerOverlay'));
        }
        const overlay = document.createElement('div');
        overlay.id = 'aiDisclaimerOverlay';
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:10000;display:flex;align-items:center;justify-content:center;';
        const box = document.createElement('div');
        box.style.cssText = 'background:#fff;border-radius:16px;padding:28px 24px;max-width:400px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,0.2);text-align:center;';
        box.innerHTML = `
            <div style="font-size:20px;font-weight:600;margin-bottom:12px;color:#333;">温馨提示</div>
            <div style="font-size:14px;color:#666;line-height:1.8;text-align:left;margin-bottom:20px;">
                <p>本平台由 AI 技术驱动，所有回复内容均由人工智能生成，仅供参考。</p>
                <p style="margin-top:8px;">AI 生成的内容可能存在不准确或不完整的情况，请您结合实际情况<strong style="color:#e74c3c;">认真研判</strong>，切勿将其作为专业医疗、法律等决策的唯一依据。</p>
                <p style="margin-top:8px;">如有任何健康或法律问题，请咨询相关领域的专业人士。</p>
            </div>
            <button id="disclaimerConfirmBtn" style="width:100%;padding:10px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border:none;border-radius:8px;font-size:15px;cursor:pointer;">我已知晓</button>
        `;
        overlay.appendChild(box);
        document.body.appendChild(overlay);

        const closeOverlay = () => {
            const el = document.getElementById('aiDisclaimerOverlay');
            if (el && el.parentNode) {
                el.parentNode.removeChild(el);
            }
        };

        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                closeOverlay();
            }
        });
        document.getElementById('disclaimerConfirmBtn').addEventListener('click', (e) => {
            e.stopPropagation();
            localStorage.setItem('aiDisclaimerAccepted', 'true');
            closeOverlay();
        });
    },

    initElements() {
        this.els.body = document.body;
        this.els.chatContent = DomUtils.getEl("chatContent");
        this.els.emptyTip = DomUtils.getEl("emptyTip");
        this.els.msgInput = DomUtils.getEl("msgInput");
        this.els.sendBtn = DomUtils.getEl("sendBtn");
        this.els.themeSwitch = DomUtils.getEl("themeSwitch");
        this.els.themeSelect = DomUtils.getEl("themeSelect");
        this.els.langSelect = DomUtils.getEl("langSelect");
        this.els.fileInput = DomUtils.getEl("fileInput");
        this.els.uploadPreview = DomUtils.getEl("uploadPreview");
        this.els.scrollToTop = DomUtils.getEl("scrollToTop");
        this.els.exampleQuestions = DomUtils.getEl("exampleQuestions");
        this.els.refreshExamples = DomUtils.getEl("refreshExamples");
        this.els.examplesContainer = DomUtils.getEl("examplesContainer");
        this.els.chatMainContainer = DomUtils.getEl("chatMainContainer");
        this.initApiConfigElements();
        this.els.productCarousel = DomUtils.getEl("productCarousel");
        this.els.carouselSlides = DomUtils.getEl("carouselSlides");
        this.els.carouselPrev = DomUtils.getEl("carouselPrev");
        this.els.carouselNext = DomUtils.getEl("carouselNext");
        this.els.carouselIndicators = DomUtils.getEl("carouselIndicators");
        this.els.userIdInput = DomUtils.getEl("userIdInput");
        this.els.sessionIdInput = DomUtils.getEl("sessionIdInput");
        this.els.resetIdBtn = DomUtils.getEl("resetIdBtn");
        this.els.idToggleBtn = DomUtils.getEl("idToggleBtn");
        this.els.idShowBar = DomUtils.getEl("idShowBar");
        this.els.minorModeBtn = DomUtils.getEl("minorModeBtn");
        this.els.personalizeBtn = DomUtils.getEl("personalizeBtn");
        this.els.stopBtn = DomUtils.getEl("stopBtn");
        this.els.disclaimerBtn = DomUtils.getEl("disclaimerBtn");
        this.els.messageContainer = DomUtils.getEl("messageContainer");
    },

    /**
     * 初始化轮播图
     */
    initCarousel() {
        // 渲染轮播图
        this.renderCarousel();
        // 绑定轮播图事件
        this.bindCarouselEvents();
        // 启动自动播放
        this.startCarouselAutoPlay();
    },

    /**
     * 绑定轮播图事件
     */
    bindCarouselEvents() {
        const prevBtn = this.els.carouselPrev;
        const nextBtn = this.els.carouselNext;
        
        // 左右切换按钮事件
        if (prevBtn) {
            prevBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.prevSlide();
            });
        }
        
        if (nextBtn) {
            nextBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.nextSlide();
            });
        }
        
        // 触摸滑动支持
        this.initTouchSwipe();
        
        // 鼠标悬停停止自动播放
        const carousel = this.els.productCarousel;
        if (carousel) {
            carousel.addEventListener('mouseenter', () => {
                this.stopCarouselAutoPlay();
            });
            carousel.addEventListener('mouseleave', () => {
                this.startCarouselAutoPlay();
            });
        }
    },

    /**
     * 初始化触摸滑动
     */
    initTouchSwipe() {
        const slidesContainer = this.els.carouselSlides;
        if (!slidesContainer) return;
        
        let touchStartX = 0;
        let touchEndX = 0;
        let isDragging = false;
        
        // 触摸开始
        slidesContainer.addEventListener('touchstart', (e) => {
            touchStartX = e.touches[0].clientX;
            isDragging = true;
            this.stopCarouselAutoPlay();
        }, { passive: true });
        
        // 触摸移动
        slidesContainer.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            touchEndX = e.touches[0].clientX;
        }, { passive: true });
        
        // 触摸结束
        slidesContainer.addEventListener('touchend', (e) => {
            if (!isDragging) return;
            isDragging = false;
            
            const diff = touchStartX - touchEndX;
            const minSwipeDistance = 50;
            
            if (Math.abs(diff) > minSwipeDistance) {
                if (diff > 0) {
                    // 向左滑 - 下一张
                    this.nextSlide();
                } else {
                    // 向右滑 - 上一张
                    this.prevSlide();
                }
            }
            
            this.startCarouselAutoPlay();
        });
        
        // 鼠标拖拽支持（桌面端）
        let mouseStartX = 0;
        let mouseEndX = 0;
        
        slidesContainer.addEventListener('mousedown', (e) => {
            mouseStartX = e.clientX;
            isDragging = true;
            this.stopCarouselAutoPlay();
        });
        
        slidesContainer.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            mouseEndX = e.clientX;
        });
        
        slidesContainer.addEventListener('mouseup', (e) => {
            if (!isDragging) return;
            isDragging = false;
            
            const diff = mouseStartX - mouseEndX;
            const minSwipeDistance = 50;
            
            if (Math.abs(diff) > minSwipeDistance) {
                if (diff > 0) {
                    this.nextSlide();
                } else {
                    this.prevSlide();
                }
            }
            
            this.startCarouselAutoPlay();
        });
        
        slidesContainer.addEventListener('mouseleave', () => {
            if (isDragging) {
                isDragging = false;
                this.startCarouselAutoPlay();
            }
        });
    },

    /**
     * 渲染轮播图
     */
    renderCarousel() {
        const { carouselSlides, carouselIndicators } = this.els;
        if (!carouselSlides || !carouselIndicators) return;

        // 清空现有内容
        carouselSlides.innerHTML = '';
        carouselIndicators.innerHTML = '';

        // 渲染轮播图幻灯片
        this.carouselData.forEach((item, index) => {
            // 创建幻灯片元素
            const slide = DomUtils.createEl('div', {
                className: `carousel-slide ${index === 0 ? 'active' : ''}`
            });
            
            // 创建图片元素
            const img = DomUtils.createEl('img', {
                src: item.image,
                alt: item.title
            });
            
            // 创建内容元素
            const content = DomUtils.createEl('div', {
                className: 'carousel-slide-content'
            });
            
            // 创建标题元素
            const title = DomUtils.createEl('h3', {
                className: 'carousel-slide-title',
                textContent: item.title
            });
            
            // 创建描述元素
            const desc = DomUtils.createEl('p', {
                className: 'carousel-slide-desc',
                textContent: item.description
            });
            
            // 组装元素
            content.appendChild(title);
            content.appendChild(desc);
            slide.appendChild(img);
            slide.appendChild(content);
            carouselSlides.appendChild(slide);
            
            // 创建指示器元素
            const indicator = DomUtils.createEl('button', {
                className: `carousel-indicator ${index === 0 ? 'active' : ''}`,
                dataset: { index }
            });
            
            // 添加点击事件
            indicator.addEventListener('click', () => {
                this.goToSlide(index);
            });
            
            carouselIndicators.appendChild(indicator);
        });
    },

    /**
     * 切换到指定幻灯片
     */
    goToSlide(index) {
        const { carouselSlides, carouselIndicators } = this.els;
        if (!carouselSlides || !carouselIndicators) return;

        // 更新当前索引
        this.currentSlide = index;
        
        // 更新幻灯片位置
        carouselSlides.style.transform = `translateX(-${index * 100}%)`;
        
        // 更新指示器状态
        const indicators = carouselIndicators.querySelectorAll('.carousel-indicator');
        indicators.forEach((indicator, i) => {
            if (i === index) {
                indicator.classList.add('active');
            } else {
                indicator.classList.remove('active');
            }
        });
    },

    /**
     * 下一张幻灯片
     */
    nextSlide() {
        this.currentSlide = (this.currentSlide + 1) % this.carouselData.length;
        this.goToSlide(this.currentSlide);
    },

    /**
     * 上一张幻灯片
     */
    prevSlide() {
        this.currentSlide = (this.currentSlide - 1 + this.carouselData.length) % this.carouselData.length;
        this.goToSlide(this.currentSlide);
    },

    /**
     * 启动轮播图自动播放
     */
    startCarouselAutoPlay() {
        // 清除现有定时器
        if (this.carouselTimer) {
            clearInterval(this.carouselTimer);
        }
        
        // 设置新定时器
        this.carouselTimer = setInterval(() => {
            this.nextSlide();
        }, 5000); // 每5秒切换一次
    },

    /**
     * 停止轮播图自动播放
     */
    stopCarouselAutoPlay() {
        if (this.carouselTimer) {
            clearInterval(this.carouselTimer);
            this.carouselTimer = null;
        }
    },

    /**
     * 初始化主题
     */
    initTheme() {
        const savedTheme = localStorage.getItem('currentTheme') || 'light';
        this.applyTheme(savedTheme);
        if (this.els.themeSelect) {
            this.els.themeSelect.value = savedTheme;
        }
    },

    /**
     * 应用主题
     */
    applyTheme(theme) {
        // 移除所有主题类
        if (this.els.body) {
            this.els.body.classList.remove('dark-mode', 'light-theme', 'soft-theme', 'modern-theme', 'minimal-theme', 'vibrant-theme');
            
            // 应用选中的主题
            if (theme === 'dark') {
                this.els.body.classList.add('dark-mode');
            } else if (theme === 'light') {
                this.els.body.classList.add('light-theme');
            } else if (theme === 'soft') {
                this.els.body.classList.add('soft-theme');
            } else if (theme === 'modern') {
                this.els.body.classList.add('modern-theme');
            } else if (theme === 'minimal') {
                this.els.body.classList.add('minimal-theme');
            } else if (theme === 'vibrant') {
                this.els.body.classList.add('vibrant-theme');
            }
            
            // 保存主题到本地存储
            localStorage.setItem('currentTheme', theme);
        }
    },

    /**
     * 初始化ID展示
     */
    initIdManager() {
        const { userId } = StateManager.getState();
        const newSessionId = IdUtils.generateRandomId();
        
        this.els.userIdInput.value = userId;
        this.els.sessionIdInput.value = newSessionId;
        
        StateManager.updateIds(userId, newSessionId);
        
        const isMobile = window.innerWidth <= 768;
        if (isMobile && this.els.idShowBar) {
            this.els.idShowBar.classList.add('id-bar-hidden');
            this.els.idShowBar.classList.remove('id-bar-visible');
        } else if (this.els.idShowBar) {
            this.els.idShowBar.classList.add('id-bar-visible');
            this.els.idShowBar.classList.remove('id-bar-hidden');
            if (this.els.idToggleBtn) {
                this.els.idToggleBtn.classList.add('expanded');
                this.els.idToggleBtn.querySelector('.toggle-text').textContent = '收起用户信息';
            }
        }
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 发送按钮
        DomUtils.on(this.els.sendBtn, "click", this.handleSendMessage.bind(this));
        if (this.els.stopBtn) {
            DomUtils.on(this.els.stopBtn, "click", () => this.handleStopGenerate());
        }
        // Enter 发送，Shift+Enter 换行
        DomUtils.on(this.els.msgInput, "keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                this.handleSendMessage();
            }
        });
        // 输入框变化
        DomUtils.on(this.els.msgInput, "input", this.handleInputChange.bind(this));
        // 主题选择器变化
        DomUtils.on(this.els.themeSelect, "change", (e) => {
            this.applyTheme(e.target.value);
        });
        // 语言选择器变化
        if (this.els.langSelect) {
            DomUtils.on(this.els.langSelect, "change", (e) => {
                localStorage.setItem('currentLanguage', e.target.value);
            });
        }
        // 文件输入变化
        DomUtils.on(this.els.fileInput, "change", this.handleFileInput.bind(this));
        // 重置ID
        DomUtils.on(this.els.resetIdBtn, "click", this.resetIds.bind(this));
        // ID输入框失焦保存
        DomUtils.on(this.els.userIdInput, "blur", this.saveIds.bind(this));
        DomUtils.on(this.els.sessionIdInput, "blur", this.saveIds.bind(this));
        // 图片操作按钮（事件委托）
        DomUtils.on(this.els.messageContainer, "click", (e) => {
            const actionBtn = e.target.closest('.action-btn');
            if (actionBtn) {
                e.preventDefault();
                e.stopPropagation();
                const action = actionBtn.dataset.action;
                const imageContainer = actionBtn.closest('.image-container');
                if (imageContainer) {
                    this.handleImageAction(action, imageContainer);
                }
            }
        });
        // 滚动到顶部按钮
        if (this.els.scrollToTop) {
            DomUtils.on(this.els.scrollToTop, "click", this.scrollToTop.bind(this));
        }
        // 示例问题按钮
        if (this.els.exampleQuestions) {
            DomUtils.on(this.els.exampleQuestions, "click", (e) => {
                const target = e.target.closest('.example-btn');
                if (target) {
                    const question = target.dataset.question;
                    if (this.els.msgInput) {
                        this.els.msgInput.value = question;
                        if (typeof this.handleSendMessage === 'function') {
                            this.handleSendMessage();
                        }
                    }
                }
            });
        }
        
        // 换一批话题按钮
        if (this.els.refreshExamples) {
            DomUtils.on(this.els.refreshExamples, "click", this.refreshExampleQuestions.bind(this));
        }
        // 滚动事件
        window.addEventListener("scroll", this.handleScroll.bind(this));
        
        // 绑定API配置相关事件
        this.bindApiConfigEvents();
    },

    /**
     * 处理滚动事件
     */
    handleScroll() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollToTopButton = this.els.scrollToTop;
        
        if (scrollToTopButton) {
            if (scrollTop > 300) {
                scrollToTopButton.style.display = 'block';
            } else {
                scrollToTopButton.style.display = 'none';
            }
        }
    },

    /**
     * 滚动到顶部
     */
    scrollToTop() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    },

    /**
     * 重置随机ID
     */
    resetIds() {
        const newUserId = IdUtils.generateRandomId();
        const newSessionId = IdUtils.generateRandomId();
        this.els.userIdInput.value = newUserId;
        this.els.sessionIdInput.value = newSessionId;
        StateManager.updateIds(newUserId, newSessionId);
        this.els.resetIdBtn.style.transform = "translateY(2px)";
        setTimeout(() => this.els.resetIdBtn.style.transform = "translateY(-1px)", 100);
        alert("ID已重置为随机值！");
    },

    /**
     * 切换ID栏展开/折叠（移动端）
     */
    toggleIdBar() {
        if (this.els.idShowBar && this.els.idToggleBtn) {
            const isHidden = this.els.idShowBar.classList.contains('id-bar-hidden');
            if (isHidden) {
                this.els.idShowBar.classList.remove('id-bar-hidden');
                this.els.idShowBar.classList.add('id-bar-visible');
                this.els.idToggleBtn.classList.add('expanded');
                this.els.idToggleBtn.querySelector('.toggle-text').textContent = '收起用户信息';
            } else {
                this.els.idShowBar.classList.remove('id-bar-visible');
                this.els.idShowBar.classList.add('id-bar-hidden');
                this.els.idToggleBtn.classList.remove('expanded');
                this.els.idToggleBtn.querySelector('.toggle-text').textContent = '展开用户信息';
            }
        }
    },

    /**
     * 保存ID
     */
    saveIds() {
        const userId = this.els.userIdInput.value.trim();
        const sessionId = this.els.sessionIdInput.value.trim();
        if (!userId || !sessionId) {
            alert("User ID和Session ID不能为空！");
            const { userId: oldUserId, sessionId: oldSessionId } = StateManager.getState();
            this.els.userIdInput.value = oldUserId;
            this.els.sessionIdInput.value = oldSessionId;
            return;
        }
        StateManager.updateIds(userId, sessionId);
    },

    /**
     * 处理输入框变化
     */
    handleInputChange() {
        const value = this.els.msgInput.value.trim();
        const { isSending } = StateManager.getState();
        this.els.sendBtn.disabled = (!value && this.uploadedFiles.length === 0) || isSending;
    },

    _toggleSendStopBtn(sending) {
        if (this.els.sendBtn) {
            this.els.sendBtn.style.display = sending ? 'none' : 'flex';
        }
        if (this.els.stopBtn) {
            this.els.stopBtn.style.display = sending ? 'flex' : 'none';
        }
    },

    handleStopGenerate() {
        ChatApi.abort();
        StateManager.update({ isSending: false });
        this._toggleSendStopBtn(false);
        this.handleInputChange();
    },

    /**
     * 处理文件输入
     */
    handleFileInput(e) {
        const files = e.target.files;
        if (!files.length) return;

        // 检查文件数量限制
        if (this.uploadedFiles.length + files.length > this.maxFiles) {
            alert(`最多只能上传${this.maxFiles}张图片`);
            return;
        }

        // 处理每个文件
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            if (this.validateFile(file)) {
                this.uploadedFiles.push(file);
                this.showUploadPreview(file);
            }
        }

        // 清空文件输入，允许重复选择相同文件
        e.target.value = '';

        // 更新发送按钮状态
        this.handleInputChange();
    },

    /**
     * 验证文件
     */
    validateFile(file) {
        // 检查文件类型
        if (!file.type.startsWith('image/')) {
            alert('只能上传图片文件');
            return false;
        }

        // 检查文件大小（限制为5MB）
        const maxSize = 5 * 1024 * 1024;
        if (file.size > maxSize) {
            alert('图片大小不能超过5MB');
            return false;
        }

        return true;
    },

    /**
     * 显示上传预览
     */
    showUploadPreview(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const previewItem = DomUtils.createEl('div', { className: 'preview-item' });
            const img = DomUtils.createEl('img', { src: e.target.result });
            const removeBtn = DomUtils.createEl('button', { 
                className: 'preview-remove',
                title: '移除图片'
            }, '×');

            // 添加移除事件
            removeBtn.addEventListener('click', () => {
                this.removeFile(file, previewItem);
            });

            // 组装
            previewItem.appendChild(img);
            previewItem.appendChild(removeBtn);
            this.els.uploadPreview.appendChild(previewItem);
        };
        reader.readAsDataURL(file);
    },

    /**
     * 移除文件
     */
    removeFile(file, previewItem) {
        // 从上传文件列表中移除
        const index = this.uploadedFiles.findIndex(f => f.name === file.name && f.size === file.size);
        if (index !== -1) {
            this.uploadedFiles.splice(index, 1);
        }

        // 从预览中移除
        if (previewItem && previewItem.parentNode) {
            previewItem.parentNode.removeChild(previewItem);
        }

        // 更新发送按钮状态
        this.handleInputChange();
    },

    /**
     * 添加欢迎消息
     */
    addWelcomeMessage() {
        const welcomeMsg = {
            sender: "AI",
            content: "👋 您好！我是YISIA，您的专属美丽闺蜜！\n\n**我擅长：**\n- 陪你聊天解闷\n- 分享医美护肤小知识\n- 讨论时尚美学话题\n- 倾听你的心事\n- 提供贴心建议\n\n**聊聊这些话题吧：**\n- 今天的心情怎么样？\n- 有什么烦恼想倾诉？\n- 想了解哪些护肤小技巧？\n- 最近有什么开心的事？\n- 需要什么建议吗？\n\n**� 温馨提示：** 随意跟我聊天就好，就像跟闺蜜聊天一样轻松自在～",
            time: DateFormat.formatFullTime(new Date()),
            id: `welcome_${Date.now()}`
        };
        // 默认渲染Markdown
        this.renderState.set(welcomeMsg.id, true);
        StateManager.addMessage(welcomeMsg);
        this.renderMessages();
    },

    /**
     * 自动滚动到底部
     */
    autoScrollToBottom() {
        this.els.chatContent.scrollTo({
            top: this.els.chatContent.scrollHeight,
            behavior: "smooth"
        });
        setTimeout(() => {
            this.els.chatContent.scrollTop = this.els.chatContent.scrollHeight;
        }, 100);
    },

    /**
     * 更新AI中间消息
     */
    updateAiMiddleMessage(placeholderId, content) {
        StateManager.updateMessageContent(placeholderId, content, true);
        this.renderMessages();
        this.autoScrollToBottom();
    },
    
    /**
     * 打字机效果 - 逐字显示新增内容
     */
    typewriterTimer: null,
    typewriterEffect(placeholderId, currentDisplay, newPart) {
        if (this.typewriterTimer) {
            clearTimeout(this.typewriterTimer);
            this.typewriterTimer = null;
        }
        
        let charIndex = 0;
        const speed = 30;
        
        const typeChar = () => {
            if (charIndex < newPart.length) {
                const displayContent = currentDisplay + newPart.substring(0, charIndex + 1);
                StateManager.updateMessageContent(placeholderId, displayContent, false);
                this.renderMessages();
                this.autoScrollToBottom();
                charIndex++;
                this.typewriterTimer = setTimeout(typeChar, speed);
            } else {
                this.typewriterTimer = null;
                this.els.msgInput.focus();
            }
        };
        
        if (newPart.length > 0) {
            typeChar();
        } else {
            this.els.msgInput.focus();
        }
    },

    /**
     * 渲染Markdown内容
     */
    renderMarkdown(content) {
        if (!content) return "";
        
        // 处理图片MD5码
        let processedContent = content.replace(/!\[.*?\]\((md5:.*?)\)/g, (match, md5) => {
            // 假设后端提供了根据MD5获取图片的接口
            const imgUrl = `/api/images/${md5.replace('md5:', '')}`;
            return `<div class="image-container"><img src="${imgUrl}" alt="Image" class="message-image" /><div class="image-actions"><button class="action-btn" data-action="copy">复制</button><button class="action-btn" data-action="save">保存</button><button class="action-btn" data-action="reference">引用</button></div></div>`;
        });
        
        // 处理视频URL
        processedContent = processedContent.replace(/!\[.*?\]\((https?:\/\/.*?\.(mp4|mov|avi|wmv))\)/g, (match, url, ext) => {
            return `<video src="${url}" controls class="message-video" />`;
        });
        
        // 处理普通图片URL
        processedContent = processedContent.replace(/!\[.*?\]\((https?:\/\/.*?\.(jpg|jpeg|png|gif|webp))\)/g, (match, url, ext) => {
            return `<div class="image-container"><img src="${url}" alt="Image" class="message-image" /><div class="image-actions"><button class="action-btn" data-action="copy">复制</button><button class="action-btn" data-action="save">保存</button><button class="action-btn" data-action="reference">引用</button></div></div>`;
        });
        
        return marked.parse(processedContent, {
            highlight: function(code, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value;
                }
                return hljs.highlightAuto(code).value;
            }
        });
    },

        /**
         * 切换消息渲染状态（渲染/原始）
         */

        toggleMessageRender(messageId, contentEl, originalContent) {
            const currentState = this.renderState.get(messageId) || true;
        const newState = !currentState;

        if (newState) {
          contentEl.innerHTML = this.renderMarkdown(originalContent);
          contentEl.classList.add("markdown");
        } else {
          contentEl.textContent = originalContent;
          contentEl.classList.remove("markdown");
        }

        this.renderState.set(messageId, newState);
        // 修复：hljs.highlightElement 是浏览器版正确方法（不是highlightBlock）
        document.querySelectorAll("pre code").forEach(block => {
          hljs.highlightElement(block);
        });
      },

    /**
     * 处理发送消息（核心：Markdown渲染）
     */
    handleSendMessage: preventRepeat(async function() {
        const userMsg = this.els.msgInput.value.trim();
        const { isSending, messageList } = StateManager.getState();
        
        if ((!userMsg && this.uploadedFiles.length === 0) || isSending) return;

        // 1. 保存ID
        this.saveIds();
        const userId = this.els.userIdInput.value.trim();
        const sessionId = this.els.sessionIdInput.value.trim();
        if (!userId || !sessionId) {
            alert("User ID和Session ID不能为空！");
            return;
        }

        // 2. 初始化状态
        StateManager.update({ isSending: true });
        this.els.sendBtn.disabled = true;
        this._toggleSendStopBtn(true);

        // 3. 上传图片（如果有）
        let uploadedImages = [];
        if (this.uploadedFiles.length > 0) {
            uploadedImages = await this.uploadFiles();
        }

        // 4. 构建消息内容，包含上传的图片
        let messageContent = userMsg;
        if (uploadedImages.length > 0) {
            uploadedImages.forEach(imgUrl => {
                messageContent += `\n![Image](${imgUrl})`;
            });
        }

        // 5. 清空输入和上传列表
        this.els.msgInput.value = "";
        this.clearUploadedFiles();

        // 6. 添加用户消息
        const userMessage = {
            sender: "用户",
            content: messageContent,
            time: DateFormat.formatFullTime(new Date()),
            id: `user_${Date.now()}`
        };
        StateManager.addMessage(userMessage);
        this.renderMessages();
        this.autoScrollToBottom();

        // 7. 添加AI中间消息
        const aiPlaceholderId = `ai_${Date.now()}`;
        const placeholderMsg = {
            id: aiPlaceholderId,
            sender: "AI",
            content: "正在思考中...",
            time: DateFormat.formatFullTime(new Date()),
            isMiddle: true
        };
        StateManager.addMessage(placeholderMsg);
        this.renderMessages();
        this.autoScrollToBottom();

        // 8. 生成context
        const contextStr = ChatUtils.generateContextString(messageList);
        // 获取当前选择的语言
        const currentLanguage = this.els.langSelect?.value || localStorage.getItem('currentLanguage') || 'auto-AUTO';
        const minorMode = StateManager.getState().minorMode;
        const personalize = StateManager.getState().personalize;

        let accumulatedContent = "";
        let hasReceived300 = false;

        try {
            await ChatApi.sendStreamMessage(
                messageContent,
                sessionId,
                userId,
                contextStr,
                currentLanguage,
                minorMode,
                personalize,
                // 流式中间过程 (code: 102)
                (chunk) => {
                    console.log('[onChunk] 收到:', chunk);
                    if (chunk.code === 102) {
                        let middleContent = chunk.data || chunk.msg || "正在分析你的请求...";
                        this.updateAiMiddleMessage(aiPlaceholderId, middleContent);
                    }
                },
                // 最终结果 (code: 200)
                (finalData) => {
                    console.log('[onComplete] 收到:', finalData);
                    // 只有在没有收到code:300的情况下才更新最终结果
                    if (!hasReceived300) {
                        let finalContent = "抱歉，我没有理解你的意思。";
                        
                        if (finalData.data) {
                            if (typeof finalData.data === 'string') {
                                // 如果data是字符串，尝试解析为JSON
                                try {
                                    const parsed = JSON.parse(finalData.data);
                                    finalContent = parsed.chat_response || parsed.final_result || finalData.data;
                                } catch (e) {
                                    // 如果不是JSON，直接使用字符串
                                    finalContent = finalData.data;
                                }
                            } else if (typeof finalData.data === 'object') {
                                // 如果data是对象，提取内容
                                finalContent = finalData.data.chat_response || finalData.data.final_result || JSON.stringify(finalData.data);
                            }
                        } else if (finalData.msg) {
                            finalContent = finalData.msg;
                        }
                        
                        // 更新AI消息
                        StateManager.updateMessageContent(aiPlaceholderId, finalContent, false);
                        // 缓存渲染状态（默认渲染）
                        this.renderState.set(aiPlaceholderId, true);
                        
                        StateManager.update({ isSending: false });
                        this._toggleSendStopBtn(false);
                        this.renderMessages();
                        this.autoScrollToBottom();
                        this.els.msgInput.focus();
                    }
                },
                // 流式打字 (code: 300) - 忽略，不渲染
                () => {},
                // 违规提示 (code: 403)
                (forbiddenData) => {
                    let forbiddenContent = "抱歉，用户的输入可能包含违法乱纪行为，很抱歉无法进行回复。";
                    
                    if (forbiddenData.data) {
                        forbiddenContent = forbiddenData.data.chat_response || forbiddenData.data.msg || forbiddenContent;
                    } else if (forbiddenData.msg) {
                        forbiddenContent = forbiddenData.msg;
                    }
                    
                    StateManager.updateMessageContent(aiPlaceholderId, forbiddenContent, false);
                    this.renderState.set(aiPlaceholderId, true);
                    StateManager.update({ isSending: false });
                    this._toggleSendStopBtn(false);
                    this.renderMessages();
                    this.autoScrollToBottom();
                    this.els.msgInput.focus();
                },
                // 错误处理
                (error) => {
                    console.error('[SSE] 收到错误:', error);
                    let errorText = "未知错误";
                    if (typeof error === 'string') {
                        errorText = error;
                    } else if (error.msg) {
                        errorText = error.msg;
                    } else if (error.message) {
                        errorText = error.message;
                    }
                    const errorContent = `❌ 出错了：${errorText}`;
                    StateManager.updateMessageContent(aiPlaceholderId, errorContent, false);
                    StateManager.update({ isSending: false });
                    this._toggleSendStopBtn(false);
                    this.renderMessages();
                    this.autoScrollToBottom();
                    this.els.msgInput.focus();
                }
            );
        } catch (error) {
            console.error("发送消息失败：", error);
            const errorContent = "🌐 网络错误，无法连接到规划器后端！";
            StateManager.updateMessageContent(aiPlaceholderId, errorContent, false);
            StateManager.update({ isSending: false });
            this._toggleSendStopBtn(false);
            this.renderMessages();
            this.autoScrollToBottom();
            this.els.msgInput.focus();
        }
    }, AppConfig.DEBOUNCE_TIME),

    /**
     * 上传文件
     */
    async uploadFiles() {
        const uploadedUrls = [];
        const { userId, sessionId } = StateManager.getState();
        
        for (const file of this.uploadedFiles) {
            try {
                // 使用ChatApi上传文件
                const imgUrl = await ChatApi.uploadFile(file, userId, sessionId);
                uploadedUrls.push(imgUrl);
            } catch (error) {
                console.error("上传文件失败：", error);
                // 如果上传失败，使用本地文件URL作为 fallback
                const reader = new FileReader();
                reader.readAsDataURL(file);
                await new Promise(resolve => {
                    reader.onload = () => {
                        uploadedUrls.push(reader.result);
                        resolve();
                    };
                });
            }
        }
        
        return uploadedUrls;
    },

    /**
     * 清空上传文件
     */
    clearUploadedFiles() {
        // 清空上传文件列表
        this.uploadedFiles = [];
        
        // 清空预览
        this.els.uploadPreview.innerHTML = "";
        
        // 更新发送按钮状态
        this.handleInputChange();
    },

    /**
     * 处理图片操作（复制、保存、引用）
     */
    handleImageAction(action, imageContainer) {
        const img = imageContainer.querySelector('img');
        if (!img) return;
        
        const imgUrl = img.src;
        
        switch (action) {
            case 'copy':
                // 复制图片URL
                navigator.clipboard.writeText(imgUrl).then(() => {
                    alert('图片URL已复制');
                }).catch(() => {
                    alert('复制失败，请手动复制');
                });
                break;
                
            case 'save':
                // 保存图片
                fetch(imgUrl)
                    .then(response => response.blob())
                    .then(blob => {
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `image_${Date.now()}.${imgUrl.split('.').pop().split('?')[0]}`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                    })
                    .catch(() => {
                        alert('保存失败，可能是跨域问题');
                    });
                break;
                
            case 'reference':
                // 引用图片到输入框
                const markdownImg = `![Image](${imgUrl})`;
                this.els.msgInput.value += (this.els.msgInput.value ? '\n' : '') + markdownImg;
                this.els.msgInput.focus();
                break;
        }
    },

    /**
     * 渲染消息列表（Markdown适配）
     */
    renderMessages() {
        const { messageList } = StateManager.getState();
        
        DomUtils.setStyle(this.els.emptyTip, {
            display: messageList.length > 0 ? "none" : "flex"
        });

        this.els.messageContainer.innerHTML = "";
        if (messageList.length === 0) {
            this.els.messageContainer.appendChild(this.els.emptyTip);
            return;
        }

        const groupedMessages = this.groupMessagesByHour(messageList);

        groupedMessages.forEach(group => {
            const timeGroup = DomUtils.createEl("div", { className: "time-group" });
            timeGroup.innerHTML = `<span>${group.time}</span>`;
            this.els.messageContainer.appendChild(timeGroup);

            group.messages.forEach(msg => {
                const messageEl = this.createMessageElement(msg);
                this.els.messageContainer.appendChild(messageEl);
            });
        });

        this.autoScrollToBottom();
    },

    /**
     * 按小时分组消息
     */
    groupMessagesByHour(messages) {
        if (!messages.length) return [];

        const groups = [];
        let currentGroup = { time: "", messages: [] };

        messages.forEach(msg => {
            const msgTime = new Date(msg.time);
            const groupTime = DateFormat.formatGroupTime(msgTime);

            if (currentGroup.time !== groupTime) {
                if (currentGroup.messages.length) groups.push(currentGroup);
                currentGroup = { time: groupTime, messages: [msg] };
            } else {
                currentGroup.messages.push(msg);
            }
        });

        if (currentGroup.messages.length) groups.push(currentGroup);
        return groups;
    },

    /**
     * 创建消息元素（Markdown+切换按钮）
     */
    createMessageElement(msg) {
        const messageDiv = DomUtils.createEl("div", {
            className: `message ${msg.sender === "用户" ? "user-message" : "ai-message"}`
        });

        // 头像
        const avatarText = msg.sender === "用户" ? "👤" : "🤖";
        const avatar = DomUtils.createEl("div", { className: "avatar" }, avatarText);
        
        // 消息包装器
        const wrapper = DomUtils.createEl("div", { className: "message-wrapper" });
        
        // 消息内容
        const contentClass = msg.isMiddle 
            ? "message-content middle" 
            : "message-content";
        const contentEl = DomUtils.createEl("div", { className: contentClass });
        
        // 处理所有消息的Markdown渲染，包括用户消息
        if (!msg.isMiddle) {
            const messageId = msg.id || `${msg.sender}_${Date.now()}`;
            const renderState = this.renderState.get(messageId) || true;
            
            // 设置初始内容
            if (renderState) {
                contentEl.innerHTML = this.renderMarkdown(msg.content);
                contentEl.classList.add("markdown");
            } else {
                contentEl.textContent = msg.content;
            }
        } else {
            // 中间消息使用更好的加载动画
            contentEl.innerHTML = `
                <div class="thinking-animation">
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="text">${msg.content || "正在思考中..."}</span>
                </div>
            `;
        }
        
        // 消息时间
        const time = DomUtils.createEl("div", { className: "message-time" }, DateFormat.formatMessageTime(new Date(msg.time)));

        // 组装基础元素（时间在内容之前）
        wrapper.appendChild(time);
        wrapper.appendChild(contentEl);

        // AI生成标识 - 放在内容下面
        if (msg.sender === "AI" && !msg.isMiddle) {
            const badge = DomUtils.createEl("div", { className: "ai-generated-badge" });
            badge.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>AI生成`;
            wrapper.appendChild(badge);
        }
        
        // 为 AI 消息添加操作按钮（复制、重新生成）
        if (msg.sender === "AI" && !msg.isMiddle) {
            const actionsDiv = DomUtils.createEl("div", { className: "message-actions" });
            
            // 复制按钮
            const copyBtn = DomUtils.createEl("button", { 
                className: "message-action-btn",
                title: "复制到输入框"
            });
            copyBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';
            copyBtn.addEventListener("click", () => {
                this.els.msgInput.value = msg.content;
                this.showToast("已复制到输入框", "success");
            });
            
            // 重新生成按钮
            const regenerateBtn = DomUtils.createEl("button", { 
                className: "message-action-btn",
                title: "重新生成"
            });
            regenerateBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"></path><path d="M1 20v-6h6"></path><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>';
            regenerateBtn.addEventListener("click", () => {
                this.handleRegenerateMessage(msg);
            });
            
            actionsDiv.appendChild(copyBtn);
            actionsDiv.appendChild(regenerateBtn);
            wrapper.appendChild(actionsDiv);
        }
        
        // 为用户消息添加操作按钮（复制、重新发送）
        if (msg.sender === "用户" && !msg.isMiddle) {
            const actionsDiv = DomUtils.createEl("div", { className: "message-actions" });
            
            // 复制按钮
            const copyBtn = DomUtils.createEl("button", { 
                className: "message-action-btn",
                title: "复制到输入框"
            });
            copyBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';
            copyBtn.addEventListener("click", () => {
                this.els.msgInput.value = msg.content;
                this.showToast("已复制到输入框", "success");
            });
            
            // 重新发送按钮
            const resendBtn = DomUtils.createEl("button", { 
                className: "message-action-btn",
                title: "重新发送"
            });
            resendBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"></path><path d="M1 20v-6h6"></path><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>';
            resendBtn.addEventListener("click", () => {
                this.handleResendUserMessage(msg);
            });
            
            actionsDiv.appendChild(copyBtn);
            actionsDiv.appendChild(resendBtn);
            wrapper.appendChild(actionsDiv);
        }
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(wrapper);

        // 代码高亮
        setTimeout(() => {
            document.querySelectorAll("pre code").forEach(block => {
                hljs.highlightElement(block);
            });
        }, 0);

        // 为图片添加点击放大功能
        setTimeout(() => {
            const images = contentEl.querySelectorAll('.message-image');
            images.forEach(img => {
                img.addEventListener('click', () => {
                    this.showImagePreview(img.src);
                });
            });
        }, 0);
        
        return messageDiv;
    },

    /**
     * 显示图片预览
     */
    showImagePreview(imgUrl) {
        // 创建预览容器
        const previewContainer = DomUtils.createEl('div', { className: 'image-preview-container' });
        const previewImage = DomUtils.createEl('img', { 
            className: 'image-preview',
            src: imgUrl 
        });
        const closeBtn = DomUtils.createEl('button', { className: 'image-preview-close' }, '×');
        
        // 组装
        previewContainer.appendChild(previewImage);
        previewContainer.appendChild(closeBtn);
        document.body.appendChild(previewContainer);
        
        // 添加关闭事件
        closeBtn.addEventListener('click', () => {
            document.body.removeChild(previewContainer);
        });
        
        // 点击容器关闭
        previewContainer.addEventListener('click', (e) => {
            if (e.target === previewContainer) {
                document.body.removeChild(previewContainer);
            }
        });
    },

    /**
     * 初始化API配置相关元素
     */
    initApiConfigElements() {
        this.els.apiConfigBtn = DomUtils.getEl("apiConfigBtn");
        this.els.apiConfigModal = DomUtils.getEl("apiConfigModal");
        this.els.closeApiConfigModal = DomUtils.getEl("closeApiConfigModal");
        this.els.apiBaseUrl = DomUtils.getEl("apiBaseUrl");
        this.els.apiPort = DomUtils.getEl("apiPort");
        this.els.saveApiConfig = DomUtils.getEl("saveApiConfig");
        this.els.testApiConnection = DomUtils.getEl("testApiConnection");
    },

    /**
     * 绑定API配置相关事件
     */
    bindApiConfigEvents() {
        // API配置按钮点击事件
        if (this.els.apiConfigBtn) {
            DomUtils.on(this.els.apiConfigBtn, "click", () => {
                this.openApiConfigModal();
            });
        }

        // 关闭模态框事件
        if (this.els.closeApiConfigModal) {
            DomUtils.on(this.els.closeApiConfigModal, "click", () => {
                this.closeApiConfigModal();
            });
        }

        // 点击模态框外部关闭
        if (this.els.apiConfigModal) {
            DomUtils.on(this.els.apiConfigModal, "click", (e) => {
                if (e.target === this.els.apiConfigModal) {
                    this.closeApiConfigModal();
                }
            });
        }

        // 保存配置事件
        if (this.els.saveApiConfig) {
            DomUtils.on(this.els.saveApiConfig, "click", () => {
                this.saveApiConfig();
            });
        }

        // 测试连接事件
        if (this.els.testApiConnection) {
            DomUtils.on(this.els.testApiConnection, "click", () => {
                this.testApiConnection();
            });
        }
    },

    /**
     * 打开API配置模态框
     */
    openApiConfigModal() {
        if (this.els.apiConfigModal) {
            // 填入当前配置
            try {
                const currentUrl = new URL(AppConfig.API_BASE_URL);
                this.els.apiBaseUrl.value = `${currentUrl.protocol}//${currentUrl.hostname}`;
                this.els.apiPort.value = currentUrl.port || '6732';
            } catch (e) {
                // 如果当前URL格式不正确，使用默认值
                this.els.apiBaseUrl.value = 'http://10.3.2.199';
                this.els.apiPort.value = '6732';
            }
            
            this.els.apiConfigModal.classList.add('show');
        }
    },

    /**
     * 关闭API配置模态框
     */
    closeApiConfigModal() {
        if (this.els.apiConfigModal) {
            this.els.apiConfigModal.classList.remove('show');
        }
    },

    /**
     * 保存API配置
     */
    saveApiConfig() {
        const baseUrl = this.els.apiBaseUrl.value.trim();
        const port = this.els.apiPort.value.trim();

        if (!baseUrl) {
            alert('请输入API服务器地址');
            return;
        }

        if (!port) {
            alert('请输入端口号');
            return;
        }

        // 验证URL格式
        try {
            new URL(baseUrl);
        } catch (e) {
            alert('请输入有效的服务器地址');
            return;
        }

        const newApiUrl = `${baseUrl}:${port}`;
        
        // 更新全局配置
        AppConfig.API_BASE_URL = newApiUrl;
        
        // 保存到本地存储
        const config = {
            apiBaseUrl: newApiUrl
        };
        localStorage.setItem(AppConfig.STORAGE_KEYS.API_CONFIG, JSON.stringify(config));
        
        alert('API配置已保存！');
        this.closeApiConfigModal();
    },

    /**
     * 测试API连接
     */
    testApiConnection() {
        const baseUrl = this.els.apiBaseUrl.value.trim();
        const port = this.els.apiPort.value.trim();

        if (!baseUrl) {
            alert('请输入API服务器地址');
            return;
        }

        if (!port) {
            alert('请输入端口号');
            return;
        }

        let testUrl;
        try {
            const urlObj = new URL(baseUrl);
            urlObj.port = port;
            urlObj.pathname = '/health';
            testUrl = urlObj.toString();
        } catch (e) {
            testUrl = `${baseUrl}:${port}/health`;
        }

        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000);

        fetch(testUrl, {
            method: 'GET',
            mode: 'cors',
            signal: controller.signal
        })
        .then(response => {
            clearTimeout(timeout);
            if (response.ok) {
                alert('连接成功！');
            } else {
                alert(`连接失败，状态码: ${response.status}`);
            }
        })
        .catch(error => {
            clearTimeout(timeout);
            console.error('测试连接失败:', error);
            if (error.name === 'AbortError') {
                alert('连接超时（5秒），请检查地址和端口是否正确');
            } else {
                alert(`连接失败：${error.message}`);
            }
        });
    },

    /**
     * 处理 AI 消息重新生成
     */
    async handleRegenerateMessage(aiMsg) {
        // 查找 AI 消息前的最后一条用户消息
        const { messageList } = StateManager.getState();
        const aiMsgIndex = messageList.findIndex(msg => msg.id === aiMsg.id);
        
        if (aiMsgIndex <= 0) {
            this.showToast("找不到对应的用户消息", "error");
            return;
        }
        
        // 向前查找最后一条用户消息
        let lastUserMsg = null;
        for (let i = aiMsgIndex - 1; i >= 0; i--) {
            if (messageList[i].sender === "用户") {
                lastUserMsg = messageList[i];
                break;
            }
        }
        
        if (!lastUserMsg) {
            this.showToast("找不到对应的用户消息", "error");
            return;
        }
        
        // 显示确认对话框
        if (!confirm("确定要重新生成这条回复吗？")) {
            return;
        }
        
        // 删除旧的 AI 消息
        StateManager.deleteMessage(aiMsg.id);
        this.renderMessages();
        
        // 重新发送用户消息
        await this.resendMessage(lastUserMsg);
    },

    /**
     * 处理用户消息重新发送
     */
    async handleResendUserMessage(userMsg) {
        // 显示确认对话框
        if (!confirm("确定要重新发送这条消息吗？")) {
            return;
        }
        
        // 删除这条用户消息及其后的所有 AI 回复
        const { messageList } = StateManager.getState();
        const userMsgIndex = messageList.findIndex(msg => msg.id === userMsg.id);
        
        if (userMsgIndex === -1) {
            this.showToast("消息不存在", "error");
            return;
        }
        
        // 删除该消息及其后的所有消息
        const messagesToDelete = [];
        for (let i = userMsgIndex; i < messageList.length; i++) {
            messagesToDelete.push(messageList[i].id);
        }
        
        messagesToDelete.forEach(msgId => {
            StateManager.deleteMessage(msgId);
        });
        
        this.renderMessages();
        
        // 重新发送用户消息
        await this.resendMessage(userMsg);
    },

    /**
     * 重新发送消息
     */
    async resendMessage(originalMsg) {
        const { userId, sessionId, isSending } = StateManager.getState();
        
        if (isSending) {
            this.showToast("正在发送消息，请稍候", "warning");
            return;
        }
        
        // 保存 ID
        this.saveIds();
        
        // 1. 添加用户消息
        const userMsg = {
            sender: "用户",
            content: originalMsg.content,
            time: new Date().toISOString(),
            id: `user_${Date.now()}`
        };
        StateManager.addMessage(userMsg);
        this.renderMessages();
        this.autoScrollToBottom();
        
        // 2. 清空输入框
        this.els.msgInput.value = "";
        this.uploadedFiles = [];
        this.handleInputChange();
        
        // 3. 添加 AI 占位消息
        const aiPlaceholderId = `ai_${Date.now()}`;
        const placeholderMsg = {
            sender: "AI",
            content: "正在思考中...",
            time: new Date().toISOString(),
            isMiddle: true,
            id: aiPlaceholderId
        };
        StateManager.addMessage(placeholderMsg);
        this.renderMessages();
        this.autoScrollToBottom();
        
        // 4. 生成 context
        const updatedMessageList = StateManager.getState().messageList;
        const contextStr = ChatUtils.generateContextString(updatedMessageList);
        
        // 获取当前选择的语言
        const currentLanguage = this.els.langSelect?.value || localStorage.getItem('currentLanguage') || 'auto-AUTO';
        const minorMode = StateManager.getState().minorMode;
        
        try {
            await ChatApi.sendStreamMessage(
                originalMsg.content,
                sessionId,
                userId,
                contextStr,
                currentLanguage,
                minorMode,
                // 流式中间过程
                (chunk) => {
                    if (chunk.code === 102 && chunk.data) {
                        let middleContent = "";
                        if (typeof chunk.data === "string") {
                            middleContent = chunk.data;
                        } else if (chunk.data.explanation) {
                            middleContent = chunk.data.explanation;
                        } else if (chunk.data.function_calls) {
                            middleContent = `正在执行函数：${chunk.data.function_calls[0]?.name || "处理数据"}`;
                        } else if (chunk.data.next_stage) {
                            middleContent = `正在${chunk.data.next_stage}...`;
                        } else {
                            middleContent = "正在分析你的请求，请稍候...";
                        }
                        this.updateAiMiddleMessage(aiPlaceholderId, middleContent);
                    }
                },
                // 最终结果
                (finalData) => {
                    const finalContent = finalData.data.final_result || "抱歉，我没有理解你的意思。";
                    // 更新 AI 消息
                    StateManager.updateMessageContent(aiPlaceholderId, finalContent, false);
                    // 缓存渲染状态（默认渲染）
                    this.renderState.set(aiPlaceholderId, true);
                    
                    StateManager.update({ isSending: false });
                    this.renderMessages();
                    this.autoScrollToBottom();
                    this.els.msgInput.focus();
                },
                // 错误处理
                (error) => {
                    const errorContent = `❌ 出错了：${error.msg || "未知错误"}`;
                    StateManager.updateMessageContent(aiPlaceholderId, errorContent, false);
                    StateManager.update({ isSending: false });
                    this.renderMessages();
                    this.autoScrollToBottom();
                    this.els.msgInput.focus();
                }
            );
        } catch (error) {
            console.error("重新发送消息失败：", error);
            StateManager.update({ isSending: false });
            this.showToast("发送失败，请重试", "error");
        }
    },

    /**
     * 刷新示例问题
     */
    refreshExampleQuestions() {
        // 定义不同类别的示例问题
        const beautyTopics = [
            "今天心情怎么样？",
            "有什么护肤小技巧可以分享吗？",
            "最近有什么开心的事吗？",
            "需要什么建议呢？",
            "想聊聊时尚穿搭吗？",
            "最近有什么烦恼想倾诉？",
            "想了解哪些护肤小技巧？",
            "有什么好看的电影推荐吗？",
            "最近有什么有趣的事情？",
            "想聊聊天吗？"
        ];
        
        const fashionTopics = [
            "今天穿什么比较好看？",
            "有什么搭配技巧可以分享？",
            "最近流行什么风格？",
            "怎么选择适合自己的服装？",
            "有什么时尚趋势值得关注？",
            "如何打造个人风格？",
            "怎样搭配颜色才好看？",
            "有什么值得购买的品牌推荐？",
            "如何根据身材选择衣服？",
            "有什么配饰搭配技巧？"
        ];
        
        const dailyTopics = [
            "最近生活怎么样？",
            "有什么有趣的事情分享？",
            "今天做了什么有意思的事？",
            "最近有什么新发现？",
            "有什么想聊的话题吗？",
            "今天过得愉快吗？",
            "有什么计划安排？",
            "最近有什么收获？",
            "有什么困惑需要帮助？",
            "想听听你的故事"
        ];
        
        // 合并所有话题
        const allTopics = [...beautyTopics, ...fashionTopics, ...dailyTopics];
        
        // 随机选择5个话题
        const selectedTopics = this.getRandomItems(allTopics, 5);
        
        // 更新示例问题按钮
        if (this.els.examplesContainer) {
            this.els.examplesContainer.innerHTML = '';
            
            selectedTopics.forEach(question => {
                const button = document.createElement('button');
                button.className = 'example-btn';
                button.setAttribute('data-question', question);
                button.textContent = question;
                this.els.examplesContainer.appendChild(button);
            });
        }
    },
    
    /**
     * 从数组中随机选择指定数量的项目
     */
    getRandomItems(array, count) {
        const shuffled = [...array].sort(() => 0.5 - Math.random());
        return shuffled.slice(0, count);
    }
};

// 页面加载完成后初始化
window.addEventListener("DOMContentLoaded", () => {
    LoginView.init();
    ChatView.init();
});


// 补充StateManager方法
if (!StateManager.updateMessageContent) {
    StateManager.updateMessageContent = function(messageId, content, isMiddle) {
        const messageList = this.getState().messageList;
        const msgIndex = messageList.findIndex(msg => msg.id === messageId);
        if (msgIndex !== -1) {
            messageList[msgIndex].content = content;
            messageList[msgIndex].isMiddle = isMiddle;
            this.update({ messageList });
        }
    };
}