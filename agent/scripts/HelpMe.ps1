<#
.SYNOPSIS
    "Помоги мне" - Запрос помощи от коллеги

.DESCRIPTION
    Этот скрипт создает запрос на помощь и генерирует ссылку,
    которую можно отправить коллеге для удаленного подключения.

.NOTES
    Разместите ярлык на рабочем столе пользователя
#>

param(
    [string]$SiemUrl = "https://siem.company.local",
    [string]$Description = ""
)

# Конфигурация
$ConfigFile = "$env:ProgramData\SIEM-Agent\config.yaml"
$AgentIdFile = "$env:ProgramData\SIEM-Agent\agent_id"

# Функция показа диалога
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Show-HelpMeDialog {
    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Помоги мне"
    $form.Size = New-Object System.Drawing.Size(450, 350)
    $form.StartPosition = "CenterScreen"
    $form.FormBorderStyle = "FixedDialog"
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.TopMost = $true
    $form.Font = New-Object System.Drawing.Font("Segoe UI", 10)

    # Иконка
    $icon = [System.Drawing.SystemIcons]::Question
    $pictureBox = New-Object System.Windows.Forms.PictureBox
    $pictureBox.Image = $icon.ToBitmap()
    $pictureBox.Location = New-Object System.Drawing.Point(20, 20)
    $pictureBox.Size = New-Object System.Drawing.Size(48, 48)
    $form.Controls.Add($pictureBox)

    # Заголовок
    $titleLabel = New-Object System.Windows.Forms.Label
    $titleLabel.Location = New-Object System.Drawing.Point(80, 20)
    $titleLabel.Size = New-Object System.Drawing.Size(340, 30)
    $titleLabel.Text = "Запросить помощь коллеги"
    $titleLabel.Font = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Bold)
    $form.Controls.Add($titleLabel)

    # Описание
    $descLabel = New-Object System.Windows.Forms.Label
    $descLabel.Location = New-Object System.Drawing.Point(80, 55)
    $descLabel.Size = New-Object System.Drawing.Size(340, 40)
    $descLabel.Text = "Опишите вашу проблему (коллега увидит это описание):"
    $form.Controls.Add($descLabel)

    # Поле ввода описания
    $descTextBox = New-Object System.Windows.Forms.TextBox
    $descTextBox.Location = New-Object System.Drawing.Point(20, 100)
    $descTextBox.Size = New-Object System.Drawing.Size(395, 80)
    $descTextBox.Multiline = $true
    $descTextBox.ScrollBars = "Vertical"
    $descTextBox.Text = $Description
    $form.Controls.Add($descTextBox)

    # Информация
    $infoLabel = New-Object System.Windows.Forms.Label
    $infoLabel.Location = New-Object System.Drawing.Point(20, 190)
    $infoLabel.Size = New-Object System.Drawing.Size(395, 60)
    $infoLabel.Text = "После нажатия 'Создать ссылку' вы получите короткую ссылку, которую можно отправить коллеге через мессенджер (Yandex, Telegram и т.д.)"
    $infoLabel.ForeColor = [System.Drawing.Color]::Gray
    $form.Controls.Add($infoLabel)

    # Кнопка создания
    $createButton = New-Object System.Windows.Forms.Button
    $createButton.Location = New-Object System.Drawing.Point(20, 260)
    $createButton.Size = New-Object System.Drawing.Size(180, 40)
    $createButton.Text = "Создать ссылку"
    $createButton.BackColor = [System.Drawing.Color]::FromArgb(0, 122, 255)
    $createButton.ForeColor = [System.Drawing.Color]::White
    $createButton.FlatStyle = "Flat"
    $createButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
    $form.Controls.Add($createButton)
    $form.AcceptButton = $createButton

    # Кнопка отмены
    $cancelButton = New-Object System.Windows.Forms.Button
    $cancelButton.Location = New-Object System.Drawing.Point(220, 260)
    $cancelButton.Size = New-Object System.Drawing.Size(100, 40)
    $cancelButton.Text = "Отмена"
    $cancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
    $form.Controls.Add($cancelButton)
    $form.CancelButton = $cancelButton

    $result = $form.ShowDialog()

    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
        return $descTextBox.Text
    }
    return $null
}

function Show-LinkDialog {
    param([string]$Link, [string]$Token)

    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Ссылка готова!"
    $form.Size = New-Object System.Drawing.Size(500, 300)
    $form.StartPosition = "CenterScreen"
    $form.FormBorderStyle = "FixedDialog"
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.TopMost = $true
    $form.Font = New-Object System.Drawing.Font("Segoe UI", 10)

    # Заголовок
    $titleLabel = New-Object System.Windows.Forms.Label
    $titleLabel.Location = New-Object System.Drawing.Point(20, 20)
    $titleLabel.Size = New-Object System.Drawing.Size(450, 30)
    $titleLabel.Text = "Отправьте эту ссылку коллеге:"
    $titleLabel.Font = New-Object System.Drawing.Font("Segoe UI", 12, [System.Drawing.FontStyle]::Bold)
    $form.Controls.Add($titleLabel)

    # Ссылка
    $linkTextBox = New-Object System.Windows.Forms.TextBox
    $linkTextBox.Location = New-Object System.Drawing.Point(20, 60)
    $linkTextBox.Size = New-Object System.Drawing.Size(350, 30)
    $linkTextBox.Text = $Link
    $linkTextBox.ReadOnly = $true
    $linkTextBox.Font = New-Object System.Drawing.Font("Consolas", 11)
    $linkTextBox.BackColor = [System.Drawing.Color]::White
    $form.Controls.Add($linkTextBox)

    # Кнопка копирования
    $copyButton = New-Object System.Windows.Forms.Button
    $copyButton.Location = New-Object System.Drawing.Point(380, 58)
    $copyButton.Size = New-Object System.Drawing.Size(90, 34)
    $copyButton.Text = "Копировать"
    $copyButton.Add_Click({
        [System.Windows.Forms.Clipboard]::SetText($Link)
        $copyButton.Text = "Скопировано!"
        $copyButton.BackColor = [System.Drawing.Color]::LightGreen
    })
    $form.Controls.Add($copyButton)

    # Код (короткий)
    $codeLabel = New-Object System.Windows.Forms.Label
    $codeLabel.Location = New-Object System.Drawing.Point(20, 110)
    $codeLabel.Size = New-Object System.Drawing.Size(200, 25)
    $codeLabel.Text = "Или продиктуйте код:"
    $form.Controls.Add($codeLabel)

    $codeTextBox = New-Object System.Windows.Forms.TextBox
    $codeTextBox.Location = New-Object System.Drawing.Point(200, 105)
    $codeTextBox.Size = New-Object System.Drawing.Size(150, 35)
    $codeTextBox.Text = $Token
    $codeTextBox.ReadOnly = $true
    $codeTextBox.Font = New-Object System.Drawing.Font("Consolas", 16, [System.Drawing.FontStyle]::Bold)
    $codeTextBox.TextAlign = "Center"
    $codeTextBox.BackColor = [System.Drawing.Color]::LightYellow
    $form.Controls.Add($codeTextBox)

    # Инструкции
    $infoLabel = New-Object System.Windows.Forms.Label
    $infoLabel.Location = New-Object System.Drawing.Point(20, 150)
    $infoLabel.Size = New-Object System.Drawing.Size(450, 60)
    $infoLabel.Text = "Когда коллега перейдет по ссылке, вы увидите запрос на подтверждение. После вашего согласия он сможет видеть ваш экран и помочь вам."
    $infoLabel.ForeColor = [System.Drawing.Color]::Gray
    $form.Controls.Add($infoLabel)

    # Кнопка закрытия
    $closeButton = New-Object System.Windows.Forms.Button
    $closeButton.Location = New-Object System.Drawing.Point(190, 220)
    $closeButton.Size = New-Object System.Drawing.Size(120, 40)
    $closeButton.Text = "Готово"
    $closeButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
    $form.Controls.Add($closeButton)
    $form.AcceptButton = $closeButton

    $form.ShowDialog()
}

function Show-ConsentDialog {
    param([string]$HelperName)

    $result = [System.Windows.Forms.MessageBox]::Show(
        "$HelperName хочет подключиться к вашему компьютеру для помощи.`n`nРазрешить подключение?",
        "Запрос на подключение",
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Question,
        [System.Windows.Forms.MessageBoxDefaultButton]::Button1,
        [System.Windows.Forms.MessageBoxOptions]::DefaultDesktopOnly
    )

    return ($result -eq [System.Windows.Forms.DialogResult]::Yes)
}

function Get-AgentId {
    if (Test-Path $AgentIdFile) {
        return Get-Content $AgentIdFile -Raw
    }
    # Генерируем временный ID если агент не установлен
    return [guid]::NewGuid().ToString()
}

function Get-SiemUrl {
    if (Test-Path $ConfigFile) {
        $config = Get-Content $ConfigFile -Raw
        if ($config -match "api_url:\s*[`"']?([^`"'\s]+)") {
            return $Matches[1]
        }
    }
    return $SiemUrl
}

# Основной код
try {
    # Показываем диалог запроса помощи
    $description = Show-HelpMeDialog
    if (-not $description) {
        exit 0
    }

    # Получаем данные
    $agentId = Get-AgentId
    $siemUrl = Get-SiemUrl
    $computerName = $env:COMPUTERNAME
    $userName = $env:USERNAME
    $userDisplayName = [System.DirectoryServices.AccountManagement.UserPrincipal]::Current.DisplayName
    if (-not $userDisplayName) { $userDisplayName = $userName }

    # Создаем запрос
    $body = @{
        agent_id = $agentId
        computer_name = $computerName
        computer_ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" } | Select-Object -First 1).IPAddress
        user_name = $userName
        user_display_name = $userDisplayName
        description = $description
        expiry_minutes = 30
    } | ConvertTo-Json

    # Отправляем запрос
    $response = Invoke-RestMethod -Uri "$siemUrl/api/v1/ad/peer-help/request" -Method Post -Body $body -ContentType "application/json"

    $token = $response.token
    $fullLink = "$siemUrl/help/$token"

    # Показываем ссылку
    Show-LinkDialog -Link $fullLink -Token $token

    # Ждем подключения помощника
    Write-Host "Ожидание помощника..." -ForegroundColor Yellow

    $timeout = 30 * 60  # 30 минут
    $elapsed = 0
    $checkInterval = 5

    while ($elapsed -lt $timeout) {
        Start-Sleep -Seconds $checkInterval
        $elapsed += $checkInterval

        try {
            $status = Invoke-RestMethod -Uri "$siemUrl/api/v1/ad/peer-help/pending/$agentId" -Method Get

            if ($status.has_pending) {
                $helperName = $status.helper_name

                # Показываем запрос на согласие
                $consent = Show-ConsentDialog -HelperName $helperName

                if ($consent) {
                    # Генерируем пароль для Remote Assistance
                    $password = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 8 | ForEach-Object { [char]$_ })

                    # Отправляем согласие
                    $consentBody = @{
                        action = "accept"
                        connection_password = $password
                        port = 3389
                    } | ConvertTo-Json

                    Invoke-RestMethod -Uri "$siemUrl/api/v1/ad/peer-help/$token/consent" -Method Post -Body $consentBody -ContentType "application/json"

                    # Запускаем Remote Assistance
                    Start-Process "msra.exe" -ArgumentList "/offerRA", $env:COMPUTERNAME

                    [System.Windows.Forms.MessageBox]::Show(
                        "Подключение разрешено!`n`nПароль для подключения: $password`n`n$helperName может теперь подключиться к вашему компьютеру.",
                        "Подключение установлено",
                        [System.Windows.Forms.MessageBoxButtons]::OK,
                        [System.Windows.Forms.MessageBoxIcon]::Information
                    )
                } else {
                    # Отклоняем
                    $consentBody = @{ action = "decline" } | ConvertTo-Json
                    Invoke-RestMethod -Uri "$siemUrl/api/v1/ad/peer-help/$token/consent" -Method Post -Body $consentBody -ContentType "application/json"
                }

                break
            }
        } catch {
            # Игнорируем ошибки проверки
        }
    }

} catch {
    [System.Windows.Forms.MessageBox]::Show(
        "Ошибка: $($_.Exception.Message)",
        "Ошибка",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    )
}
