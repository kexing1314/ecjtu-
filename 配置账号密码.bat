@echo off
echo ============ 首次配置：输入学号、密码、运营商 ============
echo 注意：输密码时屏幕不会显示任何字符，这是正常的，输完直接回车
echo.
where python >nul 2>nul && (python "%~dp0autologin.py" --setup) || (py "%~dp0autologin.py" --setup)
echo.
pause
