@echo off
where python >nul 2>nul && (python "%~dp0autologin.py") || (py "%~dp0autologin.py")
echo.
pause
