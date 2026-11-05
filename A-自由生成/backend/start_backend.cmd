@echo off
chcp 65001 >nul
setlocal EnableExtensions
title SciCanvas Backend Launcher

set "PORT=8000"
set "HERE=%~dp0"
set "HEALTH=http://127.0.0.1:%PORT%/api/health"

rem 1) 已在监听就不重复起
netstat -ano | findstr /C:":%PORT% " | findstr /C:"LISTENING" >nul 2>nul
if not errorlevel 1 (
  echo [backend] %PORT% 端口已在监听，直接复用：%HEALTH%
  goto :done
)

rem 2) 选 Python：本目录 venv 优先，回落系统 PATH
set "PY=%HERE%.venv\Scripts\python.exe"
if not exist "%PY%" (
  where python >nul 2>nul && set "PY=python"
)
if /i not "%PY%"=="python" if not exist "%PY%" (
  echo [backend] 找不到 Python。请装 Python 3，或改本脚本里的 PY 变量。
  pause
  exit /b 1
)

echo [backend] 用 %PY% 启动 uvicorn（127.0.0.1:%PORT%）
start "SciCanvas Backend" /min "%PY%" -m uvicorn main:app --host 127.0.0.1 --port %PORT%

rem 3) 等端口就绪（最多约 10 秒，用 ping 计时不依赖控制台输入）
for /l %%i in (1,1,20) do (
  ping -n 2 127.0.0.1 >nul
  netstat -ano | findstr /C:":%PORT% " | findstr /C:"LISTENING" >nul 2>nul && goto :open
)
echo [backend] 没起来。看看标题为 "SciCanvas Backend" 的最小化窗口里的报错。
pause
exit /b 1

:open
echo [backend] 已启动：%HEALTH%
echo [backend] 停止：双击 stop_backend.cmd，或关闭 "SciCanvas Backend" 窗口。

:done
ping -n 4 127.0.0.1 >nul
endlocal