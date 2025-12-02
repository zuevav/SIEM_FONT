@echo off
REM =====================================================================
REM SIEM Windows Agent - Build Script
REM =====================================================================
REM
REM Usage:
REM   build.bat              - Build agent executable
REM   build.bat clean        - Clean build artifacts
REM   build.bat install      - Build and install agent as service
REM   build.bat uninstall    - Uninstall agent service
REM
REM Requirements:
REM   - Go 1.21 or later
REM   - Windows 10/11 or Windows Server 2016+
REM   - Administrator privileges (for install/uninstall)
REM
REM =====================================================================

setlocal enabledelayedexpansion

REM Configuration
set AGENT_NAME=siem-agent
set AGENT_VERSION=1.0.0
set OUTPUT_DIR=bin
set OUTPUT_FILE=%OUTPUT_DIR%\%AGENT_NAME%.exe
set CONFIG_FILE=config.yaml

REM Colors (for better output)
set COLOR_GREEN=[92m
set COLOR_YELLOW=[93m
set COLOR_RED=[91m
set COLOR_RESET=[0m

REM Check command
if "%1"=="clean" goto :clean
if "%1"=="install" goto :install
if "%1"=="uninstall" goto :uninstall
if "%1"=="test" goto :test
if "%1"=="" goto :build

echo %COLOR_RED%Unknown command: %1%COLOR_RESET%
echo Usage: build.bat [build^|clean^|install^|uninstall^|test]
exit /b 1

:build
echo %COLOR_GREEN%Building SIEM Windows Agent v%AGENT_VERSION%...%COLOR_RESET%

REM Check if Go is installed
go version >nul 2>&1
if errorlevel 1 (
    echo %COLOR_RED%Error: Go is not installed or not in PATH%COLOR_RESET%
    echo Please install Go 1.21+ from https://golang.org/dl/
    exit /b 1
)

REM Create output directory
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

REM Get dependencies
echo %COLOR_YELLOW%Downloading dependencies...%COLOR_RESET%
go mod download
if errorlevel 1 (
    echo %COLOR_RED%Failed to download dependencies%COLOR_RESET%
    exit /b 1
)

REM Build flags
set LDFLAGS=-s -w -X main.version=%AGENT_VERSION% -X main.buildTime=%date% %time%
set BUILDFLAGS=-trimpath

REM Build the agent
echo %COLOR_YELLOW%Compiling agent...%COLOR_RESET%
go build %BUILDFLAGS% -ldflags="%LDFLAGS%" -o "%OUTPUT_FILE%" main.go
if errorlevel 1 (
    echo %COLOR_RED%Build failed%COLOR_RESET%
    exit /b 1
)

REM Check if config file exists, if not copy example
if not exist "%CONFIG_FILE%" (
    if exist "config.yaml.example" (
        echo %COLOR_YELLOW%Copying config.yaml.example to config.yaml...%COLOR_RESET%
        copy /Y "config.yaml.example" "%CONFIG_FILE%" >nul
    ) else (
        echo %COLOR_YELLOW%Warning: config.yaml.example not found%COLOR_RESET%
    )
)

REM Display file info
for %%I in ("%OUTPUT_FILE%") do set SIZE=%%~zI
set /a SIZE_MB=!SIZE! / 1048576

echo.
echo %COLOR_GREEN%Build successful!%COLOR_RESET%
echo   Executable: %OUTPUT_FILE%
echo   Size: !SIZE_MB! MB
echo   Version: %AGENT_VERSION%
echo.
echo To test the agent:
echo   %OUTPUT_FILE% -console
echo.
echo To install as Windows Service:
echo   %OUTPUT_FILE% -install
echo   sc start siem-agent
echo.
goto :end

:clean
echo %COLOR_YELLOW%Cleaning build artifacts...%COLOR_RESET%

REM Remove binaries
if exist "%OUTPUT_DIR%" (
    rmdir /S /Q "%OUTPUT_DIR%"
    echo Removed %OUTPUT_DIR%
)

REM Remove Go build cache (optional)
go clean -cache -modcache -testcache 2>nul

echo %COLOR_GREEN%Clean complete%COLOR_RESET%
goto :end

:install
echo %COLOR_GREEN%Installing SIEM Windows Agent...%COLOR_RESET%

REM Check for admin privileges
net session >nul 2>&1
if errorlevel 1 (
    echo %COLOR_RED%Error: Administrator privileges required%COLOR_RESET%
    echo Please run this script as Administrator
    exit /b 1
)

REM Build first if executable doesn't exist
if not exist "%OUTPUT_FILE%" (
    echo %COLOR_YELLOW%Agent not built, building now...%COLOR_RESET%
    call :build
    if errorlevel 1 exit /b 1
)

REM Check if config exists
if not exist "%CONFIG_FILE%" (
    echo %COLOR_RED%Error: %CONFIG_FILE% not found%COLOR_RESET%
    echo Please copy config.yaml.example to config.yaml and configure it
    exit /b 1
)

REM Uninstall existing service if present
sc query siem-agent >nul 2>&1
if not errorlevel 1 (
    echo %COLOR_YELLOW%Stopping existing service...%COLOR_RESET%
    sc stop siem-agent >nul 2>&1
    timeout /t 2 /nobreak >nul

    echo %COLOR_YELLOW%Uninstalling existing service...%COLOR_RESET%
    "%OUTPUT_FILE%" -uninstall
    timeout /t 2 /nobreak >nul
)

REM Install service
echo %COLOR_YELLOW%Installing service...%COLOR_RESET%
"%OUTPUT_FILE%" -install
if errorlevel 1 (
    echo %COLOR_RED%Service installation failed%COLOR_RESET%
    exit /b 1
)

REM Start service
echo %COLOR_YELLOW%Starting service...%COLOR_RESET%
sc start siem-agent
if errorlevel 1 (
    echo %COLOR_RED%Failed to start service%COLOR_RESET%
    echo Check logs for details
    exit /b 1
)

timeout /t 2 /nobreak >nul

REM Check service status
sc query siem-agent | find "RUNNING" >nul
if errorlevel 1 (
    echo %COLOR_YELLOW%Warning: Service is not running%COLOR_RESET%
    echo Check Event Viewer or logs for errors
) else (
    echo %COLOR_GREEN%Service installed and started successfully%COLOR_RESET%
)

echo.
echo Service commands:
echo   sc start siem-agent    - Start service
echo   sc stop siem-agent     - Stop service
echo   sc query siem-agent    - Check status
echo.
goto :end

:uninstall
echo %COLOR_YELLOW%Uninstalling SIEM Windows Agent...%COLOR_RESET%

REM Check for admin privileges
net session >nul 2>&1
if errorlevel 1 (
    echo %COLOR_RED%Error: Administrator privileges required%COLOR_RESET%
    exit /b 1
)

REM Check if service exists
sc query siem-agent >nul 2>&1
if errorlevel 1 (
    echo %COLOR_YELLOW%Service is not installed%COLOR_RESET%
    goto :end
)

REM Stop service
echo %COLOR_YELLOW%Stopping service...%COLOR_RESET%
sc stop siem-agent >nul 2>&1
timeout /t 3 /nobreak >nul

REM Uninstall service
if exist "%OUTPUT_FILE%" (
    "%OUTPUT_FILE%" -uninstall
) else (
    echo %COLOR_RED%Warning: Agent executable not found, using sc delete%COLOR_RESET%
    sc delete siem-agent
)

if errorlevel 1 (
    echo %COLOR_RED%Uninstallation failed%COLOR_RESET%
    exit /b 1
)

echo %COLOR_GREEN%Service uninstalled successfully%COLOR_RESET%
goto :end

:test
echo %COLOR_YELLOW%Testing SIEM Windows Agent...%COLOR_RESET%

REM Build first
call :build
if errorlevel 1 exit /b 1

REM Check if config exists
if not exist "%CONFIG_FILE%" (
    echo %COLOR_YELLOW%Warning: %CONFIG_FILE% not found, using defaults%COLOR_RESET%
)

REM Run in console mode for 10 seconds
echo.
echo %COLOR_GREEN%Running agent in console mode for 10 seconds...%COLOR_RESET%
echo Press Ctrl+C to stop manually
echo.

timeout /t 2 /nobreak >nul

start /B "SIEM Agent Test" "%OUTPUT_FILE%" -console
set AGENT_PID=%ERRORLEVEL%

timeout /t 10 /nobreak

REM Kill the process
taskkill /F /IM siem-agent.exe >nul 2>&1

echo.
echo %COLOR_GREEN%Test complete%COLOR_RESET%
echo Check logs for any errors
goto :end

:end
endlocal
exit /b 0
