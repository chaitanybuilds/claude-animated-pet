@echo off
REM claude-animated-pet installer - registers the pet to auto-start at Windows login.
REM Run this from inside the cloned repo folder.
REM
REM Why this asks for administrator rights first:
REM The fast logon task is registered with the highest run level, and
REM Windows refuses that registration from a normal, non-elevated
REM process with "Access is denied". Without admin rights the old
REM installer silently fell back to the Startup folder, which is why
REM the pet then showed up 10-15s late. This version asks for admin
REM once, up front, so the Scheduled Task actually gets created.
REM If you click No on the permission prompt, this installer exits
REM without changing anything - run it again and click Yes to get
REM the fast logon task.

REM Check for admin rights. "net session" only succeeds when elevated.
net session >nul 2>&1
if %ERRORLEVEL% EQU 0 goto :gotAdmin
echo.
echo This installer needs administrator rights to register the fast logon task.
echo A Windows permission prompt will appear - click Yes to continue.
echo If you click No, the installer will exit without registering anything.
echo Set UAC = CreateObject^("Shell.Application"^) > "%TEMP%\claude-pet-getadmin.vbs"
echo UAC.ShellExecute "cmd.exe", "/c ""%~f0""", "", "runas", 1 >> "%TEMP%\claude-pet-getadmin.vbs"
"%TEMP%\claude-pet-getadmin.vbs"
REM Do not delete the helper here - the elevated copy reads it first
REM and deletes it itself, below, so there is no read/delete race.
exit /b

:gotAdmin
if exist "%TEMP%\claude-pet-getadmin.vbs" del "%TEMP%\claude-pet-getadmin.vbs"
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

REM Remove any old-style Startup-folder shortcut from a previous install.
REM Windows deliberately staggers/delays apps launched from that folder by
REM several seconds on every login (its built-in "startup app delay") -
REM that's the 10-15s lag. A Scheduled Task fires immediately on logon
REM instead, so we use that now.
if exist "%VBS_PATH%" del "%VBS_PATH%"

echo Registering a Scheduled Task to launch at logon (skips the Startup-folder delay)...
schtasks /Delete /F /TN "%TASK_NAME%" >nul 2>&1
schtasks /Create /F /SC ONLOGON /RL HIGHEST /IT /TN "%TASK_NAME%" /TR "\"%INSTALL_DIR%run_pet.bat\""
if %ERRORLEVEL% NEQ 0 goto :fallback
REM Verify the task actually exists now that we are elevated. A plain
REM query from a non-elevated prompt cannot see highest-level tasks,
REM which is the confusing "no scheduled tasks at your access level"
REM message - so this check only runs here, in the elevated installer.
schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% NEQ 0 goto :fallback
schtasks /Change /TN "%TASK_NAME%" /ENABLE >nul 2>&1
REM Set Task Scheduler priority to 0 = realtime, so the pet runs first
REM at logon, ahead of normal Startup apps. This is separate from the
REM run level (HIGHEST, admin token) and from the pet's own process
REM priority bump in pet.py, which tries realtime then high then above
REM normal. If PowerShell cannot set it, the task still runs, just at
REM the default priority, so this step is allowed to fail safely.
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $s = Get-ScheduledTask -TaskName '%TASK_NAME%'; $s.Settings.Priority = 0; $s.Settings.StartWhenAvailable = $true; $s.Settings.AllowStartOnBatteries = $true; $s.Settings.DisallowStartIfOnBatteries = $false; Set-ScheduledTask -InputObject $s | Out-Null; echo Task priority set to 0 realtime } catch { echo Task priority could not be set, task will run at default priority }"
echo Scheduled Task created and enabled: %TASK_NAME%, action is run_pet.bat in this folder, priority realtime.
goto :done

:fallback
echo Scheduled Task creation FAILED - falling back to the Startup-folder method. The fast task was NOT created.
echo The pet will still autostart, but about 10-15s late after login.
echo To get the fast launch instead, run install.bat again and click Yes
echo on the administrator permission prompt.
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.CurrentDirectory = "%INSTALL_DIR%"
echo WshShell.Run "pythonw ""%INSTALL_DIR%src\pet.py""", 0, False
) > "%VBS_PATH%"
goto :done

:done
echo.
echo Done! Check above which method was used: Scheduled Task, or Startup-folder fallback.
echo If it was the fallback, the pet will still autostart, but about 10-15s late after login.
echo To start it right now without rebooting, double-click run_pet.bat.
echo.
pause
