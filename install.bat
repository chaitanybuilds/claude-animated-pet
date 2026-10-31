@echo off
REM claude-animated-pet installer - registers the pet to auto-start at Windows login.
REM Run this from inside the cloned repo folder.

setlocal
set INSTALL_DIR=%~dp0
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set VBS_PATH=%STARTUP_DIR%\ClaudeAnimatedPet.vbs
set TASK_NAME=ClaudeAnimatedPet

echo Installing Python dependencies...
pip install --break-system-packages -r "%INSTALL_DIR%requirements.txt"
if %ERRORLEVEL% NEQ 0 (
    pip install -r "%INSTALL_DIR%requirements.txt"
)

REM Remove any old-style Startup-folder shortcut from a previous install.
REM Windows deliberately staggers/delays apps launched from that folder by
REM several seconds on every login (its built-in "startup app delay") -
REM that's the 10-15s lag. A Scheduled Task fires immediately on logon
REM instead, so we use that now.
if exist "%VBS_PATH%" del "%VBS_PATH%"

echo Registering a Scheduled Task to launch at logon (skips the Startup-folder delay)...
schtasks /Create /F /SC ONLOGON /RL HIGHEST /IT /TN "%TASK_NAME%" /TR "pythonw.exe \"%INSTALL_DIR%src\pet.py\""
if %ERRORLEVEL% NEQ 0 (
    echo Scheduled Task creation failed - falling back to the Startup-folder method.
    (
    echo Set WshShell = CreateObject^("WScript.Shell"^)
    echo WshShell.CurrentDirectory = "%INSTALL_DIR%"
    echo WshShell.Run "pythonw ""%INSTALL_DIR%src\pet.py""", 0, False
    ) > "%VBS_PATH%"
)

echo.
echo Done! claude-animated-pet will now launch automatically every time you log in,
echo right away instead of 10-15s late.
echo To start it right now without rebooting, double-click run_pet.bat.
echo.
pause
