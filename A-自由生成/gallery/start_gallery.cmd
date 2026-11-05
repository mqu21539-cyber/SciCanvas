@echo off
chcp 65001 >nul
setlocal EnableExtensions
title SciCanvas Gallery Launcher

set "PORT=8080"
set "HERE=%~dp0"
set "URL=http://127.0.0.1:%PORT%/index.html"

rem 1) 端口已在监听：说明服务已起，直接开浏览器，不重复启动
netstat -ano | findstr /C:":%PORT% " | findstr /C:"LISTENING" >nul 2>nul
if not errorlevel 1 (
  echo [gallery] %PORT% 端口已在监听，直接打开 %URL%
  start "" "%URL%"
  goto :done
)

rem 2) 选 Python：系统 PATH 优先，回落到 SciCanvas 后端 venv
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY set "PY=%HERE%..\backend\.venv\Scripts\python.exe"
if /i not "%PY%"=="python" if not exist "%PY%" (
  echo [gallery] 找不到 Python。请安装 Python 3，或改本脚本里的 PY 变量。
  pause
  exit /b 1
)

echo [gallery] 用 %PY% 在 127.0.0.1:%PORT% 提供 %HERE%
start "SciCanvas Gallery Server" /min "%PY%" -m http.server %PORT% --bind 127.0.0.1 --directory "%HERE%."

rem 3) 等端口就绪（最多约 8 秒；用 ping 计时，避免依赖控制台输入）
for /l %%i in (1,1,16) do (
  ping -n 2 127.0.0.1 >nul
  netstat -ano | findstr /C:":%PORT% " | findstr /C:"LISTENING" >nul 2>nul && goto :open
)
echo [gallery] 服务没起来。看看标题为 "SciCanvas Gallery Server" 的最小化窗口里的报错。
pause
exit /b 1

:open
start "" "%URL%"
echo [gallery] 已打开 %URL%
echo [gallery] 停止服务：双击 stop_gallery.cmd，或关闭 "SciCanvas Gallery Server" 窗口。

:done
ping -n 4 127.0.0.1 >nul
endlocal