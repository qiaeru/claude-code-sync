@echo off
setlocal enabledelayedexpansion
REM Creates an encrypted claude-code-sync archive without prompts and prunes old ones,
REM for scheduled backups (Task Scheduler). Usage: backup-export.bat [out-dir] [keep]
REM (out-dir defaults to %USERPROFILE%\claude-code-sync-archives, keep to 10).
REM
REM The password must come from the CLAUDE_CODE_SYNC_PASSWORD env var, never the
REM command line, so it stays out of history and process listings.
REM
REM Parentheses inside a ( ... ) block are escaped as ^( ^): an unescaped ")"
REM closes the block early and cmd rejects the whole line.

if "%~1"=="" (set "OUT_DIR=%USERPROFILE%\claude-code-sync-archives") else (set "OUT_DIR=%~1")
set "KEEP=%~2"
if not defined KEEP set "KEEP=10"

REM At least 1: the archive just written is always among the kept ones.
echo %KEEP%| findstr /r "^[1-9][0-9]*$" >nul || (echo keep must be a positive integer ^(got: %KEEP%^).& exit /b 1)

if not defined CLAUDE_CODE_SYNC_PASSWORD (
    echo Set CLAUDE_CODE_SYNC_PASSWORD before running ^(the export password^).
    exit /b 1
)

for %%i in ("%~dp0..\..") do set "REPO_DIR=%%~fi"
for %%i in ("%~dp0..\..\..") do set "ROOT=%%~fi"
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%" || exit /b 1
REM Absolute, since the Python fallback runs from the repo folder.
for %%i in ("%OUT_DIR%") do set "OUT_DIR=%%~fi"

REM Prefer the installed CLI; otherwise run the package from the repo via py/python.
set "RUN="
where claude-code-sync >nul 2>nul && set "RUN=claude-code-sync"
if not defined RUN (
    set "PY="
    where py >nul 2>nul && set "PY=py"
    if not defined PY (
        where python >nul 2>nul && set "PY=python"
    )
    if not defined PY (echo Neither the claude-code-sync CLI nor Python is available.& exit /b 1)
    set "RUN=!PY! -m claude_code_sync"
    set "NEED_CD=1"
)

if defined NEED_CD pushd "%REPO_DIR%"
%RUN% export --root "%ROOT%" --scope all --out-dir "%OUT_DIR%" --keep %KEEP%
set "RC=%errorlevel%"
if defined NEED_CD popd
exit /b %RC%
