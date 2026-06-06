@echo off
setlocal enabledelayedexpansion
REM Creates an encrypted claude-code-sync archive without prompts and prunes old ones,
REM for scheduled backups (Task Scheduler). Usage: backup-export.bat [out-dir] [keep]
REM (out-dir defaults to %USERPROFILE%\claude-code-sync-archives, keep to 10).
REM
REM The password must come from the CLAUDE_CODE_SYNC_PASSWORD env var, never the
REM command line, so it stays out of history and process listings.

if "%~1"=="" (set "OUT_DIR=%USERPROFILE%\claude-code-sync-archives") else (set "OUT_DIR=%~1")
set "KEEP=%~2"
if not defined KEEP set "KEEP=10"

echo %KEEP%| findstr /r "^[0-9][0-9]*$" >nul || (echo keep must be a non-negative integer (got: %KEEP%).& goto :end)

if not defined CLAUDE_CODE_SYNC_PASSWORD (
    echo Set CLAUDE_CODE_SYNC_PASSWORD before running (the export password).
    goto :end
)

for %%i in ("%~dp0..\..") do set "REPO_DIR=%%~fi"
for %%i in ("%~dp0..\..\..") do set "ROOT=%%~fi"
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

REM Prefer the installed CLI; otherwise run the package from the repo via py/python.
set "RUN="
where claude-code-sync >nul 2>nul && set "RUN=claude-code-sync export"
if not defined RUN (
    set "PY="
    where py >nul 2>nul && set "PY=py"
    if not defined PY (
        where python >nul 2>nul && set "PY=python"
    )
    if not defined PY (echo Neither the claude-code-sync CLI nor Python is available.& goto :end)
    set "RUN=!PY! -m claude_code_sync export"
    set "NEED_CD=1"
)

if defined NEED_CD pushd "%REPO_DIR%"
%RUN% --root "%ROOT%" --scope all --out-dir "%OUT_DIR%"
if defined NEED_CD popd

REM Prune old archives, keeping the newest KEEP. dir /o-d sorts by modification
REM time (newest first), robust even if the hostname in the names changes.
set /a total=0
for /f "delims=" %%g in ('dir /b /a-d /o-d "%OUT_DIR%\claude-code-sync-*.zip" 2^>nul') do set /a total+=1
set /a to_delete=total-KEEP
if %to_delete% lss 0 set /a to_delete=0

set /a i=0
for /f "delims=" %%g in ('dir /b /a-d /o-d "%OUT_DIR%\claude-code-sync-*.zip" 2^>nul') do (
    set /a i+=1
    if !i! gtr %KEEP% del /q "%OUT_DIR%\%%g"
)

echo Archive written to %OUT_DIR%; kept newest %KEEP% (removed %to_delete%).

:end
