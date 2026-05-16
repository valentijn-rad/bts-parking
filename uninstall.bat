@echo off
setlocal
set "TASK_NAME=BTS Parking Checker"

schtasks /delete /tn "%TASK_NAME%" /f
if errorlevel 1 (
    echo Could not delete the task (it may not exist).
) else (
    echo Scheduled task "%TASK_NAME%" removed. The checker will no longer run.
)
pause
