<#
.SYNOPSIS
    Создание GPO для автоматического развертывания SIEM агента

.DESCRIPTION
    Этот скрипт создает объект групповой политики (GPO) для автоматического
    развертывания SIEM агента на все компьютеры в домене или выбранных OU.

.PARAMETER GPOName
    Имя создаваемой GPO

.PARAMETER SourcePath
    Локальный путь к файлам агента

.PARAMETER ServerUrl
    URL SIEM сервера

.PARAMETER ApiKey
    API ключ для агентов

.PARAMETER TargetOU
    Distinguished Name OU для привязки GPO (опционально)

.EXAMPLE
    Create-GPOForAgent.ps1 -SourcePath "C:\Agent" -ServerUrl "https://siem.domain.local/api/v1" -ApiKey "key123"

.NOTES
    Требуется:
    - Права Domain Admin или GPO Admin
    - Модуль GroupPolicy (RSAT)
    - Доступ к SYSVOL/NETLOGON
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$GPOName = "SIEM Agent Deployment",

    [Parameter(Mandatory=$true)]
    [string]$SourcePath,

    [Parameter(Mandatory=$true)]
    [string]$ServerUrl,

    [Parameter(Mandatory=$false)]
    [string]$ApiKey = "",

    [Parameter(Mandatory=$false)]
    [string]$TargetOU = "",

    [Parameter(Mandatory=$false)]
    [switch]$LinkToAllComputers
)

# Импорт модуля GroupPolicy
Import-Module GroupPolicy -ErrorAction Stop
Import-Module ActiveDirectory -ErrorAction Stop

$ErrorActionPreference = "Stop"

# Получение информации о домене
$Domain = Get-ADDomain
$DomainDN = $Domain.DistinguishedName
$DomainDNS = $Domain.DNSRoot
$NetlogonPath = "\\$DomainDNS\NETLOGON"
$AgentNetlogonPath = "$NetlogonPath\SIEMAgent"

Write-Host "=========================================="
Write-Host "Создание GPO для SIEM Agent"
Write-Host "Домен: $DomainDNS"
Write-Host "=========================================="

# 1. Копирование файлов агента в NETLOGON
Write-Host "`n[1/5] Копирование файлов агента в NETLOGON..."

if (-not (Test-Path $SourcePath)) {
    throw "Путь к агенту не найден: $SourcePath"
}

if (Test-Path $AgentNetlogonPath) {
    Remove-Item -Path $AgentNetlogonPath -Recurse -Force
}

New-Item -ItemType Directory -Path $AgentNetlogonPath -Force | Out-Null
Copy-Item -Path "$SourcePath\*" -Destination $AgentNetlogonPath -Recurse -Force

# Создание файла версии
$Version = "1.0.0"
if (Test-Path "$SourcePath\version.txt") {
    $Version = (Get-Content "$SourcePath\version.txt" -Raw).Trim()
}
Set-Content -Path "$AgentNetlogonPath\version.txt" -Value $Version

Write-Host "Файлы скопированы в: $AgentNetlogonPath"

# 2. Копирование скрипта установки
Write-Host "`n[2/5] Подготовка скрипта установки..."

$ScriptSourcePath = Join-Path $PSScriptRoot "Deploy-AgentGPO.ps1"
if (-not (Test-Path $ScriptSourcePath)) {
    throw "Скрипт Deploy-AgentGPO.ps1 не найден в $PSScriptRoot"
}

$ScriptDestPath = "$AgentNetlogonPath\Deploy-AgentGPO.ps1"
Copy-Item -Path $ScriptSourcePath -Destination $ScriptDestPath -Force

# Создание wrapper-скрипта с параметрами
$WrapperScript = @"
# SIEM Agent GPO Installation Wrapper
# Auto-generated script

`$ErrorActionPreference = "SilentlyContinue"

# Параметры установки
`$AgentPath = "$AgentNetlogonPath"
`$ServerUrl = "$ServerUrl"
`$ApiKey = "$ApiKey"

# Запуск установки
& "`$AgentPath\Deploy-AgentGPO.ps1" -AgentPath `$AgentPath -ServerUrl `$ServerUrl -ApiKey `$ApiKey

exit `$LASTEXITCODE
"@

$WrapperPath = "$AgentNetlogonPath\Install-SIEMAgent.ps1"
Set-Content -Path $WrapperPath -Value $WrapperScript -Encoding UTF8

Write-Host "Скрипты подготовлены"

# 3. Создание GPO
Write-Host "`n[3/5] Создание GPO: $GPOName..."

# Удаление существующей GPO с таким именем
$ExistingGPO = Get-GPO -Name $GPOName -ErrorAction SilentlyContinue
if ($ExistingGPO) {
    Write-Host "Удаление существующей GPO..."
    Remove-GPO -Name $GPOName -ErrorAction SilentlyContinue
}

# Создание новой GPO
$GPO = New-GPO -Name $GPOName -Comment "Автоматическое развертывание SIEM Security Agent на все компьютеры домена"

Write-Host "GPO создана: $($GPO.DisplayName)"

# 4. Настройка GPO - добавление скрипта запуска
Write-Host "`n[4/5] Настройка скрипта запуска компьютера..."

# Путь к хранилищу GPO
$GPOPath = "\\$DomainDNS\SYSVOL\$DomainDNS\Policies\{$($GPO.Id)}"
$ScriptsPath = "$GPOPath\Machine\Scripts\Startup"

# Создание директории для скриптов
New-Item -ItemType Directory -Path $ScriptsPath -Force | Out-Null

# Копирование скрипта в GPO
$GPOScriptPath = "$ScriptsPath\Install-SIEMAgent.ps1"
Copy-Item -Path $WrapperPath -Destination $GPOScriptPath -Force

# Создание scripts.ini
$ScriptsIniPath = "$GPOPath\Machine\Scripts\scripts.ini"
$ScriptsIniContent = @"

[Startup]
0CmdLine=$GPOScriptPath
0Parameters=
"@
Set-Content -Path $ScriptsIniPath -Value $ScriptsIniContent -Encoding Unicode

# Настройка psscripts.ini для PowerShell
$PSScriptsIniPath = "$GPOPath\Machine\Scripts\psscripts.ini"
$PSScriptsIniContent = @"

[Startup]
0CmdLine=$GPOScriptPath
0Parameters=
"@
Set-Content -Path $PSScriptsIniPath -Value $PSScriptsIniContent -Encoding Unicode

# Обновление версии GPO
$GPO | Set-GPRegistryValue -Key "HKLM\Software\SIEM" -ValueName "DeploymentEnabled" -Type String -Value "True" | Out-Null

Write-Host "Скрипт запуска настроен"

# 5. Привязка GPO к OU
Write-Host "`n[5/5] Привязка GPO..."

if ($TargetOU) {
    # Привязка к конкретной OU
    New-GPLink -Name $GPOName -Target $TargetOU -LinkEnabled Yes -ErrorAction SilentlyContinue
    Write-Host "GPO привязана к: $TargetOU"
} elseif ($LinkToAllComputers) {
    # Привязка к корню домена (все компьютеры)
    New-GPLink -Name $GPOName -Target $DomainDN -LinkEnabled Yes -ErrorAction SilentlyContinue
    Write-Host "GPO привязана к корню домена (все компьютеры)"
} else {
    Write-Host "GPO создана, но не привязана. Используйте GPMC для привязки к нужным OU."
}

# Вывод инструкций
Write-Host "`n=========================================="
Write-Host "GPO успешно создана!"
Write-Host "=========================================="
Write-Host "`nСледующие шаги:"
Write-Host "1. Откройте Group Policy Management Console (gpmc.msc)"
Write-Host "2. Найдите GPO '$GPOName'"
Write-Host "3. Привяжите GPO к нужным OU с компьютерами"
Write-Host "4. Дождитесь обновления политик на компьютерах (gpupdate /force)"
Write-Host "`nФайлы агента: $AgentNetlogonPath"
Write-Host "Лог установки: C:\Windows\Temp\SIEMAgent_Install.log"

# Вывод команды для принудительного обновления
Write-Host "`nДля принудительного обновления политик на компьютерах выполните:"
Write-Host "  Invoke-GPUpdate -Computer <имя_компьютера> -Force"
Write-Host "  или на клиенте: gpupdate /force && shutdown /r /t 0"

return $GPO
