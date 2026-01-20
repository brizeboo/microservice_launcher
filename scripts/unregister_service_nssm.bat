@echo off
cd /d "%~dp0"
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -Command "Start-Process '%~0' -Verb RunAs"
    exit
)
set NSSM_PATH=
if exist "%~dp0\nssm.exe" set NSSM_PATH="%~dp0\nssm.exe"
if exist "%~dp0\vendor\nssm\nssm.exe" set NSSM_PATH="%~dp0\vendor\nssm\nssm.exe"
if "%NSSM_PATH%"=="" set NSSM_PATH="nssm"
%NSSM_PATH% stop MicroserviceLauncher
%NSSM_PATH% remove MicroserviceLauncher confirm
echo Service removed.
pause
