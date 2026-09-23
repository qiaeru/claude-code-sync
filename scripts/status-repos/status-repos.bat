@echo off
setlocal enabledelayedexpansion
REM Shows the Git status of every repo in the folder that holds this claude-code-sync
REM checkout (or in the folder given as the first argument): branch, working-tree
REM state, and how far ahead/behind its upstream each one is. Read-only. See the README.
REM
REM Ahead/behind is measured against the last fetched state, so it stays offline and
REM fast; run update-repos (or git fetch) first to refresh it. The hosting checkout
REM is skipped, like update-repos.

set "RC=0"
where git >nul 2>nul || (echo git is not on your PATH.& set "RC=1" & goto :end)

if "%~1"=="" (
    pushd "%~dp0..\..\.." || goto :end
) else (
    pushd "%~1" 2>nul || (echo Folder not found: %~1& set "RC=1" & goto :end)
)
set "ROOT=%CD%"

pushd "%~dp0..\.."
set "SELF=%CD%"
popd

echo Status in %ROOT%
echo.

set /a attention=0
for /d %%d in ("%ROOT%\*") do (
    if exist "%%d\.git" if /i not "%%~fd"=="%SELF%" (
        call :status "%%d"
        if errorlevel 1 set /a attention+=1
    )
)

popd

echo.
echo Done. !attention! repo(s) need attention.
REM Non-zero exit when a repo needs attention, like the .sh version.
if !attention! gtr 0 set "RC=1"
goto :end

REM ---- per-repo status; prints one line, returns errorlevel 1 if it needs attention.
:status
setlocal
set "repo=%~1"
set "name=%~nx1"

REM symbolic-ref also names the branch of a repo with no commit yet.
set "branch="
for /f "delims=" %%b in ('git -C "%repo%" symbolic-ref -q --short HEAD 2^>nul') do set "branch=%%b"
if not defined branch (
    git -C "%repo%" rev-parse -q --verify HEAD >nul 2>nul && (set "branch=(detached)") || (set "branch=?")
)

set "changes=0"
for /f %%c in ('git -C "%repo%" status --porcelain 2^>nul ^| find /c /v ""') do set "changes=%%c"
if "%changes%"=="0" (set "state=clean") else (set "state=%changes% changed")

set "ahead=0"
set "behind=0"
set "hasup="
for /f "tokens=1,2" %%a in ('git -C "%repo%" rev-list --left-right --count @{upstream}...HEAD 2^>nul') do (
    set "behind=%%a" & set "ahead=%%b" & set "hasup=1"
)
if not defined hasup (
    set "sync=no upstream"
) else (
    set "sync=up to date"
    if not "%ahead%"=="0" if "%behind%"=="0"     set "sync=ahead %ahead%"
    if "%ahead%"=="0"     if not "%behind%"=="0" set "sync=behind %behind%"
    if not "%ahead%"=="0" if not "%behind%"=="0" set "sync=ahead %ahead%, behind %behind%"
)

REM Pad the first three fields into columns (no printf in batch).
set "c1=%name%                          "
set "c2=%branch%                          "
set "c3=%state%                          "
echo %c1:~0,22% %c2:~0,18% %c3:~0,14% %sync%

set "rc=0"
if not "%changes%"=="0" set "rc=1"
if not "%ahead%"=="0" set "rc=1"
if not "%behind%"=="0" set "rc=1"
endlocal & exit /b %rc%

:end
REM The pause keeps a double-clicked window open; the exit code still follows.
pause
exit /b %RC%
