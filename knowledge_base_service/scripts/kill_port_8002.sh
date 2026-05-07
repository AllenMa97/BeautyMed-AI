#!/bin/bash

PORT=8002

echo "========================================"
echo "  知识库服务端口清理工具 (Linux/Mac)"
echo "  目标端口: $PORT"
echo "========================================"
echo

if command -v lsof &> /dev/null; then
    PIDS=$(lsof -t -i:$PORT)
elif command -v ss &> /dev/null; then
    PIDS=$(ss -tlnp 2>/dev/null | grep ":$PORT " | awk '{print $7}' | cut -d',' -f2 | cut -d'=' -f2)
elif command -v netstat &> /dev/null; then
    PIDS=$(netstat -tlnp 2>/dev/null | grep ":$PORT " | awk '{print $7}' | cut -d'/' -f1)
else
    echo "[错误] 未找到 lsof、ss 或 netstat 命令"
    exit 1
fi

if [ -z "$PIDS" ]; then
    echo "[INFO] 端口 $PORT 没有被占用，可以直接启动服务。"
    echo
    echo "========================================"
    echo "  操作完成"
    echo "========================================"
    exit 0
fi

for PID in $PIDS; do
    if [ -n "$PID" ]; then
        PROCESS_NAME=$(ps -p $PID -o comm= 2>/dev/null || echo "未知")
        echo "[发现] 端口 $PORT 被进程占用"
        echo "[进程信息]"
        echo "  - 进程名: $PROCESS_NAME"
        echo "  - PID: $PID"
        echo
        
        kill -9 $PID 2>/dev/null
        
        if [ $? -eq 0 ]; then
            echo "[成功] 已终止进程 $PID，端口 $PORT 已释放。"
        else
            echo "[失败] 无法终止进程 $PID，请尝试使用 sudo 运行此脚本。"
        fi
    fi
done

echo
echo "========================================"
echo "  操作完成"
echo "========================================"
