@echo off
REM claude-animated-pet installer - registers the pet to auto-start at Windows login.
REM Run this from inside the cloned repo folder.

setlocal
set INSTALL_DIR=%~dp0
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set VBS_PATH=%STARTUP_DIR%\ClaudeAnimatedPet.vbs

echo Installing Python dependencies...
pip install --break-system-packages -r "%INSTALL_DIR%requirements.txt"
if %ERRORLEVEL% NEQ 0 (
    pip install -r "%INSTALL_DIR%requirements.txt"
)

echo Creating startup launcher (silent, no console window)...
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.CurrentDirectory = "%INSTALL_DIR%"
echo WshShell.Run "pythonw ""%INSTALL_DIR%src\pet.py""", 0, False
) > "%VBS_PATH%"

echo.
echo Done! claude-animated-pet will now launch automatically every time you log in.
echo To start it right now without rebooting, double-click:
echo   %VBS_PATH%
echo.
pause
