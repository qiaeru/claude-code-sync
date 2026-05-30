@echo off
REM Launch Claude Code Sync: start the local server and open the web UI.
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -m claude_code_sync %*
) else (
    python -m claude_code_sync %*
)

endlocal
