@echo off
setlocal enabledelayedexpansion
REM Prunes the import backups that claude-code-sync writes to
REM %USERPROFILE%\.claude-code-sync-backups\<timestamp>\, keeping the most recent.
REM Usage: clean-backups.bat [keep]   (keep defaults to 10). See the README.
REM
REM The tool never removes these itself, so they accumulate; this is the housekeeping
REM it deliberately leaves to you. The script lists what it will delete and asks first.

set "BACKUP_ROOT=%USERPROFILE%\.claude-code-sync-backups"
set "KEEP=%~1"
if not defined KEEP set "KEEP=10"

echo %KEEP%| findstr /r "^[0-9][0-9]*$" >nul || (echo keep must be a non-negative integer (got: %KEEP%).& goto :end)

if not exist "%BACKUP_ROOT%\" (
    echo No backups found (%BACKUP_ROOT% does not exist).
    goto :end
)

REM dir /o-n lists newest first (names are timestamps), so entries past KEEP are oldest.
set /a total=0
for /f "delims=" %%g in ('dir /b /ad /o-n "%BACKUP_ROOT%" 2^>nul') do set /a total+=1

set /a to_delete=total-KEEP
if %to_delete% leq 0 (
    echo %total% backup(s) present, keeping %KEEP%. Nothing to prune.
    goto :end
)

echo %total% backup(s) present. These %to_delete% oldest will be removed:
set /a i=0
for /f "delims=" %%g in ('dir /b /ad /o-n "%BACKUP_ROOT%" 2^>nul') do (
    set /a i+=1
    if !i! gtr %KEEP% echo   %%g
)
echo.

set /p "reply=Delete them? [y/N] "
if /i not "%reply%"=="y" if /i not "%reply%"=="yes" (echo Aborted. Nothing deleted.& goto :end)

set /a i=0
for /f "delims=" %%g in ('dir /b /ad /o-n "%BACKUP_ROOT%" 2^>nul') do (
    set /a i+=1
    if !i! gtr %KEEP% rmdir /s /q "%BACKUP_ROOT%\%%g"
)
echo Removed %to_delete% backup(s).

:end
pause
