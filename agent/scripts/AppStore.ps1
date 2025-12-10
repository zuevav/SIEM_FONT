<#
.SYNOPSIS
    Магазин приложений SIEM - Клиентское приложение

.DESCRIPTION
    Этот скрипт позволяет пользователям просматривать доступные приложения
    и устанавливать их или отправлять запросы на установку администратору.

.NOTES
    Разместите ярлык на рабочем столе пользователя
#>

param(
    [string]$SiemUrl = "https://siem.company.local"
)

# Конфигурация
$ConfigFile = "$env:ProgramData\SIEM-Agent\config.yaml"
$AgentIdFile = "$env:ProgramData\SIEM-Agent\agent_id"

# Подключаем Windows Forms
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Глобальные переменные
$script:Apps = @()
$script:SelectedApp = $null
$script:AgentId = $null
$script:BaseUrl = $null

function Get-AgentId {
    if (Test-Path $AgentIdFile) {
        return (Get-Content $AgentIdFile -Raw).Trim()
    }
    return $null
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

function Get-UserInfo {
    $info = @{
        UserName = $env:USERNAME
        DisplayName = $env:USERNAME
        Department = ""
    }

    try {
        Add-Type -AssemblyName System.DirectoryServices.AccountManagement
        $user = [System.DirectoryServices.AccountManagement.UserPrincipal]::Current
        if ($user.DisplayName) { $info.DisplayName = $user.DisplayName }

        # Получаем отдел из AD
        $searcher = New-Object DirectoryServices.DirectorySearcher
        $searcher.Filter = "(&(objectClass=user)(sAMAccountName=$($env:USERNAME)))"
        $result = $searcher.FindOne()
        if ($result -and $result.Properties["department"]) {
            $info.Department = $result.Properties["department"][0]
        }
    } catch {
        # Игнорируем ошибки AD
    }

    return $info
}

function Invoke-ApiRequest {
    param(
        [string]$Endpoint,
        [string]$Method = "GET",
        [object]$Body = $null
    )

    $url = "$script:BaseUrl$Endpoint"

    try {
        $params = @{
            Uri = $url
            Method = $Method
            ContentType = "application/json"
            UseBasicParsing = $true
        }

        if ($Body) {
            $params.Body = ($Body | ConvertTo-Json -Depth 10)
        }

        return Invoke-RestMethod @params
    } catch {
        return $null
    }
}

function Get-Apps {
    param([string]$Category = "")

    $endpoint = "/api/v1/ad/appstore/apps/client?agent_id=$script:AgentId"
    if ($Category -and $Category -ne "Все категории") {
        $endpoint += "&category=$Category"
    }

    return Invoke-ApiRequest -Endpoint $endpoint
}

function Request-AppInstall {
    param(
        [int]$AppId,
        [string]$Reason
    )

    $userInfo = Get-UserInfo

    $body = @{
        app_id = $AppId
        agent_id = $script:AgentId
        computer_name = $env:COMPUTERNAME
        user_name = $userInfo.UserName
        user_display_name = $userInfo.DisplayName
        user_department = $userInfo.Department
        request_reason = $Reason
    }

    return Invoke-ApiRequest -Endpoint "/api/v1/ad/appstore/requests" -Method "POST" -Body $body
}

function Show-MainWindow {
    # Главное окно
    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Магазин приложений"
    $form.Size = New-Object System.Drawing.Size(900, 650)
    $form.StartPosition = "CenterScreen"
    $form.Font = New-Object System.Drawing.Font("Segoe UI", 10)
    $form.BackColor = [System.Drawing.Color]::White

    # Заголовок
    $headerPanel = New-Object System.Windows.Forms.Panel
    $headerPanel.Dock = "Top"
    $headerPanel.Height = 70
    $headerPanel.BackColor = [System.Drawing.Color]::FromArgb(0, 122, 255)
    $form.Controls.Add($headerPanel)

    $titleLabel = New-Object System.Windows.Forms.Label
    $titleLabel.Text = "Магазин приложений"
    $titleLabel.Font = New-Object System.Drawing.Font("Segoe UI", 18, [System.Drawing.FontStyle]::Bold)
    $titleLabel.ForeColor = [System.Drawing.Color]::White
    $titleLabel.Location = New-Object System.Drawing.Point(20, 20)
    $titleLabel.AutoSize = $true
    $headerPanel.Controls.Add($titleLabel)

    # Панель фильтров
    $filterPanel = New-Object System.Windows.Forms.Panel
    $filterPanel.Dock = "Top"
    $filterPanel.Height = 50
    $filterPanel.Padding = New-Object System.Windows.Forms.Padding(10, 10, 10, 5)
    $form.Controls.Add($filterPanel)

    $categoryLabel = New-Object System.Windows.Forms.Label
    $categoryLabel.Text = "Категория:"
    $categoryLabel.Location = New-Object System.Drawing.Point(10, 15)
    $categoryLabel.AutoSize = $true
    $filterPanel.Controls.Add($categoryLabel)

    $categoryCombo = New-Object System.Windows.Forms.ComboBox
    $categoryCombo.Location = New-Object System.Drawing.Point(100, 12)
    $categoryCombo.Size = New-Object System.Drawing.Size(200, 30)
    $categoryCombo.DropDownStyle = "DropDownList"
    $categoryCombo.Items.AddRange(@(
        "Все категории",
        "Офис",
        "Разработка",
        "Утилиты",
        "Мультимедиа",
        "Безопасность",
        "Коммуникации"
    ))
    $categoryCombo.SelectedIndex = 0
    $filterPanel.Controls.Add($categoryCombo)

    $refreshButton = New-Object System.Windows.Forms.Button
    $refreshButton.Text = "Обновить"
    $refreshButton.Location = New-Object System.Drawing.Point(320, 10)
    $refreshButton.Size = New-Object System.Drawing.Size(100, 32)
    $refreshButton.FlatStyle = "Flat"
    $refreshButton.BackColor = [System.Drawing.Color]::FromArgb(240, 240, 240)
    $filterPanel.Controls.Add($refreshButton)

    # Панель содержимого
    $contentPanel = New-Object System.Windows.Forms.SplitContainer
    $contentPanel.Dock = "Fill"
    $contentPanel.SplitterDistance = 550
    $contentPanel.Panel1MinSize = 300
    $contentPanel.Panel2MinSize = 250
    $form.Controls.Add($contentPanel)

    # Список приложений (ListView)
    $appList = New-Object System.Windows.Forms.ListView
    $appList.Dock = "Fill"
    $appList.View = "Details"
    $appList.FullRowSelect = $true
    $appList.GridLines = $true
    $appList.MultiSelect = $false
    $appList.Columns.Add("Название", 200)
    $appList.Columns.Add("Категория", 100)
    $appList.Columns.Add("Версия", 80)
    $appList.Columns.Add("Издатель", 150)
    $appList.Columns.Add("Статус", 100)
    $contentPanel.Panel1.Controls.Add($appList)

    # Панель деталей
    $detailsPanel = New-Object System.Windows.Forms.Panel
    $detailsPanel.Dock = "Fill"
    $detailsPanel.Padding = New-Object System.Windows.Forms.Padding(15)
    $detailsPanel.BackColor = [System.Drawing.Color]::FromArgb(248, 248, 248)
    $contentPanel.Panel2.Controls.Add($detailsPanel)

    $detailsTitle = New-Object System.Windows.Forms.Label
    $detailsTitle.Text = "Выберите приложение"
    $detailsTitle.Font = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Bold)
    $detailsTitle.Location = New-Object System.Drawing.Point(15, 15)
    $detailsTitle.Size = New-Object System.Drawing.Size(280, 30)
    $detailsPanel.Controls.Add($detailsTitle)

    $detailsVersion = New-Object System.Windows.Forms.Label
    $detailsVersion.Text = ""
    $detailsVersion.ForeColor = [System.Drawing.Color]::Gray
    $detailsVersion.Location = New-Object System.Drawing.Point(15, 45)
    $detailsVersion.AutoSize = $true
    $detailsPanel.Controls.Add($detailsVersion)

    $detailsPublisher = New-Object System.Windows.Forms.Label
    $detailsPublisher.Text = ""
    $detailsPublisher.ForeColor = [System.Drawing.Color]::Gray
    $detailsPublisher.Location = New-Object System.Drawing.Point(15, 65)
    $detailsPublisher.AutoSize = $true
    $detailsPanel.Controls.Add($detailsPublisher)

    $detailsDesc = New-Object System.Windows.Forms.TextBox
    $detailsDesc.Multiline = $true
    $detailsDesc.ReadOnly = $true
    $detailsDesc.ScrollBars = "Vertical"
    $detailsDesc.Location = New-Object System.Drawing.Point(15, 100)
    $detailsDesc.Size = New-Object System.Drawing.Size(280, 200)
    $detailsDesc.BackColor = [System.Drawing.Color]::White
    $detailsDesc.BorderStyle = "FixedSingle"
    $detailsPanel.Controls.Add($detailsDesc)

    $statusLabel = New-Object System.Windows.Forms.Label
    $statusLabel.Text = ""
    $statusLabel.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
    $statusLabel.Location = New-Object System.Drawing.Point(15, 310)
    $statusLabel.AutoSize = $true
    $detailsPanel.Controls.Add($statusLabel)

    $installButton = New-Object System.Windows.Forms.Button
    $installButton.Text = "Установить"
    $installButton.Location = New-Object System.Drawing.Point(15, 350)
    $installButton.Size = New-Object System.Drawing.Size(130, 40)
    $installButton.BackColor = [System.Drawing.Color]::FromArgb(52, 199, 89)
    $installButton.ForeColor = [System.Drawing.Color]::White
    $installButton.FlatStyle = "Flat"
    $installButton.FlatAppearance.BorderSize = 0
    $installButton.Enabled = $false
    $installButton.Visible = $false
    $detailsPanel.Controls.Add($installButton)

    $requestButton = New-Object System.Windows.Forms.Button
    $requestButton.Text = "Запросить"
    $requestButton.Location = New-Object System.Drawing.Point(155, 350)
    $requestButton.Size = New-Object System.Drawing.Size(130, 40)
    $requestButton.BackColor = [System.Drawing.Color]::FromArgb(0, 122, 255)
    $requestButton.ForeColor = [System.Drawing.Color]::White
    $requestButton.FlatStyle = "Flat"
    $requestButton.FlatAppearance.BorderSize = 0
    $requestButton.Enabled = $false
    $requestButton.Visible = $false
    $detailsPanel.Controls.Add($requestButton)

    # Статус-бар
    $statusBar = New-Object System.Windows.Forms.StatusStrip
    $statusBarLabel = New-Object System.Windows.Forms.ToolStripStatusLabel
    $statusBarLabel.Text = "Готов"
    $statusBar.Items.Add($statusBarLabel)
    $form.Controls.Add($statusBar)

    # Функция загрузки приложений
    $loadApps = {
        $statusBarLabel.Text = "Загрузка приложений..."
        $form.Refresh()

        $appList.Items.Clear()
        $script:Apps = Get-Apps -Category $categoryCombo.Text

        if ($script:Apps) {
            foreach ($app in $script:Apps) {
                $item = New-Object System.Windows.Forms.ListViewItem($app.display_name)
                $item.SubItems.Add($app.category)
                $item.SubItems.Add($app.version)
                $item.SubItems.Add($app.publisher)

                $status = if ($app.can_install) { "Доступно" }
                         elseif ($app.request_status -eq "pending") { "Ожидает" }
                         elseif ($app.request_status -eq "approved") { "Одобрено" }
                         elseif ($app.request_status -eq "denied") { "Отклонено" }
                         else { "По запросу" }
                $item.SubItems.Add($status)

                $item.Tag = $app

                # Цвет по статусу
                if ($app.can_install) {
                    $item.BackColor = [System.Drawing.Color]::FromArgb(232, 245, 233)
                } elseif ($app.request_status -eq "pending") {
                    $item.BackColor = [System.Drawing.Color]::FromArgb(255, 243, 224)
                } elseif ($app.request_status -eq "denied") {
                    $item.BackColor = [System.Drawing.Color]::FromArgb(255, 235, 238)
                }

                $appList.Items.Add($item)
            }
            $statusBarLabel.Text = "Загружено приложений: $($script:Apps.Count)"
        } else {
            $statusBarLabel.Text = "Не удалось загрузить приложения"
        }
    }

    # Функция обновления деталей
    $updateDetails = {
        param($app)

        $script:SelectedApp = $app
        $detailsTitle.Text = $app.display_name
        $detailsVersion.Text = "Версия: $($app.version)"
        $detailsPublisher.Text = "Издатель: $($app.publisher)"
        $detailsDesc.Text = $app.description

        $installButton.Visible = $false
        $requestButton.Visible = $false
        $installButton.Enabled = $false
        $requestButton.Enabled = $false

        if ($app.can_install) {
            $statusLabel.Text = "Можно установить"
            $statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(52, 199, 89)
            $installButton.Visible = $true
            $installButton.Enabled = $true
        } elseif ($app.request_status -eq "pending") {
            $statusLabel.Text = "Ожидает одобрения (#$($app.request_id))"
            $statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(255, 149, 0)
        } elseif ($app.request_status -eq "approved") {
            $statusLabel.Text = "Одобрено - можно установить"
            $statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(52, 199, 89)
            $installButton.Visible = $true
            $installButton.Enabled = $true
        } elseif ($app.request_status -eq "denied") {
            $statusLabel.Text = "Запрос отклонён"
            $statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(255, 59, 48)
            $requestButton.Text = "Запросить снова"
            $requestButton.Visible = $true
            $requestButton.Enabled = $true
        } else {
            $statusLabel.Text = "Требуется одобрение"
            $statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(0, 122, 255)
            $requestButton.Text = "Запросить"
            $requestButton.Visible = $true
            $requestButton.Enabled = $true
        }
    }

    # Обработчики событий
    $categoryCombo.Add_SelectedIndexChanged({ & $loadApps })
    $refreshButton.Add_Click({ & $loadApps })

    $appList.Add_SelectedIndexChanged({
        if ($appList.SelectedItems.Count -gt 0) {
            $app = $appList.SelectedItems[0].Tag
            & $updateDetails $app
        }
    })

    $installButton.Add_Click({
        if (-not $script:SelectedApp) { return }

        $result = [System.Windows.Forms.MessageBox]::Show(
            "Установить приложение '$($script:SelectedApp.display_name)'?",
            "Подтверждение установки",
            [System.Windows.Forms.MessageBoxButtons]::YesNo,
            [System.Windows.Forms.MessageBoxIcon]::Question
        )

        if ($result -eq [System.Windows.Forms.DialogResult]::Yes) {
            $statusBarLabel.Text = "Запуск установки..."
            $form.Refresh()

            # Запрашиваем информацию об установке
            $response = Request-AppInstall -AppId $script:SelectedApp.app_id -Reason "Прямая установка"

            if ($response -and $response.can_install -and $response.install_info) {
                $installInfo = $response.install_info

                try {
                    # Скачиваем установщик если нужно
                    $installerPath = $installInfo.installer_path
                    if (-not $installerPath -and $installInfo.installer_url) {
                        $tempPath = [System.IO.Path]::GetTempPath()
                        $installerPath = Join-Path $tempPath "siem_app_$($response.request_id).$($installInfo.installer_type)"

                        $statusBarLabel.Text = "Загрузка установщика..."
                        $form.Refresh()

                        Invoke-WebRequest -Uri $installInfo.installer_url -OutFile $installerPath -UseBasicParsing
                    }

                    $statusBarLabel.Text = "Установка..."
                    $form.Refresh()

                    # Запускаем установщик
                    switch ($installInfo.installer_type) {
                        "msi" {
                            $args = "/i `"$installerPath`" /qn /norestart"
                            if ($installInfo.silent_install_args) {
                                $args += " $($installInfo.silent_install_args)"
                            }
                            Start-Process "msiexec" -ArgumentList $args -Wait -NoNewWindow
                        }
                        "exe" {
                            $args = $installInfo.silent_install_args
                            if ($args) {
                                Start-Process $installerPath -ArgumentList $args -Wait -NoNewWindow
                            } else {
                                Start-Process $installerPath -Wait -NoNewWindow
                            }
                        }
                        "msix" {
                            Add-AppxPackage -Path $installerPath
                        }
                    }

                    # Сообщаем об успехе
                    Invoke-ApiRequest -Endpoint "/api/v1/ad/appstore/requests/$($response.request_id)/installed?exit_code=0" -Method "POST"

                    [System.Windows.Forms.MessageBox]::Show(
                        "Приложение '$($script:SelectedApp.display_name)' успешно установлено!",
                        "Установка завершена",
                        [System.Windows.Forms.MessageBoxButtons]::OK,
                        [System.Windows.Forms.MessageBoxIcon]::Information
                    )

                    $statusBarLabel.Text = "Установка завершена"

                } catch {
                    # Сообщаем об ошибке
                    Invoke-ApiRequest -Endpoint "/api/v1/ad/appstore/requests/$($response.request_id)/installed?exit_code=1&output=$($_.Exception.Message)" -Method "POST"

                    [System.Windows.Forms.MessageBox]::Show(
                        "Ошибка установки: $($_.Exception.Message)",
                        "Ошибка",
                        [System.Windows.Forms.MessageBoxButtons]::OK,
                        [System.Windows.Forms.MessageBoxIcon]::Error
                    )

                    $statusBarLabel.Text = "Ошибка установки"
                }
            } else {
                [System.Windows.Forms.MessageBox]::Show(
                    "Не удалось получить информацию для установки",
                    "Ошибка",
                    [System.Windows.Forms.MessageBoxButtons]::OK,
                    [System.Windows.Forms.MessageBoxIcon]::Error
                )
            }
        }
    })

    $requestButton.Add_Click({
        if (-not $script:SelectedApp) { return }

        # Показываем диалог запроса
        $reasonForm = New-Object System.Windows.Forms.Form
        $reasonForm.Text = "Запрос на установку"
        $reasonForm.Size = New-Object System.Drawing.Size(450, 280)
        $reasonForm.StartPosition = "CenterParent"
        $reasonForm.FormBorderStyle = "FixedDialog"
        $reasonForm.MaximizeBox = $false
        $reasonForm.MinimizeBox = $false
        $reasonForm.Font = New-Object System.Drawing.Font("Segoe UI", 10)

        $reasonLabel = New-Object System.Windows.Forms.Label
        $reasonLabel.Text = "Укажите причину запроса установки`n'$($script:SelectedApp.display_name)':"
        $reasonLabel.Location = New-Object System.Drawing.Point(20, 20)
        $reasonLabel.Size = New-Object System.Drawing.Size(400, 50)
        $reasonForm.Controls.Add($reasonLabel)

        $reasonTextBox = New-Object System.Windows.Forms.TextBox
        $reasonTextBox.Multiline = $true
        $reasonTextBox.Location = New-Object System.Drawing.Point(20, 75)
        $reasonTextBox.Size = New-Object System.Drawing.Size(395, 100)
        $reasonTextBox.ScrollBars = "Vertical"
        $reasonForm.Controls.Add($reasonTextBox)

        $submitBtn = New-Object System.Windows.Forms.Button
        $submitBtn.Text = "Отправить запрос"
        $submitBtn.Location = New-Object System.Drawing.Point(20, 190)
        $submitBtn.Size = New-Object System.Drawing.Size(150, 40)
        $submitBtn.BackColor = [System.Drawing.Color]::FromArgb(0, 122, 255)
        $submitBtn.ForeColor = [System.Drawing.Color]::White
        $submitBtn.FlatStyle = "Flat"
        $submitBtn.DialogResult = [System.Windows.Forms.DialogResult]::OK
        $reasonForm.Controls.Add($submitBtn)
        $reasonForm.AcceptButton = $submitBtn

        $cancelBtn = New-Object System.Windows.Forms.Button
        $cancelBtn.Text = "Отмена"
        $cancelBtn.Location = New-Object System.Drawing.Point(180, 190)
        $cancelBtn.Size = New-Object System.Drawing.Size(100, 40)
        $cancelBtn.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
        $reasonForm.Controls.Add($cancelBtn)
        $reasonForm.CancelButton = $cancelBtn

        $dialogResult = $reasonForm.ShowDialog($form)

        if ($dialogResult -eq [System.Windows.Forms.DialogResult]::OK) {
            $reason = $reasonTextBox.Text
            if (-not $reason) {
                $reason = "Требуется для работы"
            }

            $statusBarLabel.Text = "Отправка запроса..."
            $form.Refresh()

            $response = Request-AppInstall -AppId $script:SelectedApp.app_id -Reason $reason

            if ($response -and $response.request_id) {
                [System.Windows.Forms.MessageBox]::Show(
                    "Запрос на установку '$($script:SelectedApp.display_name)' отправлен!`n`nНомер запроса: #$($response.request_id)`nСтатус: $($response.status)`n`nВы получите уведомление когда запрос будет рассмотрен.",
                    "Запрос отправлен",
                    [System.Windows.Forms.MessageBoxButtons]::OK,
                    [System.Windows.Forms.MessageBoxIcon]::Information
                )

                # Обновляем список
                & $loadApps
            } else {
                [System.Windows.Forms.MessageBox]::Show(
                    "Не удалось отправить запрос. Попробуйте позже.",
                    "Ошибка",
                    [System.Windows.Forms.MessageBoxButtons]::OK,
                    [System.Windows.Forms.MessageBoxIcon]::Error
                )
            }

            $statusBarLabel.Text = "Готов"
        }
    })

    # Начальная загрузка
    & $loadApps

    $form.ShowDialog()
}

# Главный код
try {
    $script:AgentId = Get-AgentId
    $script:BaseUrl = Get-SiemUrl

    if (-not $script:AgentId) {
        [System.Windows.Forms.MessageBox]::Show(
            "SIEM-агент не установлен на этом компьютере.`n`nДля работы магазина приложений необходим установленный агент.",
            "Агент не найден",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Warning
        )
        exit 1
    }

    Show-MainWindow

} catch {
    [System.Windows.Forms.MessageBox]::Show(
        "Ошибка запуска магазина: $($_.Exception.Message)",
        "Ошибка",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    )
}
