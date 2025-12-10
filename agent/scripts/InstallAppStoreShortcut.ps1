<#
.SYNOPSIS
    Установка ярлыка магазина приложений на рабочий стол

.DESCRIPTION
    Этот скрипт устанавливает ярлык "Магазин приложений" на рабочий стол
    текущего пользователя или всех пользователей.

.PARAMETER AllUsers
    Установить для всех пользователей (требуются права администратора)

.PARAMETER SiemUrl
    URL SIEM-сервера

.EXAMPLE
    .\InstallAppStoreShortcut.ps1 -AllUsers
#>

param(
    [switch]$AllUsers,
    [string]$SiemUrl = "https://siem.company.local"
)

$ErrorActionPreference = "Stop"

# Определяем пути
$AgentPath = "$env:ProgramData\SIEM-Agent"
$ScriptName = "AppStore.ps1"
$ShortcutName = "Магазин приложений.lnk"

if ($AllUsers) {
    $DesktopPath = [Environment]::GetFolderPath("CommonDesktopDirectory")
    $StartMenuPath = [Environment]::GetFolderPath("CommonStartMenu") + "\Programs\SIEM"
} else {
    $DesktopPath = [Environment]::GetFolderPath("Desktop")
    $StartMenuPath = [Environment]::GetFolderPath("StartMenu") + "\Programs\SIEM"
}

# Проверяем права администратора для AllUsers
if ($AllUsers) {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Error "Для установки для всех пользователей требуются права администратора"
        exit 1
    }
}

# Создаем папку агента если нет
if (-not (Test-Path $AgentPath)) {
    New-Item -ItemType Directory -Path $AgentPath -Force | Out-Null
}

# Копируем скрипт магазина
$ScriptSource = Join-Path $PSScriptRoot $ScriptName
$ScriptDest = Join-Path $AgentPath $ScriptName

if (Test-Path $ScriptSource) {
    Copy-Item $ScriptSource $ScriptDest -Force
    Write-Host "Скрипт скопирован в $ScriptDest" -ForegroundColor Green
} else {
    # Скачиваем с сервера если локально нет
    Write-Host "Скрипт не найден локально, попытка загрузки с сервера..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri "$SiemUrl/static/agent/AppStore.ps1" -OutFile $ScriptDest -UseBasicParsing
        Write-Host "Скрипт загружен с сервера" -ForegroundColor Green
    } catch {
        Write-Error "Не удалось получить скрипт магазина: $_"
        exit 1
    }
}

# Создаем папку в меню Пуск
if (-not (Test-Path $StartMenuPath)) {
    New-Item -ItemType Directory -Path $StartMenuPath -Force | Out-Null
}

# Функция создания ярлыка
function New-Shortcut {
    param(
        [string]$Path,
        [string]$TargetPath,
        [string]$Arguments,
        [string]$Description,
        [string]$IconLocation
    )

    $WScriptShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WScriptShell.CreateShortcut($Path)
    $Shortcut.TargetPath = $TargetPath
    $Shortcut.Arguments = $Arguments
    $Shortcut.Description = $Description
    $Shortcut.WorkingDirectory = $AgentPath
    if ($IconLocation) {
        $Shortcut.IconLocation = $IconLocation
    }
    $Shortcut.Save()
}

# Параметры ярлыка
$TargetPath = "powershell.exe"
$Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptDest`" -SiemUrl `"$SiemUrl`""
$Description = "Магазин приложений SIEM - просмотр и установка разрешённого ПО"

# Используем иконку из shell32.dll (иконка магазина/коробки)
$IconLocation = "%SystemRoot%\System32\shell32.dll,167"

# Создаем ярлык на рабочем столе
$DesktopShortcut = Join-Path $DesktopPath $ShortcutName
New-Shortcut -Path $DesktopShortcut -TargetPath $TargetPath -Arguments $Arguments -Description $Description -IconLocation $IconLocation
Write-Host "Ярлык создан: $DesktopShortcut" -ForegroundColor Green

# Создаем ярлык в меню Пуск
$StartMenuShortcut = Join-Path $StartMenuPath $ShortcutName
New-Shortcut -Path $StartMenuShortcut -TargetPath $TargetPath -Arguments $Arguments -Description $Description -IconLocation $IconLocation
Write-Host "Ярлык создан: $StartMenuShortcut" -ForegroundColor Green

Write-Host "`nУстановка завершена!" -ForegroundColor Cyan
Write-Host "Теперь пользователи могут открыть 'Магазин приложений' с рабочего стола или из меню Пуск." -ForegroundColor Cyan
