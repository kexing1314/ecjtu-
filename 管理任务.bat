@echo off
setlocal
set PY=
where python >nul 2>nul && set PY=python
if not defined PY (where py >nul 2>nul && set PY=py)
if not defined PY (
    echo 未检测到 Python，请先安装: https://www.python.org/downloads/
    echo 安装时务必勾选 "Add Python to PATH"
    pause
    exit /b
)

:menu
cls
echo ============================================
echo   ECJTU 校园网自动登录 - 计划任务管理
echo ============================================
echo   [1] 安装自动登录（自动适配本机路径）
echo   [2] 卸载自动登录（删除计划任务）
echo   [3] 查看任务状态
echo   [0] 退出
echo.
set /p c=请输入数字后回车:
if "%c%"=="1" %PY% "%~dp0install_task.py"
if "%c%"=="2" %PY% "%~dp0install_task.py" --remove
if "%c%"=="3" %PY% "%~dp0install_task.py" --query
if "%c%"=="0" exit /b
echo.
pause
goto menu
