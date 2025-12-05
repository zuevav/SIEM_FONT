<#
.SYNOPSIS
    SIEM System - Automated Installer for Windows
    
.DESCRIPTION
    Click-to-run installation script for Windows with Docker Desktop
    
.EXAMPLE
    # Download and run:
    Invoke-WebRequest -Uri https://raw.githubusercontent.com/YOUR_ORG/SIEM_FONT/main/install.ps1 -OutFile install.ps1
    PowerShell -ExecutionPolicy Bypass -File install.ps1
    
.NOTES
    Requires: Windows 10/11 or Windows Server 2019/2022
    Requires: Administrator privileges
#>

param(
    [string]$InstallPath = "C:\SIEM",
    [string]$GitHubRepo = "zuevav/SIEM_FONT",
    [string]$Branch = "main"
)

#Requires -RunAsAdministrator

# Configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

###############################################################################
# Helper Functions
###############################################################################

function Write-Banner {
    Write-Host ""
    Write-Host "   _____ _____ ______ __  __   _____           _        _ _" -ForegroundColor Cyan
    Write-Host "  / ____|_   _|  ____|  \/  | |_   _|         | |      | | |" -ForegroundColor Cyan
    Write-Host " | (___   | | | |__  | \  / |   | |  _ __  ___| |_ __ _| | | ___ _ __" -ForegroundColor Cyan
    Write-Host "  \___ \  | | |  __| | |\/| |   | | | '_ \/ __| __/ _\` | | |/ _ \ '__|" -ForegroundColor Cyan
    Write-Host "  ____) |_| |_| |____| |  | |  _| |_| | | \__ \ || (_| | | |  __/ |" -ForegroundColor Cyan
    Write-Host " |_____/|_____|______|_|  |_| |_____|_| |_|___/\__\__,_|_|_|\___|_|" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Security Information and Event Management System" -ForegroundColor Green
    Write-Host "Version: 1.0 | Windows Installer" -ForegroundColor Blue
    Write-Host ""
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[✓] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-DockerDesktop {
    Write-Info "Checking Docker Desktop..."
    
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $dockerVersion = docker --version
        Write-Success "Docker found: $dockerVersion"
        return $true
    }
    
    Write-Warning "Docker Desktop not found"
    return $false
}

function Install-DockerDesktop {
    Write-Info "Docker Desktop is required for SIEM"
    Write-Info "Please install Docker Desktop manually:"
    Write-Host "  1. Visit: https://www.docker.com/products/docker-desktop/" -ForegroundColor Cyan
    Write-Host "  2. Download Docker Desktop for Windows" -ForegroundColor Cyan
    Write-Host "  3. Install and restart your computer" -ForegroundColor Cyan
    Write-Host "  4. Run this installer again" -ForegroundColor Cyan
    Write-Host ""
    
    $openBrowser = Read-Host "Open Docker Desktop download page in browser? (Y/n)"
    if ($openBrowser -eq "" -or $openBrowser -eq "y" -or $openBrowser -eq "Y") {
        Start-Process "https://www.docker.com/products/docker-desktop/"
    }
    
    exit 1
}

function Test-Git {
    Write-Info "Checking Git..."
    
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $gitVersion = git --version
        Write-Success "Git found: $gitVersion"
        return $true
    }
    
    Write-Warning "Git not found"
    return $false
}

function Install-Git {
    Write-Info "Installing Git for Windows..."
    
    $gitInstaller = "$env:TEMP\Git-Installer.exe"
    Write-Info "Downloading Git installer..."
    
    Invoke-WebRequest -Uri "https://github.com/git-for-windows/git/releases/latest/download/Git-2.43.0-64-bit.exe" `
        -OutFile $gitInstaller
    
    Write-Info "Running Git installer..."
    Start-Process -FilePath $gitInstaller -ArgumentList "/VERYSILENT /NORESTART" -Wait
    
    Write-Success "Git installed"
    
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Get-SIEMFromGitHub {
    Write-Info "Downloading SIEM from GitHub..."
    
    if (!(Test-Path $InstallPath)) {
        New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
    }
    
    Set-Location $InstallPath
    
    if (Test-Path "$InstallPath\.git") {
        Write-Info "SIEM already exists, updating..."
        git pull origin $Branch
    }
    else {
        Write-Info "Cloning repository..."
        git clone -b $Branch "https://github.com/$GitHubRepo.git" .
    }
    
    Write-Success "SIEM downloaded to $InstallPath"
}

function New-SIEMConfiguration {
    Write-Info "Starting configuration wizard..."
    Write-Host ""
    
    Set-Location $InstallPath
    
    if (Test-Path ".env") {
        Write-Warning "Configuration file (.env) already exists"
        $reconfigure = Read-Host "Do you want to reconfigure? (y/N)"
        if ($reconfigure -ne "y" -and $reconfigure -ne "Y") {
            Write-Info "Keeping existing configuration"
            return
        }
    }
    
    Write-Info "Creating configuration file..."
    
    # Generate secure passwords
    $dbPassword = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    $jwtSecret = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | ForEach-Object {[char]$_})
    
    # Get user input
    Write-Host ""
    Write-Host "=== Admin User ===" -ForegroundColor Blue
    $adminUser = Read-Host "Admin username [admin]"
    if ([string]::IsNullOrEmpty($adminUser)) { $adminUser = "admin" }
    
    $adminPass = Read-Host "Admin password [admin123]" -AsSecureString
    $adminPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminPass)
    )
    if ([string]::IsNullOrEmpty($adminPassPlain)) { $adminPassPlain = "admin123" }
    
    Write-Host ""
    Write-Host "=== Network Configuration ===" -ForegroundColor Blue
    $apiPort = Read-Host "API Port [8000]"
    if ([string]::IsNullOrEmpty($apiPort)) { $apiPort = "8000" }
    
    $frontendPort = Read-Host "Frontend Port [3000]"
    if ([string]::IsNullOrEmpty($frontendPort)) { $frontendPort = "3000" }
    
    Write-Host ""
    Write-Host "=== AI Configuration ===" -ForegroundColor Blue
    Write-Host "Choose AI provider:"
    Write-Host "1) DeepSeek (free, recommended)"
    Write-Host "2) Yandex GPT (requires API key)"
    Write-Host "3) None (skip AI features)"
    $aiChoice = Read-Host "Choice [1]"
    if ([string]::IsNullOrEmpty($aiChoice)) { $aiChoice = "1" }
    
    $aiProvider = "none"
    $aiApiKey = ""
    
    switch ($aiChoice) {
        "1" {
            $aiProvider = "deepseek"
            $aiApiKey = Read-Host "DeepSeek API Key (or press Enter to skip)"
        }
        "2" {
            $aiProvider = "yandex_gpt"
            $aiApiKey = Read-Host "Yandex GPT API Key"
            $yandexFolderId = Read-Host "Yandex GPT Folder ID"
        }
        "3" {
            $aiProvider = "none"
        }
    }
    
    # Create .env file
    $envContent = @"
# SIEM Configuration File
# Generated: $(Get-Date)

# Database
POSTGRES_USER=siem
POSTGRES_PASSWORD=$dbPassword
POSTGRES_DB=siem_db
DATABASE_URL=postgresql://siem:$dbPassword@db:5432/siem_db

# Backend
JWT_SECRET=$jwtSecret
JWT_ALGORITHM=HS256
JWT_EXPIRATION=7200

# Admin User
DEFAULT_ADMIN_USERNAME=$adminUser
DEFAULT_ADMIN_PASSWORD=$adminPassPlain

# AI Configuration
AI_PROVIDER=$aiProvider
"@
    
    if ($aiProvider -eq "deepseek" -and ![string]::IsNullOrEmpty($aiApiKey)) {
        $envContent += "`nDEEPSEEK_API_KEY=$aiApiKey"
    }
    
    if ($aiProvider -eq "yandex_gpt") {
        $envContent += "`nYANDEX_GPT_API_KEY=$aiApiKey"
        $envContent += "`nYANDEX_GPT_FOLDER_ID=$yandexFolderId"
    }
    
    $envContent += @"

# Network
API_PORT=$apiPort
FRONTEND_PORT=$frontendPort

# Logging
LOG_LEVEL=INFO

# Security
CORS_ORIGINS=http://localhost:$frontendPort,http://127.0.0.1:$frontendPort
"@
    
    Set-Content -Path ".env" -Value $envContent
    Write-Success "Configuration saved to .env"
    
    # Store variables for summary
    $script:AdminUser = $adminUser
    $script:AdminPass = $adminPassPlain
    $script:ApiPort = $apiPort
    $script:FrontendPort = $frontendPort
}

function Start-SIEMContainers {
    Write-Info "Building and starting SIEM..."
    
    Set-Location $InstallPath
    
    # Check if docker compose or docker-compose
    $composeCmd = if (docker compose version 2>$null) { "docker compose" } else { "docker-compose" }
    
    Write-Info "Pulling Docker images..."
    Invoke-Expression "$composeCmd pull"
    
    Write-Info "Building SIEM images..."
    Invoke-Expression "$composeCmd build"
    
    Write-Info "Starting services..."
    Invoke-Expression "$composeCmd up -d"
    
    Write-Success "SIEM started"
}

function Wait-ForServices {
    Write-Info "Waiting for services to be ready..."
    
    $maxAttempts = 60
    $attempt = 0
    
    while ($attempt -lt $maxAttempts) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$($script:ApiPort)/health" -UseBasicParsing -TimeoutSec 1
            if ($response.StatusCode -eq 200) {
                Write-Success "Backend is ready"
                return
            }
        }
        catch {
            Write-Host "." -NoNewline
        }
        
        $attempt++
        Start-Sleep -Seconds 2
    }
    
    Write-Host ""
    Write-Warning "Backend did not start in time. Check logs with: docker-compose logs backend"
}

function Test-SIEMHealth {
    Write-Info "Running health checks..."
    
    Set-Location $InstallPath
    
    $composeCmd = if (docker compose version 2>$null) { "docker compose" } else { "docker-compose" }
    
    $services = @("db", "backend", "frontend")
    $allHealthy = $true
    
    foreach ($service in $services) {
        $status = Invoke-Expression "$composeCmd ps $service" | Select-String "Up"
        if ($status) {
            Write-Success "$service is running"
        }
        else {
            Write-Error "$service is not running"
            $allHealthy = $false
        }
    }
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$($script:ApiPort)/health" -UseBasicParsing
        if ($response.Content -like "*healthy*") {
            Write-Success "API health check passed"
        }
    }
    catch {
        Write-Warning "API health check failed (service may still be starting)"
        $allHealthy = $false
    }
    
    return $allHealthy
}

function New-WindowsService {
    Write-Info "Creating Windows scheduled task for auto-start..."
    
    $taskName = "SIEM System"
    $action = New-ScheduledTaskAction -Execute "docker-compose" -Argument "up -d" -WorkingDirectory $InstallPath
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
    
    Write-Success "Scheduled task created for auto-start"
}

function Write-Summary {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║                                                            ║" -ForegroundColor Green
    Write-Host "║  🎉 SIEM Installation Complete!                           ║" -ForegroundColor Green
    Write-Host "║                                                            ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "Installation Directory: " -NoNewline -ForegroundColor Blue
    Write-Host $InstallPath
    Write-Host "Configuration File: " -NoNewline -ForegroundColor Blue
    Write-Host "$InstallPath\.env"
    Write-Host ""
    Write-Host "Access URLs:" -ForegroundColor Blue
    Write-Host "  • Frontend: " -NoNewline -ForegroundColor Blue
    Write-Host "http://localhost:$($script:FrontendPort)" -ForegroundColor Green
    Write-Host "  • API:      " -NoNewline -ForegroundColor Blue
    Write-Host "http://localhost:$($script:ApiPort)" -ForegroundColor Green
    Write-Host "  • API Docs: " -NoNewline -ForegroundColor Blue
    Write-Host "http://localhost:$($script:ApiPort)/docs" -ForegroundColor Green
    Write-Host ""
    Write-Host "Default Credentials:" -ForegroundColor Blue
    Write-Host "  • Username: " -NoNewline -ForegroundColor Blue
    Write-Host $script:AdminUser -ForegroundColor Green
    Write-Host "  • Password: " -NoNewline -ForegroundColor Blue
    Write-Host $script:AdminPass -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  IMPORTANT: Change default password after first login!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Useful Commands:" -ForegroundColor Blue
    Write-Host "  • View logs:      docker-compose logs -f" -ForegroundColor Green
    Write-Host "  • Stop SIEM:      docker-compose stop" -ForegroundColor Green
    Write-Host "  • Start SIEM:     docker-compose start" -ForegroundColor Green
    Write-Host "  • Restart SIEM:   docker-compose restart" -ForegroundColor Green
    Write-Host "  • Update SIEM:    git pull && docker-compose up -d --build" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Blue
    Write-Host "  1. Access the web interface"
    Write-Host "  2. Login with default credentials"
    Write-Host "  3. Install Windows Agent on endpoints"
    Write-Host "  4. Configure detection rules"
    Write-Host "  5. Monitor Dashboard"
    Write-Host ""
    Write-Host "Documentation: $InstallPath\docs\" -ForegroundColor Green
    Write-Host "Support: https://github.com/$GitHubRepo/issues" -ForegroundColor Green
    Write-Host ""
}

###############################################################################
# Main Installation Flow
###############################################################################

function Main {
    try {
        # Print banner
        Write-Banner
        
        # Check administrator
        if (!(Test-Administrator)) {
            Write-Error "This script must be run as Administrator"
            Write-Info "Right-click PowerShell and select 'Run as Administrator'"
            exit 1
        }
        
        # Check Docker Desktop
        if (!(Test-DockerDesktop)) {
            Install-DockerDesktop
            exit 1
        }
        
        # Check Git
        if (!(Test-Git)) {
            Install-Git
        }
        
        # Download SIEM
        Get-SIEMFromGitHub
        
        # Configure
        New-SIEMConfiguration
        
        # Build and start
        Start-SIEMContainers
        
        # Wait for services
        Wait-ForServices
        
        # Health check
        if (!(Test-SIEMHealth)) {
            Write-Warning "Some health checks failed. Check logs for details."
        }
        
        # Create scheduled task
        New-WindowsService
        
        # Print summary
        Write-Summary
        
        Write-Success "Installation completed successfully!"
    }
    catch {
        Write-Error "Installation failed: $_"
        Write-Error $_.ScriptStackTrace
        exit 1
    }
}

# Run main function
Main
