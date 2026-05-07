/**
 * Developer: 马赫·马智勇
 * Position: 大模型算法工程师
 * Created: 2026-04-16
 * Copyright (c) 2026. All rights reserved.
 */
/**
 * DOM操作工具类
 * 封装常用的DOM操作，减少重复代码
 */
const DomUtils = {
    /**
     * 获取DOM元素（简化document.getElementById）
     * @param {string} id 元素ID
     * @returns {HTMLElement|null} DOM元素
     */
    getEl(id) {
        return document.getElementById(id);
    },

    /**
     * 给元素添加事件监听
     * @param {HTMLElement} el DOM元素
     * @param {string} event 事件名
     * @param {Function} handler 事件处理函数
     */
    on(el, event, handler) {
        if (el && event && handler) {
            el.addEventListener(event, handler);
        }
    },

    /**
     * 移除元素事件监听
     * @param {HTMLElement} el DOM元素
     * @param {string} event 事件名
     * @param {Function} handler 事件处理函数
     */
    off(el, event, handler) {
        if (el && event && handler) {
            el.removeEventListener(event, handler);
        }
    },

    /**
     * 设置元素样式
     * @param {HTMLElement} el DOM元素
     * @param {Object} styles 样式对象
     */
    setStyle(el, styles) {
        if (!el || !styles) return;
        Object.keys(styles).forEach(key => {
            el.style[key] = styles[key];
        });
    },

    /**
     * 滚动元素到底部
     * @param {HTMLElement} el DOM元素
     */
    scrollToBottom(el) {
        if (el) {
            el.scrollTop = el.scrollHeight;
        }
    },

    /**
     * 创建DOM元素
     * @param {string} tag 标签名
     * @param {Object} attrs 属性对象
     * @param {string} content 内容（可选）
     * @returns {HTMLElement} 新创建的元素
     */
    createEl(tag, attrs = {}, content = "") {
        const el = document.createElement(tag);
        // 设置属性
        Object.keys(attrs).forEach(key => {
            if (key === "className") {
                el.className = attrs[key];
            } else {
                el.setAttribute(key, attrs[key]);
            }
        });
        // 设置内容
        if (content) {
            el.textContent = content;
        }
        return el;
    }
};