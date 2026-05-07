/**
 * Developer: 马赫·马智勇
 * Position: 大模型算法工程师
 * Created: 2026-04-16
 * Copyright (c) 2026. All rights reserved.
 */
const express = require('express');
const path = require('path');
const app = express();

// 从命令行参数获取端口
let PORT = process.env.PORT || 3000;
const args = process.argv.slice(2);
for (let i = 0; i < args.length; i++) {
    if (args[i] === '--port' && i + 1 < args.length) {
        PORT = parseInt(args[i + 1]);
        break;
    }
}

// 设置静态文件目录
app.use('/chat', express.static(path.join(__dirname, '.'), {
    etag: false,
    maxAge: 0,
    setHeaders: (res, filePath) => {
        if (filePath.endsWith('.html')) {
            res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
        } else {
            res.setHeader('Cache-Control', 'no-cache');
        }
    }
}));

// 处理SPA路由 - 将所有路由指向index.html
app.get('/chat*', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`服务器运行在 http://localhost:${PORT}`);
    console.log(`局域网访问地址: http://<your-ip-address>:${PORT}`);
    console.log('按 Ctrl+C 停止服务器');
});