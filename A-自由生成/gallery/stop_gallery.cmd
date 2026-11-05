@echo off
chcp 65001 >nul
setlocal EnableExtensions
title SciCanvas Gallery Stopper

set "PORT=8080"
set "PID="

rem 找出 8080 上监听进程的 PID（netstat -ano 的第 5 列）
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /C:":%PORT% " ^| findstr /C:"LISTENING"') do set "PID=%%p"

if not defined PID (
  echo [gallery] %PORT% 端口没有在监听，服务本来就没起。
  goto :done
)

rem 只结束 python 进程，避免误杀别的程序
tasklist /FI "PID eq %PID%" /NH | findstr /I "python" >nul
if errorlevel 1 (
  echo [gallery] %PORT% 被 PID %PID% 占用，但它不是 python，可能不是本套脚本起的服务。
  echo [gallery] 已中止，没有结束任何进程。
  goto :done
)

echo [gallery] 结束 PID %PID% 及其子进程...
taskkill /PID %PID% /T /F >nul 2>nul

rem 最多等 10 秒确认端口释放（用 ping 计时，避免依赖控制台输入）
for /l %%i in (1,1,10) do (
  netstat -ano | findstr /C:":%PORT% " | findstr /C:"LISTENING" >nul 2>nul || goto :stopped
  ping -n 2 127.0.0.1 >nul
)
echo [gallery] 结束失败，服务仍在监听 %PORT%%，请手动关掉 "SciCanvas Gallery Server" 窗口。
goto :done

:stopped
echo [gallery] 已停止，%PORT% 端口已释放。

:done
ping -n 4 127.0.0.1 >nul
endlocal