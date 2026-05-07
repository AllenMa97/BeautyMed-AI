@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set PORT=8002

echo ========================================
echo   知识库服务端口清理工具 (Windows)
echo   目标端口: %PORT%
echo ========================================
echo.

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT% "') do (
    set PID=%%a
    goto :found
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%"') do (
    set PID=%%a
    goto :found
)

echo [INFO] 端口 %PORT% 没有被占用，可以直接启动服务。
goto :end

:found
echo [发现] 端口 %PORT% 被进程 PID=!PID! 占用
echo.

for /f "tokens=1" %%b in ('tasklist /FI "PID eq !PID!" /NH 2^>nul') do (
    set PROCESS_NAME=%%b
    goto :show_process
)

:show_process
echo [进程信息]
echo   - 进程名: !PROCESS_NAME!
echo   - PID: !PID!
echo.

taskkill /F /PID !PID! >nul 2>&1

if !errorlevel! equ 0 (
    echo [成功] 已终止进程 !PID!，端口 %PORT% 已释放。
) else (
    echo [失败] 无法终止进程 !PID!，请尝试以管理员身份运行此脚本。
)

:end
echo.
echo ========================================
echo   操作完成
echo ========================================
pause
