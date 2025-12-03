# =====================================================================
# SIEM SYSTEM - AUTOMATED INSTALLER FOR WINDOWS
# =====================================================================
# PowerShell script for easy installation on Windows
# Run as Administrator
# =====================================================================

#Requires -RunAsAdministrator

param(
    [switch]$SkipDB = $false,
    [switch]$SkipBackend = $false,
    [switch]$SkipFrontend = $false,
    [string]$SqlServer = "localhost",
    [string]$SqlUser = "",
    [string]$SqlPassword = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Colors
function Write-Success { Write-Host "✓ $args" -ForegroundColor Green }
function Write-Error { Write-Host "✗ $args" -ForegroundColor Red }
function Write-Info { Write-Host "ℹ $args" -ForegroundColor Cyan }
function Write-Warning { Write-Host "⚠ $args" -ForegroundColor Yellow }
function Write-Step { Write-Host "`n===> $args" -ForegroundColor Yellow }

# Banner
Write-Host @"
╔═══════════════════════════════════════════════════════════╗
║          SIEM SYSTEM - AUTOMATED INSTALLER               ║
║          Version 1.0.0                                    ║
╚═══════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

Write-Info "Starting installation process..."
Write-Info "Current directory: $(Get-Location)"

# =====================================================================
# STEP 1: CHECK PREREQUISITES
# =====================================================================

Write-Step "Step 1: Checking prerequisites"

# Check PowerShell version
$psVersion = $PSVersionTable.PSVersion
if ($psVersion.Major -lt 5) {
    Write-Error "PowerShell 5.0+ required. Current version: $psVersion"
    exit 1
}
Write-Success "PowerShell version: $psVersion"

# Check if running as admin
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator"
    exit 1
}
Write-Success "Running as Administrator"

# Check Python
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -eq 3 -and $minor -ge 11) {
            Write-Success "Python version: $pythonVersion"
        } else {
            Write-Error "Python 3.11+ required. Current: $pythonVersion"
            Write-Info "Download from: https://www.python.org/downloads/"
            exit 1
        }
    }
} catch {
    Write-Error "Python not found. Please install Python 3.11+"
    Write-Info "Download from: https://www.python.org/downloads/"
    exit 1
}

# Check pip
try {
    $pipVersion = python -m pip --version
    Write-Success "pip installed: $pipVersion"
} catch {
    Write-Error "pip not found"
    exit 1
}

# Check Node.js (optional for frontend)
if (-not $SkipFrontend) {
    try {
        $nodeVersion = node --version
        Write-Success "Node.js version: $nodeVersion"
    } catch {
        Write-Warning "Node.js not found. Frontend will be skipped."
        Write-Info "Install Node.js 18+ from: https://nodejs.org/"
        $SkipFrontend = $true
    }
}

# Check SQL Server connection
if (-not $SkipDB) {
    Write-Info "Checking SQL Server connection..."
    try {
        $sqlcmdVersion = sqlcmd -?
        Write-Success "sqlcmd utility found"

        # Test connection
        Write-Info "Testing connection to SQL Server: $SqlServer"

        if ($SqlUser) {
            sqlcmd -S $SqlServer -U $SqlUser -P $SqlPassword -Q "SELECT @@VERSION" -b | Out-Null
        } else {
            sqlcmd -S $SqlServer -E -Q "SELECT @@VERSION" -b | Out-Null
        }

        Write-Success "SQL Server connection successful"
    } catch {
        Write-Error "Cannot connect to SQL Server: $SqlServer"
        Write-Info "Install SQL Server tools from: https://aka.ms/ssmsfullsetup"
        Write-Info "Or skip database installation with -SkipDB flag"
        exit 1
    }
}

# =====================================================================
# STEP 2: CREATE ENVIRONMENT FILE
# =====================================================================

Write-Step "Step 2: Setting up environment configuration"

$envFile = ".env"
$envExample = ".env.example"

if (-not (Test-Path $envExample)) {
    Write-Error "$envExample not found"
    exit 1
}

if (Test-Path $envFile) {
    Write-Warning ".env file already exists"
    $overwrite = Read-Host "Overwrite? (y/N)"
    if ($overwrite -ne "y") {
        Write-Info "Keeping existing .env file"
    } else {
        Copy-Item $envExample $envFile -Force
        Write-Success "Created .env from template"
    }
} else {
    Copy-Item $envExample $envFile
    Write-Success "Created .env from template"
}

# Update .env with SQL Server connection
if (-not $SkipDB) {
    Write-Info "Updating SQL Server connection settings in .env..."

    $envContent = Get-Content $envFile
    $envContent = $envContent -replace '^MSSQL_SERVER=.*', "MSSQL_SERVER=$SqlServer"

    if ($SqlUser) {
        $envContent = $envContent -replace '^MSSQL_USER=.*', "MSSQL_USER=$SqlUser"
        $envContent = $envContent -replace '^MSSQL_PASSWORD=.*', "MSSQL_PASSWORD=$SqlPassword"
    }

    $envContent | Set-Content $envFile
    Write-Success "Updated .env with SQL Server settings"
}

Write-Warning "IMPORTANT: Please edit .env file and configure:"
Write-Info "  - Yandex GPT API keys (YANDEX_GPT_API_KEY, YANDEX_GPT_FOLDER_ID)"
Write-Info "  - SMTP settings for email notifications"
Write-Info "  - Organization info for CBR reports"
Write-Info "  - JWT_SECRET_KEY (change from default!)"

$continue = Read-Host "`nPress Enter to continue after editing .env, or type 'skip' to continue without editing"
if ($continue -eq "skip") {
    Write-Warning "Continuing with default settings. You can edit .env later."
}

# =====================================================================
# STEP 3: INSTALL DATABASE
# =====================================================================

if (-not $SkipDB) {
    Write-Step "Step 3: Installing database schema"

    $dbScripts = @(
        "database/schema.sql",
        "database/procedures.sql",
        "database/triggers.sql",
        "database/seed.sql",
        "database/jobs.sql"
    )

    foreach ($script in $dbScripts) {
        if (-not (Test-Path $script)) {
            Write-Error "Script not found: $script"
            exit 1
        }

        Write-Info "Executing $script..."

        try {
            if ($SqlUser) {
                sqlcmd -S $SqlServer -U $SqlUser -P $SqlPassword -i $script -b
            } else {
                sqlcmd -S $SqlServer -E -i $script -b
            }
            Write-Success "Executed $script"
        } catch {
            Write-Error "Failed to execute $script"
            Write-Error $_.Exception.Message
            exit 1
        }
    }

    Write-Success "Database installation completed!"
    Write-Info "Database: SIEM_DB"
    Write-Info "Default users created:"
    Write-Info "  - admin / Admin123!"
    Write-Info "  - analyst / Admin123!"
    Write-Info "  - viewer / Admin123!"
    Write-Warning "CHANGE DEFAULT PASSWORDS after first login!"

} else {
    Write-Warning "Skipping database installation"
}

# =====================================================================
# STEP 4: INSTALL BACKEND
# =====================================================================

if (-not $SkipBackend) {
    Write-Step "Step 4: Installing backend dependencies"

    Set-Location backend

    # Create virtual environment
    Write-Info "Creating Python virtual environment..."
    python -m venv venv

    # Activate venv and install dependencies
    Write-Info "Installing Python packages..."
    .\venv\Scripts\Activate.ps1

    python -m pip install --upgrade pip
    pip install -r requirements.txt

    Write-Success "Backend dependencies installed"

    # Initialize database models (if script exists)
    if (Test-Path "scripts/init_db.py") {
        Write-Info "Initializing database models..."
        python scripts/init_db.py
    }

    deactivate
    Set-Location ..

    Write-Success "Backend installation completed!"

} else {
    Write-Warning "Skipping backend installation"
}

# =====================================================================
# STEP 5: INSTALL FRONTEND
# =====================================================================

if (-not $SkipFrontend) {
    Write-Step "Step 5: Installing frontend dependencies"

    if (Test-Path "frontend/package.json") {
        Set-Location frontend

        Write-Info "Installing npm packages..."
        npm install

        Write-Success "Frontend dependencies installed"

        Set-Location ..
    } else {
        Write-Warning "Frontend not found, skipping"
    }
} else {
    Write-Warning "Skipping frontend installation"
}

# =====================================================================
# STEP 6: INSTALL NETWORK MONITOR (Optional - WSL recommended)
# =====================================================================

Write-Step "Step 6: Network Monitor (optional)"

if (Test-Path "network_monitor") {
    Write-Warning "Network Monitor is designed for Linux"
    Write-Info "For Windows, we recommend installing it in WSL (Windows Subsystem for Linux)"
    Write-Info "Alternatively, you can run it on a separate Linux server"

    $installNetmon = Read-Host "Install Network Monitor in WSL or skip? (wsl/skip) [skip]"

    if ($installNetmon -eq "wsl") {
        Write-Info "To install Network Monitor in WSL:"
        Write-Info "1. Install WSL: wsl --install"
        Write-Info "2. Open WSL: wsl"
        Write-Info "3. cd /mnt/c/<path-to-project>/network_monitor"
        Write-Info "4. Run: ./install.sh"
        Write-Info ""
        Write-Info "Network Monitor will run on the same machine via WSL"
    } else {
        Write-Info "Skipping Network Monitor installation"
        Write-Info "You can install it later on a Linux server"
    }
} else {
    Write-Warning "Network Monitor directory not found"
}

# =====================================================================
# STEP 7: CREATE SHORTCUTS AND SCRIPTS
# =====================================================================

Write-Step "Step 7: Creating helper scripts"

# Start backend script
$startBackend = @"
@echo off
cd backend
call venv\Scripts\activate.bat
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"@

$startBackend | Out-File -FilePath "start_backend.bat" -Encoding ASCII
Write-Success "Created start_backend.bat"

# Start frontend script
if (-not $SkipFrontend -and (Test-Path "frontend")) {
    $startFrontend = @"
@echo off
cd frontend
npm run dev
"@
    $startFrontend | Out-File -FilePath "start_frontend.bat" -Encoding ASCII
    Write-Success "Created start_frontend.bat"
}

# Stop all script
$stopAll = @"
@echo off
echo Stopping SIEM services...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM node.exe /T 2>nul
echo Done.
pause
"@

$stopAll | Out-File -FilePath "stop_all.bat" -Encoding ASCII
Write-Success "Created stop_all.bat"

# =====================================================================
# COMPLETION
# =====================================================================

Write-Host @"

╔═══════════════════════════════════════════════════════════╗
║          INSTALLATION COMPLETED SUCCESSFULLY!             ║
╚═══════════════════════════════════════════════════════════╝

"@ -ForegroundColor Green

Write-Success "SIEM System has been installed!"

Write-Info "`nNext steps:"
Write-Host "1. Edit .env file with your configuration" -ForegroundColor Yellow
Write-Host "2. Start backend:  .\start_backend.bat" -ForegroundColor Yellow

if (-not $SkipFrontend) {
    Write-Host "3. Start frontend: .\start_frontend.bat" -ForegroundColor Yellow
}

if ((Test-Path "network_monitor") -and ($installNetmon -eq "wsl")) {
    Write-Host "4. Install Network Monitor in WSL (see instructions above)" -ForegroundColor Yellow
}

Write-Host "`nAccess the system:" -ForegroundColor Cyan
Write-Host "  Backend API:  http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:     http://localhost:8000/docs" -ForegroundColor White

if (-not $SkipFrontend) {
    Write-Host "  Frontend:     http://localhost:5173" -ForegroundColor White
}

Write-Host "`nDefault credentials:" -ForegroundColor Cyan
Write-Host "  Username: admin" -ForegroundColor White
Write-Host "  Password: Admin123!" -ForegroundColor White

Write-Warning "`n⚠ SECURITY:"
Write-Info "  - Change default passwords after first login"
Write-Info "  - Configure JWT_SECRET_KEY in .env"
Write-Info "  - Set up Yandex GPT API keys for AI analysis"
Write-Info "  - Configure SMTP for email notifications"

Write-Host "`nFor help, see README.md" -ForegroundColor Cyan

Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
