#!/bin/bash
# Knowledge Base Service 管理脚本（支持start/stop/restart/debug四模式）
# debug模式：前台运行、实时看日志、保留--reload热重载，适配开发调试
# start模式：后台运行、日志重定向、禁用--reload，适配生产环境

# ===================== 核心配置（按需修改）=====================
PROJECT_DIR=/root/YISIA_Algorithm/knowledge_base_service
VENV_DIR=/root/YISIA_Algorithm/venv
HOST=0.0.0.0
PORT=8002
LOG_DIR=${PROJECT_DIR}/logs
LOG_FILE=${LOG_DIR}/knowledge_base_service.log
ERROR_LOG_FILE=${LOG_DIR}/knowledge_base_service_err.log
# =============================================================================

# 激活虚拟环境
activate_venv() {
    if [ -d "${VENV_DIR}/bin" ]; then
        source "${VENV_DIR}/bin/activate"
    else
        echo "❌ 虚拟环境不存在：${VENV_DIR}"
        exit 1
    fi
}

# 检查端口占用并获取PID
get_pid() {
    lsof -i:${PORT} -t
}

# 生产启动：nohup后台运行、日志重定向、禁用--reload
start() {
    PID=$(get_pid)
    if [ -n "${PID}" ]; then
        echo "❌ Knowledge Base Service已在运行，端口${PORT}，PID：${PID}"
        exit 1
    fi

    activate_venv
    cd ${PROJECT_DIR} || { echo "❌ 项目目录不存在：${PROJECT_DIR}"; exit 1; }
    mkdir -p ${LOG_DIR}
    echo "✅ 【生产模式】开始启动Knowledge Base Service，端口：${PORT}"
    echo "📜 日志文件：${LOG_FILE}，错误日志：${ERROR_LOG_FILE}"
    echo "🔗 访问文档：http://你的LinuxIP:${PORT}/docs"

    nohup python -m uvicorn main:app --host ${HOST} --port ${PORT} \
        > ${LOG_FILE} 2> ${ERROR_LOG_FILE} &

    sleep 2
    PID=$(get_pid)
    if [ -n "${PID}" ]; then
        echo "🎉 Knowledge Base Service启动成功，PID：${PID}"
    else
        echo "❌ Knowledge Base Service启动失败，请查看错误日志：${ERROR_LOG_FILE}"
    fi
}

# 停止服务
stop() {
    PID=$(get_pid)
    if [ -z "${PID}" ]; then
        echo "❌ Knowledge Base Service未运行，端口${PORT}无占用"
        exit 1
    fi

    echo "⚡ 正在停止Knowledge Base Service，PID：${PID}"
    kill ${PID}
    sleep 2

    PID=$(get_pid)
    if [ -z "${PID}" ]; then
        echo "✅ Knowledge Base Service已成功停止"
    else
        echo "⚠️  优雅停止失败，强制杀死进程PID：${PID}"
        kill -9 ${PID}
        sleep 1
        PID=$(get_pid)
        [ -z "${PID}" ] && echo "✅ Knowledge Base Service强制停止成功" || echo "❌ 进程杀死失败"
    fi
}

# 重启服务
restart() {
    echo "🔄 正在重启Knowledge Base Service【生产模式】..."
    stop
    start
}

# 调试模式 - 前台运行、实时日志、保留--reload热重载
debug() {
    PID=$(get_pid)
    if [ -n "${PID}" ]; then
        echo "❌ 端口${PORT}已被占用，PID：${PID}，请先执行 $0 stop 释放端口"
        exit 1
    fi

    activate_venv
    cd ${PROJECT_DIR} || { echo "❌ 项目目录不存在：${PROJECT_DIR}"; exit 1; }
    echo -e "📌 【调试模式】启动Knowledge Base Service，特性：\n  1. 前台运行，SSH终端实时查看日志\n  2. 保留--reload，代码修改自动热重载\n  3. 关闭终端/按Ctrl+C即停止服务"
    echo "🔗 访问文档：http://你的LinuxIP:${PORT}/docs"
    echo "⚠️  退出调试模式请按：Ctrl + C"
    echo "=============================================================="

    python -m uvicorn main:app --reload --host ${HOST} --port ${PORT}
}

# 脚本使用说明
usage() {
    echo "==================== Knowledge Base Service 管理脚本 ===================="
    echo "使用方法：$0 [start|stop|restart|debug]"
    echo "模式说明："
    echo "  $0 start   # 生产模式：后台运行、日志重定向、禁用热重载"
    echo "  $0 stop    # 通用停止：终止任意模式的服务进程"
    echo "  $0 restart # 生产重启：先停止再启动生产模式"
    echo "  $0 debug   # 调试模式：前台运行、实时日志、保留热重载"
    echo "================================================================"
    exit 1
}

# 主逻辑
if [ $# -ne 1 ]; then
    usage
fi

case $1 in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    debug)
        debug
        ;;
    *)
        echo "❌ 无效参数：$1"
        usage
        ;;
esac
