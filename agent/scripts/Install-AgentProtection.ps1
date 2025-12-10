<#
.SYNOPSIS
    Установка защиты SIEM агента

.DESCRIPTION
    Этот скрипт настраивает защиту SIEM агента:
    - Устанавливает Watchdog службу
    - Защищает файлы агента через ACL
    - Защищает службу от остановки обычными пользователями
    - Настраивает мониторинг целостности

.PARAMETER AgentPath
    Путь к папке агента

.PARAMETER SiemUrl
    URL SIEM-сервера

.EXAMPLE
    .\Install-AgentProtection.ps1 -AgentPath "C:\Program Files\SIEM-Agent"
#>

param(
    [string]$AgentPath = "$env:ProgramData\SIEM-Agent",
    [string]$SiemUrl = "https://siem.company.local",
    [switch]$SkipWatchdog,
    [switch]$SkipFileProtection,
    [switch]$SkipServiceProtection
)

$ErrorActionPreference = "Stop"

# Проверка прав администратора
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Требуются права администратора"
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Установка защиты SIEM агента" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Защита файлов агента через ACL
if (-not $SkipFileProtection) {
    Write-Host "[1/3] Защита файлов агента..." -ForegroundColor Yellow

    $filesToProtect = @(
        "$AgentPath\siem-agent.exe",
        "$AgentPath\siem-watchdog.exe",
        "$AgentPath\config.yaml",
        "$AgentPath\agent_id"
    )

    foreach ($file in $filesToProtect) {
        if (Test-Path $file) {
            try {
                # Получаем текущий ACL
                $acl = Get-Acl $file

                # Удаляем наследование и очищаем существующие правила
                $acl.SetAccessRuleProtection($true, $false)

                # Добавляем права только для SYSTEM и Администраторов
                $systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
                    "NT AUTHORITY\SYSTEM",
                    "FullControl",
                    "Allow"
                )
                $adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
                    "BUILTIN\Administrators",
                    "FullControl",
                    "Allow"
                )

                $acl.SetAccessRule($systemRule)
                $acl.SetAccessRule($adminRule)

                Set-Acl -Path $file -AclObject $acl
                Write-Host "  ✓ Защищён: $file" -ForegroundColor Green
            } catch {
                Write-Host "  ✗ Ошибка защиты $file : $_" -ForegroundColor Red
            }
        }
    }

    # Защита папки агента
    try {
        $acl = Get-Acl $AgentPath

        # Отключаем наследование
        $acl.SetAccessRuleProtection($true, $false)

        # Очищаем все правила
        $acl.Access | ForEach-Object { $acl.RemoveAccessRule($_) } | Out-Null

        # SYSTEM - полный доступ с наследованием
        $systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            "NT AUTHORITY\SYSTEM",
            "FullControl",
            "ContainerInherit,ObjectInherit",
            "None",
            "Allow"
        )

        # Администраторы - полный доступ с наследованием
        $adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            "BUILTIN\Administrators",
            "FullControl",
            "ContainerInherit,ObjectInherit",
            "None",
            "Allow"
        )

        $acl.SetAccessRule($systemRule)
        $acl.SetAccessRule($adminRule)

        Set-Acl -Path $AgentPath -AclObject $acl
        Write-Host "  ✓ Папка агента защищена: $AgentPath" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ Ошибка защиты папки: $_" -ForegroundColor Red
    }

    Write-Host ""
}

# 2. Защита службы SIEM Agent
if (-not $SkipServiceProtection) {
    Write-Host "[2/3] Защита службы SIEMAgent..." -ForegroundColor Yellow

    $serviceName = "SIEMAgent"

    try {
        # Проверяем существование службы
        $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
        if (-not $service) {
            Write-Host "  ! Служба $serviceName не найдена, пропуск" -ForegroundColor Yellow
        } else {
            # Устанавливаем SDDL для службы
            # D: - DACL
            # (A;;CCLCSWRPWPDTLOCRRC;;;SY) - SYSTEM: все права
            # (A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA) - Администраторы: все права
            # (A;;CCLCSWLOCRRC;;;IU) - Интерактивные пользователи: только чтение статуса
            # (A;;CCLCSWLOCRRC;;;SU) - Service Users: только чтение статуса
            $sddl = "D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWLOCRRC;;;IU)(A;;CCLCSWLOCRRC;;;SU)"

            $result = sc.exe sdset $serviceName $sddl 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✓ Служба $serviceName защищена" -ForegroundColor Green
                Write-Host "    Обычные пользователи больше не могут остановить службу" -ForegroundColor Gray
            } else {
                Write-Host "  ✗ Ошибка: $result" -ForegroundColor Red
            }
        }
    } catch {
        Write-Host "  ✗ Ошибка защиты службы: $_" -ForegroundColor Red
    }

    # Настраиваем автоматический перезапуск службы при сбое
    try {
        sc.exe failure $serviceName reset= 86400 actions= restart/5000/restart/10000/restart/30000 | Out-Null
        Write-Host "  ✓ Настроен автоперезапуск при сбое" -ForegroundColor Green
    } catch {
        Write-Host "  ! Не удалось настроить автоперезапуск: $_" -ForegroundColor Yellow
    }

    Write-Host ""
}

# 3. Установка Watchdog службы
if (-not $SkipWatchdog) {
    Write-Host "[3/3] Установка Watchdog службы..." -ForegroundColor Yellow

    $watchdogExe = "$AgentPath\siem-watchdog.exe"

    if (Test-Path $watchdogExe) {
        try {
            # Останавливаем если запущена
            $existingService = Get-Service -Name "SIEMWatchdog" -ErrorAction SilentlyContinue
            if ($existingService) {
                Stop-Service -Name "SIEMWatchdog" -Force -ErrorAction SilentlyContinue
                & $watchdogExe -uninstall 2>&1 | Out-Null
            }

            # Устанавливаем службу
            $result = & $watchdogExe -install 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✓ Watchdog служба установлена" -ForegroundColor Green

                # Защищаем Watchdog службу тоже
                $sddl = "D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWLOCRRC;;;IU)"
                sc.exe sdset "SIEMWatchdog" $sddl 2>&1 | Out-Null

                # Настраиваем перезапуск
                sc.exe failure "SIEMWatchdog" reset= 86400 actions= restart/5000/restart/10000/restart/30000 | Out-Null

                # Запускаем
                Start-Service -Name "SIEMWatchdog"
                Write-Host "  ✓ Watchdog служба запущена" -ForegroundColor Green
            } else {
                Write-Host "  ✗ Ошибка установки: $result" -ForegroundColor Red
            }
        } catch {
            Write-Host "  ✗ Ошибка: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "  ! Watchdog не найден: $watchdogExe" -ForegroundColor Yellow
        Write-Host "    Скомпилируйте watchdog и поместите в папку агента" -ForegroundColor Gray
    }

    Write-Host ""
}

# 4. Обновляем конфигурацию агента
Write-Host "Обновление конфигурации агента..." -ForegroundColor Yellow

$configPath = "$AgentPath\config.yaml"
if (Test-Path $configPath) {
    try {
        $configContent = Get-Content $configPath -Raw

        # Добавляем секцию protection если её нет
        if ($configContent -notmatch "protection:") {
            $protectionConfig = @"

# Защита агента от вредоносного ПО и пользователей
protection:
  enabled: true
  protect_files: true
  protect_service: true
  monitor_tampering: true
  alert_on_tampering: true
  self_heal_enabled: false
  watchdog_enabled: true
  prevent_debugger: true
  integrity_check_interval: 30
"@
            Add-Content -Path $configPath -Value $protectionConfig
            Write-Host "  ✓ Конфигурация защиты добавлена" -ForegroundColor Green
        } else {
            Write-Host "  - Конфигурация защиты уже существует" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  ✗ Ошибка обновления конфигурации: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Защита агента установлена!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Результат:" -ForegroundColor White
Write-Host "  • Файлы агента защищены (только SYSTEM и Администраторы)" -ForegroundColor Gray
Write-Host "  • Служба защищена от остановки пользователями" -ForegroundColor Gray
Write-Host "  • Watchdog следит за работой агента" -ForegroundColor Gray
Write-Host "  • Автоперезапуск при сбоях настроен" -ForegroundColor Gray
Write-Host ""
Write-Host "Для проверки выполните:" -ForegroundColor Yellow
Write-Host "  sc query SIEMAgent" -ForegroundColor White
Write-Host "  sc query SIEMWatchdog" -ForegroundColor White
Write-Host ""
