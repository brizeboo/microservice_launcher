@echo off
cd /d "%~dp0"
set VENV_DIR=..\.venv
set WHEELS_DIR=..\vendor\wheels
set PIP_PROXY_OPTION=
if not "%HTTPS_PROXY%"=="" set PIP_PROXY_OPTION=--proxy "%HTTPS_PROXY%"
if "%PIP_PROXY_OPTION%"=="" if not "%HTTP_PROXY%"=="" set PIP_PROXY_OPTION=--proxy "%HTTP_PROXY%"

echo ==========================================
echo      ServiceLauncher Build Script
echo ==========================================

REM 1. Check/Create Virtual Environment
if not exist %VENV_DIR% (
    echo [INFO] Creating virtual environment...
    python -m venv %VENV_DIR%
) else (
    echo [INFO] Virtual environment found.
)

REM 2. Install Dependencies
echo [INFO] Installing dependencies...
echo [INFO] Using proxy: %PIP_PROXY_OPTION%
if exist %WHEELS_DIR% (
    echo [INFO] Offline mode: %WHEELS_DIR%
    %VENV_DIR%\Scripts\python -m pip install --no-index --find-links %WHEELS_DIR% -r ..\requirements.txt
    %VENV_DIR%\Scripts\python -m pip install --no-index --find-links %WHEELS_DIR% pyinstaller
    %VENV_DIR%\Scripts\python -m pip install --no-index --find-links %WHEELS_DIR% pillow
) else (
    %VENV_DIR%\Scripts\python -m pip install -r ..\requirements.txt %PIP_PROXY_OPTION% --retries 2 --timeout 20
    if errorlevel 1 (
        if exist %WHEELS_DIR% (
            echo [WARN] Network install failed, falling back to offline wheels...
            %VENV_DIR%\Scripts\python -m pip install --no-index --find-links %WHEELS_DIR% -r ..\requirements.txt
        )
    )
    %VENV_DIR%\Scripts\python -m pip install pyinstaller %PIP_PROXY_OPTION% --retries 2 --timeout 20
    if errorlevel 1 (
        if exist %WHEELS_DIR% (
            echo [WARN] Network install failed, falling back to offline wheels...
            %VENV_DIR%\Scripts\python -m pip install --no-index --find-links %WHEELS_DIR% pyinstaller
        )
    )
    %VENV_DIR%\Scripts\python -m pip install pillow %PIP_PROXY_OPTION% --retries 2 --timeout 20
    if errorlevel 1 (
        if exist %WHEELS_DIR% (
            echo [WARN] Network install failed, falling back to offline wheels...
            %VENV_DIR%\Scripts\python -m pip install --no-index --find-links %WHEELS_DIR% pillow
        )
    )
)

REM 3. Clean previous builds
echo [INFO] Cleaning up previous build artifacts...
if exist build rmdir /s /q build
REM if exist dist rmdir /s /q dist
REM Do not delete spec file as we have customized it
REM if exist *.spec del *.spec

REM 4. Run PyInstaller
echo [INFO] Building executable with PyInstaller...
REM Using existing spec file for advanced configuration (version info, upx disabled)
echo [INFO] Generating ICO from PNG...
%VENV_DIR%\Scripts\python ..\scripts\convert_icon.py
%VENV_DIR%\Scripts\python -m PyInstaller --clean ServiceLauncher.spec

REM 5. Report Success
if exist "dist\MicroServiceLauncher.exe" (
    echo [OUTPUT] %CD%\dist\MicroServiceLauncher.exe
    echo.
    echo [SUCCESS] Build completed successfully!
    if not exist "dist\conf" mkdir "dist\conf"
    if exist "..\services_config.json" copy /Y "..\services_config.json" "dist\conf\services.json" >nul
    if exist "..\services_config.example.json" copy /Y "..\services_config.example.json" "dist\conf\services_config.example.json" >nul
    if exist "nssm.exe" copy /Y "nssm.exe" "dist\nssm.exe" >nul
    if exist "register_service_nssm.bat" copy /Y "register_service_nssm.bat" "dist\register_service_nssm.bat" >nul
    if exist "unregister_service_nssm.bat" copy /Y "unregister_service_nssm.bat" "dist\unregister_service_nssm.bat" >nul
    if exist "..\README.md" copy /Y "..\README.md" "dist\README.md" >nul
    if exist "..\scripts\assets\logo2.png" copy /Y "..\scripts\assets\logo2.png" "dist\app_logo.png" >nul
    if exist "..\scripts\assets\logo2.png" copy /Y "..\scripts\assets\logo2.png" "dist\conf\app_logo.png" >nul
) else (
    echo.
    echo [ERROR] Build failed. Check the output above for errors.
)

echo.
echo push any button exit...
pause >nul
