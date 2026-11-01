@echo off
REM claude-animated-pet uninstaller.
REM Run this from inside the cloned repo folder.
REM It always runs as administrator, because deleting the old
REM Scheduled Task (if present) needs admin rights.
REM
REM What it does, in order:
REM  1. Deletes the Startup shortcut ClaudeAnimatedPet.vbs
REM  2. Deletes the old Scheduled Task ClaudeAnimatedPet, if present
REM  3. Tries to stop the running pet process, best effort only
REM  4. Asks: delete the project files too? Y = delete, N = keep
REM     Y deletes ONLY the project files listed below, in this
REM     folder. Any other file in this folder is left untouched.
REM     N keeps all project files, so you can run this again later.
REM  5. Prints thank you, waits for a key, then closes the terminal.
REM     In the delete case, uninstall.bat deletes itself as
REM     the last line after the key press. The folder itself
REM     stays if your other files were in it, as intended.

REM Check for admin rights. "net session" only succeeds when elevated.
net session >nul 2>&1
if %ERRORLEVEL% EQU 0 goto :gotAdmin
echo.
echo This uninstaller needs administrator rights to remove the old task.
echo A Windows permission prompt will appear - click Yes to continue.
echo If you click No, the uninstaller will exit without changing anything.
echo Set UAC = CreateObject^("Shell.Application"^) > "%TEMP%\claude-pet-uninstall-getadmin.vbs"
echo UAC.ShellExecute "cmd.exe", "/c ""%~f0""", "", "runas", 1 >> "%TEMP%\claude-pet-uninstall-getadmin.vbs"
"%TEMP%\claude-pet-uninstall-getadmin.vbs"
exit /b

:gotAdmin
if exist "%TEMP%\claude-pet-uninstall-getadmin.vbs" del "%TEMP%\claude-pet-uninstall-getadmin.vbs"
REM An elevated command prompt starts in System32, so go back to the
REM folder this script lives in before doing anything else.
cd /d "%~dp0"

setlocal
set INSTALL_DIR=%~dp0
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set VBS_PATH=%STARTUP_DIR%\ClaudeAnimatedPet.vbs
set TASK_NAME=ClaudeAnimatedPet

echo Uninstalling claude-animated-pet...
echo.

REM 1. Startup shortcut
if exist "%VBS_PATH%" (
    del "%VBS_PATH%"
    echo Startup shortcut deleted: %VBS_PATH%
) else (
    echo No Startup shortcut found at %VBS_PATH%
)

REM 2. Old Scheduled Task, if present
schtasks /Delete /F /TN "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Old Scheduled Task deleted: %TASK_NAME%
) else (
    echo No old Scheduled Task to delete, or it was already gone.
)

REM 3. Stop the running pet, best effort only. Only processes whose
REM command line contains pet.py are stopped, other Python apps are
REM left alone. If this fails, just end the pet in Task Manager or
REM reboot, it will not autostart again after step 1 and 2.
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*pet.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } } catch { }" >nul 2>&1
echo Pet autostart removed. If the pet is still on screen, end it in Task Manager or reboot, it will not come back on login.
echo.

:ask
set /p DELETE_FILES=Do you want to DELETE the project files too? (y/n) [Y = delete, N = keep]:
if /i "%DELETE_FILES%"=="Y" goto :delete_files
if /i "%DELETE_FILES%"=="N" goto :keep_files
echo Please press Y or N.
goto :ask

:delete_files
echo.
echo Deleting ONLY project files in %INSTALL_DIR%
echo Any other file in this folder will be left untouched.
REM Folders, project only
if exist "%INSTALL_DIR%src" rd /s /q "%INSTALL_DIR%src"
if exist "%INSTALL_DIR%assets" rd /s /q "%INSTALL_DIR%assets"
if exist "%INSTALL_DIR%.git" rd /s /q "%INSTALL_DIR%.git"
REM Files, project only
if exist "%INSTALL_DIR%gen_sprites.py" del /q "%INSTALL_DIR%gen_sprites.py"
if exist "%INSTALL_DIR%gen_sprites_mascot.py" del /q "%INSTALL_DIR%gen_sprites_mascot.py"
if exist "%INSTALL_DIR%install.bat" del /q "%INSTALL_DIR%install.bat"
if exist "%INSTALL_DIR%run_pet.bat" del /q "%INSTALL_DIR%run_pet.bat"
if exist "%INSTALL_DIR%requirements.txt" del /q "%INSTALL_DIR%requirements.txt"
if exist "%INSTALL_DIR%LICENSE" del /q "%INSTALL_DIR%LICENSE"
if exist "%INSTALL_DIR%ASSETS-LICENSE.md" del /q "%INSTALL_DIR%ASSETS-LICENSE.md"
if exist "%INSTALL_DIR%README.md" del /q "%INSTALL_DIR%README.md"
if exist "%INSTALL_DIR%.gitignore" del /q "%INSTALL_DIR%.gitignore"
if exist "%INSTALL_DIR%pet_config.json" del /q "%INSTALL_DIR%pet_config.json"
echo Project files deleted.
goto :thankyou_delete

:keep_files
echo.
echo Keeping project files in %INSTALL_DIR%
echo You can run uninstall.bat again later to delete them.
goto :thankyou_keep

:thankyou_keep
echo.
echo thank you for using my project - Chaitany
echo.
pause
exit /b

:thankyou_delete
echo.
echo thank you for using my project - Chaitany
echo.
pause
REM Delete this uninstaller itself as the very last line.
REM After this, the folder will be empty if no other files were
REM in it, or it will still contain your other files, as intended.
del "%~f0"
