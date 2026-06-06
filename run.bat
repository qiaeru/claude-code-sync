@echo off
REM Launch Claude Code Sync: start the local server and open the web UI.
setlocal
cd /d "%~dp0"

REM Prefer the Windows Python launcher (py), fall back to python on PATH.
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo Python 3.11+ is required, but neither py nor python is on your PATH.
    exit /b 1
)

%PY% -m claude_code_sync %*

endlocal
