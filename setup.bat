@echo off
setlocal

REM ===== BTS Parking Checker - setup =====
REM Registers a Windows Scheduled Task that runs checker.py every 15 minutes.

set "SCRIPT_DIR=%~dp0"
set "TASK_NAME=BTS Parking Checker"

echo.
echo Project folder: %SCRIPT_DIR%
echo.

REM --- Locate pythonw.exe (runs with no console window) ---
for /f "delims=" %%i in ('where pythonw 2^>nul') do (
    set "PYW=%%i"
    goto :found
)
echo ERROR: pythonw.exe not found on PATH.
echo Install Python or add it to PATH, then re-run setup.bat.
pause
exit /b 1

:found
echo Using Python: %PYW%

REM --- Check config.json exists ---
if not exist "%SCRIPT_DIR%config.json" (
    echo.
    echo WARNING: config.json not found.
    echo Copy config.example.json to config.json and fill in your Gmail
    echo address and 16-character App Password before the checker can email you.
    echo.
)

REM --- Create / replace the scheduled task: every 15 min, 24/7 ---
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "\"%PYW%\" \"%SCRIPT_DIR%checker.py\"" ^
    /sc minute ^
    /mo 15 ^
    /f

if errorlevel 1 (
    echo.
    echo ERROR: Failed to create the scheduled task.
    pause
    exit /b 1
)

echo.
echo Scheduled task "%TASK_NAME%" created: runs every 15 minutes.
echo Running it once now as a test...
echo.
schtasks /run /tn "%TASK_NAME%"

echo.
echo Done. Check checker.log in this folder in a moment to confirm it ran.
echo To stop it later, run uninstall.bat.
pause
