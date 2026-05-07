/**
 * Developer: 马赫·马智勇
 * Position: 大模型算法工程师
 * Created: 2026-04-16
 * Copyright (c) 2026. All rights reserved.
 */
/**
 * 防抖函数
 * @param {Function} func 要防抖的函数
 * @param {number} wait 防抖时间（ms）
 * @returns {Function} 防抖后的函数
 */
function debounce(func, wait) {
    let timeout = null;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            func.apply(this, args);
        }, wait);
    };
}

/**
 * 简易的防重复执行工具（基于时间戳）
 * @param {Function} func 要执行的函数
 * @param {number} interval 间隔时间（ms）
 * @returns {Function} 包装后的函数
 */
function preventRepeat(func, interval) {
    let lastExecuteTime = 0;
    return function(...args) {
        const now = Date.now();
        if (now - lastExecuteTime >= interval) {
            lastExecuteTime = now;
            return func.apply(this, args);
        }
    };
}