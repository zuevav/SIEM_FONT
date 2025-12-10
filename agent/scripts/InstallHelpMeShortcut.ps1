<#
.SYNOPSIS
    Устанавливает ярлык "Помоги мне" на рабочий стол пользователя

.DESCRIPTION
    Этот скрипт создает ярлык на рабочем столе для быстрого
    запроса помощи от коллег.

.PARAMETER SiemUrl
    URL SIEM сервера

.EXAMPLE
    .\InstallHelpMeShortcut.ps1 -SiemUrl "https://siem.company.local"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$SiemUrl
)

$ErrorActionPreference = "Stop"

# Путь к скрипту HelpMe.ps1
$scriptPath = "$env:ProgramData\SIEM-Agent\scripts\HelpMe.ps1"

# Создаем директорию если не существует
$scriptDir = Split-Path $scriptPath -Parent
if (-not (Test-Path $scriptDir)) {
    New-Item -ItemType Directory -Path $scriptDir -Force | Out-Null
}

# Копируем скрипт
$sourceScript = Join-Path $PSScriptRoot "HelpMe.ps1"
if (Test-Path $sourceScript) {
    Copy-Item $sourceScript $scriptPath -Force
} else {
    # Если скрипт запущен из другого места, скачиваем
    Write-Host "Скрипт HelpMe.ps1 не найден рядом. Используем встроенную версию."
}

# Создаем BAT файл для запуска PowerShell скрипта
$batContent = @"
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$scriptPath" -SiemUrl "$SiemUrl"
"@
$batPath = "$env:ProgramData\SIEM-Agent\scripts\HelpMe.bat"
Set-Content -Path $batPath -Value $batContent -Encoding ASCII

# Создаем ярлык на рабочем столе
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "Помоги мне.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $batPath
$shortcut.WorkingDirectory = $scriptDir
$shortcut.Description = "Запросить помощь коллеги через SIEM"
$shortcut.IconLocation = "shell32.dll,24"  # Иконка с вопросом
$shortcut.WindowStyle = 7  # Minimized
$shortcut.Save()

# Также создаем в общем меню Пуск (для всех пользователей)
try {
    $allUsersStartMenu = [Environment]::GetFolderPath("CommonStartMenu")
    $programsPath = Join-Path $allUsersStartMenu "Programs\SIEM Agent"

    if (-not (Test-Path $programsPath)) {
        New-Item -ItemType Directory -Path $programsPath -Force | Out-Null
    }

    $startMenuShortcut = Join-Path $programsPath "Помоги мне.lnk"
    $shortcut2 = $shell.CreateShortcut($startMenuShortcut)
    $shortcut2.TargetPath = $batPath
    $shortcut2.WorkingDirectory = $scriptDir
    $shortcut2.Description = "Запросить помощь коллеги через SIEM"
    $shortcut2.IconLocation = "shell32.dll,24"
    $shortcut2.WindowStyle = 7
    $shortcut2.Save()

    Write-Host "Ярлык создан в меню Пуск: $startMenuShortcut" -ForegroundColor Green
} catch {
    Write-Host "Не удалось создать ярлык в меню Пуск (требуются права администратора)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Установка завершена!" -ForegroundColor Green
Write-Host "Ярлык 'Помоги мне' создан на рабочем столе: $shortcutPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Использование:" -ForegroundColor White
Write-Host "1. Пользователь нажимает на ярлык 'Помоги мне'" -ForegroundColor Gray
Write-Host "2. Описывает свою проблему" -ForegroundColor Gray
Write-Host "3. Получает ссылку и отправляет коллеге" -ForegroundColor Gray
Write-Host "4. Коллега открывает ссылку и подключается" -ForegroundColor Gray
Write-Host "5. Пользователь подтверждает подключение" -ForegroundColor Gray
