@echo off
REM claude-animated-pet installer - Startup-folder autostart only.
REM Run this from inside the cloned repo folder.
REM
REM No Task Scheduler task is created any more, on purpose.
REM The old task was unreliable on this PC: it was created with
REM SUCCESS, but it did not run after reboot, and the priority
REM step failed with default priority. Startup is simpler and
REM reliable: Windows launches it about 10-15 seconds after login
REM (its built-in startup delay). That delay is accepted here.
REM No administrator rights are needed for Startup, so no UAC
REM prompt is required for this installer.
REM
REM An elevated command prompt starts in System32, so go back to the
REM folder this script lives in before doing anything else.
cd /d "%~dp0"

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

REM Remove the old Task Scheduler task if it still exists, so the
REM pet does not launch twice (once from the task, once from Startup).
REM This delete may fail without admin rights, that is fine, the
REM task will not be recreated by this installer. If a task still
REM shows in Task Scheduler Library after this, delete it once
REM manually from there, then this Startup method alone will run.
schtasks /Delete /F /TN "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Old Scheduled Task removed: %TASK_NAME%
) else (
    echo No old Scheduled Task to remove, or it could not be deleted without admin rights.
)

echo Adding pet to Startup folder, compulsory, not a fallback...
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.CurrentDirectory = "%INSTALL_DIR%"
echo WshShell.Run """%INSTALL_DIR%run_pet.bat""", 0, False
) > "%VBS_PATH%"

if exist "%VBS_PATH%" (
    echo Startup shortcut created: %VBS_PATH%
) else (
    echo ERROR: Startup shortcut could not be created at %VBS_PATH%
    pause
    exit /b 1
)

echo.
echo Done! claude-animated-pet will now launch automatically every time you log in,
echo via the Startup folder, in about 10-15 seconds after login.
echo To start it right now without rebooting, double-click run_pet.bat.
echo.
pause
