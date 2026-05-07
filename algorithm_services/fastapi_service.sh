#!/bin/bash
# Algorithm Service 管理脚本（systemd 守护进程 + debug 调试模式）
# install/start/stop/restart/status/uninstall 使用 systemd 守护进程
# debug 使用前台模式（实时日志 + 热重载）

SERVICE_NAME="yisia-algorithm"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PROJECT_DIR=/root/YISIA_Algorithm/algorithm_services
VENV_DIR=/root/YISIA_Algorithm/venv
PYTHON_BIN=${VENV_DIR}/bin/python
HOST=0.0.0.0
PORT=6732
LOG_DIR=${PROJECT_DIR}/logs

# 检查是否 root（debug 模式除外）
if [ "$1" != "debug" ] && [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用 root 权限运行：sudo $0 $1"
    exit 1
fi

# 安装 systemd 服务
install() {
    if [ ! -f "${PROJECT_DIR}/main.py" ]; then
        echo "❌ 项目目录不存在：${PROJECT_DIR}"
        exit 1
    fi

    mkdir -p ${LOG_DIR}

    echo "📝 生成 systemd 服务文件..."
    cat > ${SERVICE_FILE} << EOF
[Unit]
Description=YISIA Algorithm Service
After=network.target

[Service]
Type=simple
WorkingDirectory=${PROJECT_DIR}
Environment=PYTHONPATH=/root/YISIA_Algorithm
ExecStart=${PYTHON_BIN} -m uvicorn main:app --host ${HOST} --port ${PORT}
Restart=always
RestartSec=5
StandardOutput=append:${LOG_DIR}/algorithm_service.log
StandardError=append:${LOG_DIR}/algorithm_service_err.log

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
    echo "✅ Algorithm Service 已启动"
}

stop() {
    systemctl stop ${SERVICE_NAME}
    echo "✅ Algorithm Service 已停止"
}

restart() {
    systemctl restart ${SERVICE_NAME}
    echo "✅ Algorithm Service 已重启"
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

# 调试模式 - 前台运行、实时日志、保留--reload热重载
debug() {
    PID=$(lsof -i:${PORT} -t 2>/dev/null)
    if [ -n "${PID}" ]; then
        echo "❌ 端口${PORT}已被占用，PID：${PID}，请先执行 $0 stop 释放端口"
        exit 1
    fi

    source ${VENV_DIR}/bin/activate
    cd ${PROJECT_DIR} || { echo "❌ 项目目录不存在：${PROJECT_DIR}"; exit 1; }
    export PYTHONPATH=/root/YISIA_Algorithm
    echo -e "📌 【调试模式】启动Algorithm Service，特性：\n  1. 前台运行，SSH终端实时查看日志\n  2. 保留--reload，代码修改自动热重载\n  3. 关闭终端/按Ctrl+C即停止服务"
    echo "🔗 访问文档：http://你的LinuxIP:${PORT}/api/docs"
    echo "⚠️  退出调试模式请按：Ctrl + C"
    echo "=============================================================="

    python -m uvicorn main:app --reload --host ${HOST} --port ${PORT}
}

usage() {
    echo "==================== YISIA Algorithm Service ===================="
    echo "使用方法：sudo $0 [install|start|stop|restart|status|uninstall|debug]"
    echo ""
    echo "  install   # 首次安装（生成systemd服务+开机自启）"
    echo "  start     # 启动服务（守护进程）"
    echo "  stop      # 停止服务"
    echo "  restart   # 重启服务"
    echo "  status    # 查看运行状态"
    echo "  uninstall # 卸载服务"
    echo "  debug     # 调试模式（前台运行，不需要sudo）"
    echo "==============================================================="
    exit 1
}

if [ $# -ne 1 ]; then
    usage
fi

case $1 in
    install)   install ;;
    start)     start ;;
    stop)      stop ;;
    restart)   restart ;;
    status)    status ;;
    uninstall) uninstall ;;
    debug)     debug ;;
    *) echo "❌ 无效参数：$1"; usage ;;
esac
