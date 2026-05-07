#!/bin/bash
# YISIA Frontend Service 管理脚本（systemd 守护进程）
# 支持 install/start/stop/restart/status/uninstall

SERVICE_NAME="yisia-frontend"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PROJECT_DIR=/root/YISIA_Algorithm/frontend_services
NODE_BIN=$(which node)

# 检查是否 root
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用 root 权限运行：sudo $0 $1"
    exit 1
fi

# 安装 systemd 服务
install() {
    if [ ! -f "${PROJECT_DIR}/server.js" ]; then
        echo "❌ 项目目录不存在：${PROJECT_DIR}"
        exit 1
    fi

    if [ ! -d "${PROJECT_DIR}/node_modules" ]; then
        echo "📦 安装前端依赖..."
        cd ${PROJECT_DIR} && npm install --production
    fi

    echo "📝 生成 systemd 服务文件..."
    cat > ${SERVICE_FILE} << EOF
[Unit]
Description=YISIA Frontend Service
After=network.target

[Service]
Type=simple
WorkingDirectory=${PROJECT_DIR}
ExecStart=${NODE_BIN} server.js
Restart=always
RestartSec=3
StandardOutput=null
StandardError=null
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable ${SERVICE_NAME}
    echo "✅ 服务安装完成（已设置开机自启）"
    echo "💡 启动命令：$0 start"
}

start() {
    if [ ! -f "${SERVICE_FILE}" ]; then
        echo "❌ 服务未安装，请先执行：$0 install"
        exit 1
    fi
    systemctl start ${SERVICE_NAME}
    echo "✅ 前端服务已启动"
}

stop() {
    systemctl stop ${SERVICE_NAME}
    echo "✅ 前端服务已停止"
}

restart() {
    systemctl restart ${SERVICE_NAME}
    echo "✅ 前端服务已重启"
}

status() {
    systemctl status ${SERVICE_NAME} --no-pager
}

uninstall() {
    systemctl stop ${SERVICE_NAME} 2>/dev/null
    systemctl disable ${SERVICE_NAME} 2>/dev/null
    rm -f ${SERVICE_FILE}
    systemctl daemon-reload
    echo "✅ 服务已卸载"
}

usage() {
    echo "==================== YISIA Frontend Service ===================="
    echo "使用方法：sudo $0 [install|start|stop|restart|status|uninstall]"
    echo ""
    echo "  install   # 首次安装（生成systemd服务+开机自启）"
    echo "  start     # 启动服务"
    echo "  stop      # 停止服务"
    echo "  restart   # 重启服务"
    echo "  status    # 查看运行状态"
    echo "  uninstall # 卸载服务（删除开机自启）"
    echo "==============================================================="
    exit 1
}

if [ $# -ne 1 ]; then
    usage
fi

case $1 in
    install)  install ;;
    start)    start ;;
    stop)     stop ;;
    restart)  restart ;;
    status)   status ;;
    uninstall) uninstall ;;
    *) echo "❌ 无效参数：$1"; usage ;;
esac
