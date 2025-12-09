<#
.SYNOPSIS
    Скрипт установки SIEM агента через GPO (Group Policy)

.DESCRIPTION
    Этот скрипт предназначен для установки SIEM агента на все компьютеры домена
    через групповую политику (Computer Startup Script).

    Для развертывания:
    1. Скопируйте файлы агента в сетевую папку NETLOGON или DFS
    2. Создайте GPO и добавьте этот скрипт как Computer Startup Script
    3. Привяжите GPO к нужным OU с компьютерами

.PARAMETER AgentPath
    Путь к папке с файлами агента (UNC путь к NETLOGON)

.PARAMETER ServerUrl
    URL SIEM сервера (API endpoint)

.PARAMETER ApiKey
    API ключ для регистрации агента

.EXAMPLE
    Deploy-AgentGPO.ps1 -AgentPath "\\domain.local\NETLOGON\SIEMAgent" -ServerUrl "https://siem.domain.local/api/v1" -ApiKey "your-api-key"

.NOTES
    Author: SIEM Team
    Version: 1.0.0
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$AgentPath = "\\$env:USERDNSDOMAIN\NETLOGON\SIEMAgent",

    [Parameter(Mandatory=$false)]
    [string]$ServerUrl = "https://siem.domain.local/api/v1",

    [Parameter(Mandatory=$false)]
    [string]$ApiKey = "",

    [Parameter(Mandatory=$false)]
    [string]$InstallDir = "C:\Program Files\SIEM Agent",

    [Parameter(Mandatory=$false)]
    [switch]$Force,

    [Parameter(Mandatory=$false)]
    [switch]$Uninstall
)

# Логирование
$LogPath = "C:\Windows\Temp\SIEMAgent_Install.log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Add-Content -Path $LogPath -Value $LogMessage
    if ($Level -eq "ERROR") {
        Write-Error $Message
    } else {
        Write-Host $LogMessage
    }
}

function Get-InstalledAgentVersion {
    $ConfigPath = Join-Path $InstallDir "config.json"
    if (Test-Path $ConfigPath) {
        try {
            $Config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
            return $Config.version
        } catch {
            return $null
        }
    }
    return $null
}

function Get-AvailableAgentVersion {
    $VersionFile = Join-Path $AgentPath "version.txt"
    if (Test-Path $VersionFile) {
        return (Get-Content $VersionFile -Raw).Trim()
    }
    return "1.0.0"
}

function Stop-AgentService {
    Write-Log "Остановка службы SIEM Agent..."
    $Service = Get-Service -Name "SIEMAgent" -ErrorAction SilentlyContinue
    if ($Service) {
        if ($Service.Status -eq "Running") {
            Stop-Service -Name "SIEMAgent" -Force
            Start-Sleep -Seconds 3
        }
        Write-Log "Служба остановлена"
    }
}

function Start-AgentService {
    Write-Log "Запуск службы SIEM Agent..."
    $Service = Get-Service -Name "SIEMAgent" -ErrorAction SilentlyContinue
    if ($Service) {
        Start-Service -Name "SIEMAgent"
        Start-Sleep -Seconds 2
        $Service.Refresh()
        Write-Log "Служба запущена: $($Service.Status)"
    } else {
        Write-Log "Служба не найдена - требуется установка" "WARNING"
    }
}

function Install-AgentService {
    Write-Log "Установка службы SIEM Agent..."

    $ExePath = Join-Path $InstallDir "siem-agent.exe"

    # Создание службы
    $ServiceParams = @{
        Name = "SIEMAgent"
        BinaryPathName = "`"$ExePath`" --service"
        DisplayName = "SIEM Security Agent"
        Description = "SIEM Security Monitoring Agent - собирает события безопасности и отправляет в SIEM"
        StartupType = "Automatic"
    }

    New-Service @ServiceParams -ErrorAction SilentlyContinue

    # Настройка автоматического перезапуска при сбое
    sc.exe failure SIEMAgent reset= 86400 actions= restart/60000/restart/60000/restart/60000 | Out-Null

    Write-Log "Служба установлена"
}

function Uninstall-AgentService {
    Write-Log "Удаление службы SIEM Agent..."

    Stop-AgentService

    $Service = Get-Service -Name "SIEMAgent" -ErrorAction SilentlyContinue
    if ($Service) {
        sc.exe delete SIEMAgent | Out-Null
        Start-Sleep -Seconds 2
        Write-Log "Служба удалена"
    }
}

function Copy-AgentFiles {
    Write-Log "Копирование файлов агента из $AgentPath..."

    # Проверка доступности источника
    if (-not (Test-Path $AgentPath)) {
        Write-Log "Путь к агенту недоступен: $AgentPath" "ERROR"
        return $false
    }

    # Создание директории установки
    if (-not (Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
        Write-Log "Создана директория: $InstallDir"
    }

    # Копирование файлов
    try {
        Copy-Item -Path "$AgentPath\*" -Destination $InstallDir -Recurse -Force
        Write-Log "Файлы скопированы"
        return $true
    } catch {
        Write-Log "Ошибка копирования: $_" "ERROR"
        return $false
    }
}

function Set-AgentConfig {
    Write-Log "Настройка конфигурации агента..."

    $ConfigPath = Join-Path $InstallDir "config.json"
    $Version = Get-AvailableAgentVersion

    $Config = @{
        version = $Version
        server_url = $ServerUrl
        api_key = $ApiKey
        agent_id = [guid]::NewGuid().ToString()
        computer_name = $env:COMPUTERNAME
        domain = $env:USERDNSDOMAIN
        install_date = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")

        # Настройки сбора данных
        collectors = @{
            events = @{ enabled = $true; interval_seconds = 30 }
            sysmon = @{ enabled = $true; interval_seconds = 10 }
            inventory = @{ enabled = $true; interval_seconds = 3600 }
            software_control = @{ enabled = $true }
        }

        # Настройки отправки
        sender = @{
            batch_size = 100
            send_interval_seconds = 60
            retry_count = 3
            retry_delay_seconds = 5
        }

        # Настройки безопасности
        security = @{
            verify_ssl = $true
            encrypt_data = $true
        }
    } | ConvertTo-Json -Depth 5

    Set-Content -Path $ConfigPath -Value $Config -Encoding UTF8
    Write-Log "Конфигурация сохранена"
}

function Add-FirewallRule {
    Write-Log "Настройка правил брандмауэра..."

    # Разрешить исходящие подключения агента
    $ExePath = Join-Path $InstallDir "siem-agent.exe"

    Remove-NetFirewallRule -DisplayName "SIEM Agent Outbound" -ErrorAction SilentlyContinue

    New-NetFirewallRule -DisplayName "SIEM Agent Outbound" `
        -Direction Outbound `
        -Program $ExePath `
        -Action Allow `
        -Protocol TCP `
        -Profile Domain,Private `
        -Description "Allow SIEM Agent to communicate with SIEM server" | Out-Null

    # Разрешить Remote Assistance для удаленной поддержки
    Enable-NetFirewallRule -DisplayGroup "Remote Assistance" -ErrorAction SilentlyContinue

    Write-Log "Правила брандмауэра настроены"
}

function Register-AgentWithServer {
    Write-Log "Регистрация агента на сервере..."

    $ConfigPath = Join-Path $InstallDir "config.json"
    $Config = Get-Content $ConfigPath -Raw | ConvertFrom-Json

    $Body = @{
        agent_id = $Config.agent_id
        computer_name = $env:COMPUTERNAME
        domain = $env:USERDNSDOMAIN
        os_version = (Get-CimInstance Win32_OperatingSystem).Caption
        ip_address = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.PrefixOrigin -ne "WellKnown" } | Select-Object -First 1).IPAddress
        mac_address = (Get-NetAdapter | Where-Object Status -eq "Up" | Select-Object -First 1 | Get-NetAdapterAdvancedProperty -RegistryKeyword "NetworkAddress" -ErrorAction SilentlyContinue).RegistryValue
        installed_at = $Config.install_date
        version = $Config.version
    } | ConvertTo-Json

    try {
        $Headers = @{
            "Content-Type" = "application/json"
            "X-API-Key" = $ApiKey
        }

        $Response = Invoke-RestMethod -Uri "$ServerUrl/agents/register" -Method POST -Body $Body -Headers $Headers -TimeoutSec 30

        if ($Response.success) {
            Write-Log "Агент успешно зарегистрирован"
            return $true
        }
    } catch {
        Write-Log "Не удалось зарегистрировать агент: $_" "WARNING"
        # Не блокируем установку - агент зарегистрируется позже
    }

    return $false
}

# Основная логика

Write-Log "=========================================="
Write-Log "SIEM Agent GPO Deployment Script"
Write-Log "Computer: $env:COMPUTERNAME"
Write-Log "Domain: $env:USERDNSDOMAIN"
Write-Log "=========================================="

# Проверка прав администратора
$IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $IsAdmin) {
    Write-Log "Требуются права администратора!" "ERROR"
    exit 1
}

# Режим удаления
if ($Uninstall) {
    Write-Log "Режим удаления агента..."

    Uninstall-AgentService

    if (Test-Path $InstallDir) {
        Remove-Item -Path $InstallDir -Recurse -Force
        Write-Log "Файлы агента удалены"
    }

    Remove-NetFirewallRule -DisplayName "SIEM Agent Outbound" -ErrorAction SilentlyContinue

    Write-Log "Удаление завершено"
    exit 0
}

# Проверка необходимости установки/обновления
$InstalledVersion = Get-InstalledAgentVersion
$AvailableVersion = Get-AvailableAgentVersion

if ($InstalledVersion -and -not $Force) {
    if ($InstalledVersion -eq $AvailableVersion) {
        Write-Log "Агент уже установлен (версия $InstalledVersion) - обновление не требуется"

        # Убедимся что служба запущена
        Start-AgentService
        exit 0
    } else {
        Write-Log "Доступно обновление: $InstalledVersion -> $AvailableVersion"
    }
}

# Установка/Обновление агента
Write-Log "Начало установки/обновления агента..."

# Остановка службы если существует
Stop-AgentService

# Копирование файлов
if (-not (Copy-AgentFiles)) {
    Write-Log "Установка прервана из-за ошибки копирования" "ERROR"
    exit 1
}

# Настройка конфигурации (только при первой установке)
if (-not $InstalledVersion) {
    Set-AgentConfig
}

# Настройка брандмауэра
Add-FirewallRule

# Установка/обновление службы
if (-not $InstalledVersion) {
    Install-AgentService
}

# Запуск службы
Start-AgentService

# Регистрация на сервере (не критично)
Register-AgentWithServer

Write-Log "=========================================="
Write-Log "Установка завершена успешно!"
Write-Log "Версия: $AvailableVersion"
Write-Log "=========================================="

exit 0
