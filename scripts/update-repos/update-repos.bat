@echo off
setlocal enabledelayedexpansion
REM Fast-forwards every Git repo in the folder that holds this claude-code-sync
REM checkout (or in the folder given as the first argument). See the README to run it.
REM
REM Why fast-forward only: a repo with unpushed or diverged commits is reported and
REM left untouched instead of silently merged. The hosting checkout is skipped too.

where git >nul 2>nul || (echo git is not on your PATH.& goto :end)

if "%~1"=="" (
    pushd "%~dp0..\..\.." || goto :end
) else (
    pushd "%~1" 2>nul || (echo Folder not found: %~1& goto :end)
)
set "ROOT=%CD%"

pushd "%~dp0..\.."
set "SELF=%CD%"
popd

echo Updating repos in %ROOT%
echo.

set /a ok=0
set /a attention=0

for /d %%d in ("%ROOT%\*") do (
    if exist "%%d\.git" if /i not "%%~fd"=="%SELF%" (
        echo === %%~nxd ===
        git -C "%%d" pull --ff-only
        if errorlevel 1 (
            echo !! %%~nxd left untouched ^(fast-forward not possible^)
            set /a attention+=1
        ) else (
            set /a ok+=1
        )
    )
)

popd

echo.
echo Done. !ok! ok, !attention! need attention.

:end
pause
