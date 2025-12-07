# IPBan Integration - Настройка и мониторинг

## Обзор

IPBan - это бесплатный open-source инструмент для защиты Windows серверов от brute-force атак путем автоматической блокировки IP адресов после неудачных попыток входа.

SIEM система интегрируется с IPBan для:
- Мониторинга всех блокировок IP адресов
- Детекции массовых атак
- Корреляции с threat intelligence данными
- Автоматического реагирования через SOAR playbooks

---

## Что мониторит SIEM

### Event IDs IPBan

| Event ID | Описание | Severity | Детали |
|----------|----------|----------|--------|
| **1** | IP адрес заблокирован | Medium/High | SourceIP, UserName, FailedAttempts, BanReason |
| **2** | IP адрес разблокирован | Info | SourceIP |
| **3** | Обнаружена неудачная попытка входа | Low/Medium | SourceIP, UserName, Source (RDP/SSH/HTTP) |
| **4** | Изменение конфигурации IPBan | Medium | UserName, ConfigurationChange |
| **5** | Статус сервиса IPBan | Info | ServiceStatus (started/stopped) |

### Detection Rules

SIEM содержит 3 правила детекции для IPBan:

1. **Rule 11: Массовая блокировка IP адресов**
   - Триггер: >10 IP заблокировано за 5 минут
   - Severity: High (3)
   - Тип: Threshold
   - Действие: Автоматический запуск playbook "IPBan Mass Attack Response"

2. **Rule 12: IP адрес заблокирован**
   - Триггер: Любая блокировка IP (Event ID 1)
   - Severity: Medium (2)
   - Тип: Simple
   - Цель: Корреляция и статистика

3. **Rule 13: Повторные неудачные попытки входа**
   - Триггер: 5+ попыток с одного IP за 60 секунд (Event ID 3)
   - Severity: Medium (2)
   - Тип: Threshold
   - Цель: Детекция brute-force атак

---

## Установка IPBan на Windows

### Шаг 1: Скачивание IPBan

```powershell
# Скачайте последнюю версию с GitHub
Invoke-WebRequest -Uri "https://github.com/DigitalRuby/IPBan/releases/latest/download/IPBan-Windows-x64.zip" -OutFile "C:\Temp\IPBan.zip"

# Распакуйте в C:\IPBan
Expand-Archive -Path "C:\Temp\IPBan.zip" -DestinationPath "C:\IPBan"
```

### Шаг 2: Настройка IPBan

Отредактируйте `C:\IPBan\ipban.config`:

```xml
<?xml version="1.0"?>
<configuration>
  <!-- Файлы логирования -->
  <appSettings>
    <add key="LogFilePath" value="C:\IPBan\logfile.txt"/>
    <add key="LogLevel" value="Info"/>

    <!-- Порог блокировки -->
    <add key="FailedLoginAttemptsBeforeBan" value="5"/>
    <add key="BanTime" value="01:00:00:00"/> <!-- 1 день -->

    <!-- Whitelist -->
    <add key="Whitelist" value="192.168.1.0/24,10.0.0.0/8"/>

    <!-- Email уведомления (опционально) -->
    <add key="SmtpServer" value="smtp.company.com"/>
    <add key="SmtpPort" value="587"/>
    <add key="SmtpUsername" value="ipban@company.com"/>
    <add key="SmtpPassword" value="password"/>
    <add key="EmailFrom" value="ipban@company.com"/>
    <add key="EmailTo" value="admin@company.com"/>
  </appSettings>

  <!-- Логи для мониторинга -->
  <LogFilesToParse>
    <!-- RDP -->
    <LogFile>
      <PathAndMask>C:\Windows\System32\LogFiles\**\*.evtx</PathAndMask>
      <Source>RDP</Source>
      <PlatformRegex>Windows</PlatformRegex>
      <FailedLoginRegex><![CDATA[failed password|authentication failure|invalid user]]></FailedLoginRegex>
    </LogFile>

    <!-- SSH (если установлен OpenSSH) -->
    <LogFile>
      <PathAndMask>C:\ProgramData\ssh\logs\sshd.log</PathAndMask>
      <Source>SSH</Source>
      <FailedLoginRegex><![CDATA[Failed password|Invalid user]]></FailedLoginRegex>
    </LogFile>
  </LogFilesToParse>

  <!-- Правила firewall -->
  <FirewallRules>
    <FirewallRule>
      <Block>true</Block>
      <IPAddressRanges>0.0.0.0/0</IPAddressRanges>
    </FirewallRule>
  </FirewallRules>
</configuration>
```

### Шаг 3: Установка как Windows Service

```powershell
# Откройте PowerShell как Администратор
cd C:\IPBan

# Установите службу
.\IPBan.exe -install

# Запустите службу
Start-Service IPBan

# Проверьте статус
Get-Service IPBan
```

### Шаг 4: Настройка Event Log (для SIEM)

IPBan автоматически пишет события в Windows Event Log:
- **Application Log** → Source: "IPBan"

SIEM агент автоматически соберет эти события.

---

## Настройка SIEM Agent для сбора IPBan событий

### Конфигурация агента

Отредактируйте `C:\ProgramData\SIEM\agent.yaml`:

```yaml
# Event Log Configuration
eventlog:
  enabled: true

  # Каналы для мониторинга
  channels:
    - name: "Application"
      enabled: true
      # IPBan события пишутся в Application log

    - name: "Security"
      enabled: true

    - name: "System"
      enabled: true

  # Провайдеры для фильтрации
  providers:
    - "IPBan"           # Фильтр по провайдеру IPBan
    - "Microsoft-Windows-Security-Auditing"
    - "Microsoft-Windows-Sysmon"

  # Опционально: фильтр по Event IDs
  event_ids:
    IPBan:
      - 1    # IP banned
      - 2    # IP unbanned
      - 3    # Failed login detected
      - 4    # Configuration change
      - 5    # Service status

# Интервал сбора (секунды)
collection_interval: 10

# Server endpoint
server:
  url: "http://siem-server.company.local:8000"
  api_key: "your_api_key_here"
```

### Перезапуск агента

```powershell
Restart-Service SIEM-Agent
```

---

## Проверка работы интеграции

### 1. Генерация тестового события

```powershell
# Попытайтесь войти с неправильным паролем 5+ раз через RDP
# IPBan заблокирует IP и создаст Event ID 1

# Или используйте PowerShell для генерации события
New-EventLog -LogName Application -Source "IPBan" -ErrorAction SilentlyContinue

Write-EventLog -LogName Application -Source "IPBan" -EventId 1 -EntryType Warning `
  -Message "Test: IP 192.168.1.100 banned after 5 failed login attempts (User: testuser)"
```

### 2. Проверка в SIEM UI

1. Откройте SIEM Web UI: `http://siem-server:3000`
2. Перейдите в **События** → фильтр по Source Type = "IPBan"
3. Должны увидеть события IPBan с деталями:
   - Event ID
   - Source IP
   - Username
   - Failed Attempts
   - Ban Reason

### 3. Проверка алертов

1. Перейдите в **Алерты**
2. Если было заблокировано >10 IP за 5 минут, должен быть alert:
   - **IPBan: Массовая блокировка IP адресов** (Rule 11)
3. Каждая блокировка создает alert:
   - **IPBan: IP адрес заблокирован** (Rule 12)

### 4. Проверка SOAR Playbook

1. Перейдите в **SOAR** → **Выполнения**
2. Должны увидеть автоматический запуск playbook:
   - **IPBan Mass Attack Response**
3. Действия playbook:
   - Check Threat Intelligence (проверка IP в AbuseIPDB/VirusTotal)
   - Send Email (уведомление SOC)
   - Create Ticket (тикет в FreeScout)

---

## Логи IPBan

### Расположение логов

IPBan создает логи в:
```
C:\IPBan\logfile.txt              # Основной лог
C:\IPBan\logfile.txt.1            # Ротированный лог
C:\IPBan\nlog-internal.txt        # Внутренние логи NLog
```

### Формат логов

```
2025-12-07 15:30:45.123|INFO|IPBan|IP address 192.168.1.100 banned, user: administrator, failed login attempts: 7, ban reason: Failed RDP login
2025-12-07 15:31:10.456|INFO|IPBan|IP address 10.20.30.40 banned, user: root, failed login attempts: 12, ban reason: Failed SSH login
2025-12-07 16:00:00.789|INFO|IPBan|IP address 192.168.1.100 unbanned
```

### Мониторинг логов (опционально)

Если нужно собирать логи напрямую (а не через Event Log):

```yaml
# В agent.yaml добавьте file collector
file_collector:
  enabled: true
  files:
    - path: "C:\\IPBan\\logfile.txt"
      parser: "ipban"
      encoding: "utf-8"
```

---

## Whitelist - исключение IP адресов

### Через IPBan конфигурацию

Отредактируйте `C:\IPBan\ipban.config`:

```xml
<appSettings>
  <!-- Whitelist IP адресов (CIDR) -->
  <add key="Whitelist" value="192.168.1.0/24,10.0.0.0/8,172.16.0.0/12"/>

  <!-- Whitelist для отдельных IP -->
  <add key="Whitelist" value="8.8.8.8,1.1.1.1"/>
</appSettings>
```

### Через SIEM Detection Rules

Создайте исключение в SIEM:

1. Перейдите в **Правила** → Rule 12 ("IPBan: IP адрес заблокирован")
2. Добавьте whitelist в `rule_logic`:

```json
{
  "provider": "IPBan",
  "event_code": 1,
  "source_ip_not_in": ["192.168.1.0/24", "10.0.0.0/8"]
}
```

---

## Troubleshooting

### Проблема: События IPBan не появляются в SIEM

**Решение:**

1. Проверьте, что IPBan служба запущена:
```powershell
Get-Service IPBan
```

2. Проверьте Event Log вручную:
```powershell
Get-EventLog -LogName Application -Source IPBan -Newest 10
```

3. Проверьте, что SIEM Agent собирает Application log:
```powershell
# Проверьте логи агента
Get-Content "C:\ProgramData\SIEM\logs\agent.log" -Tail 50
```

4. Проверьте конфигурацию агента:
```powershell
Get-Content "C:\ProgramData\SIEM\agent.yaml"
```

### Проблема: IPBan блокирует легитимные IP

**Решение:**

1. Добавьте IP в whitelist (см. выше)
2. Увеличьте порог блокировки:
```xml
<add key="FailedLoginAttemptsBeforeBan" value="10"/>
```

3. Уменьшите время бана:
```xml
<add key="BanTime" value="00:01:00:00"/> <!-- 1 час вместо 1 дня -->
```

### Проблема: Слишком много алертов

**Решение:**

1. Увеличьте порог для Rule 11 (массовые блокировки):
```sql
UPDATE config.detection_rules
SET rule_logic = '{"provider": "IPBan", "event_code": 1, "count": 20, "time_window": 300}'
WHERE rule_id = 11;
```

2. Отключите Rule 12 (каждая блокировка):
```sql
UPDATE config.detection_rules
SET is_enabled = FALSE
WHERE rule_id = 12;
```

### Проблема: IPBan не блокирует атаки

**Решение:**

1. Проверьте firewall правила:
```powershell
Get-NetFirewallRule -DisplayName "*IPBan*"
```

2. Проверьте логи IPBan на ошибки:
```powershell
Get-Content "C:\IPBan\logfile.txt" -Tail 100 | Select-String "ERROR"
```

3. Убедитесь, что Event Log источники настроены правильно в `ipban.config`

---

## Статистика и отчёты

### Dashboard метрики

В SIEM Dashboard автоматически показываются:
- **Заблокированные IP за последние 24 часа**
- **Топ атакующих IP адресов**
- **География атак** (через GeoIP)
- **Топ пользователей по неудачным попыткам**

### Запросы для аналитики

```sql
-- Топ-10 заблокированных IP за последнюю неделю
SELECT
    SourceIP,
    COUNT(*) as ban_count,
    MIN(EventTime) as first_ban,
    MAX(EventTime) as last_ban
FROM security_events.Events
WHERE Provider = 'IPBan'
  AND EventCode = 1
  AND EventTime >= DATEADD(day, -7, GETDATE())
GROUP BY SourceIP
ORDER BY ban_count DESC
LIMIT 10;

-- Статистика по источникам атак (RDP vs SSH vs HTTP)
SELECT
    JSON_VALUE(EventData, '$.Source') as attack_source,
    COUNT(*) as attempts
FROM security_events.Events
WHERE Provider = 'IPBan'
  AND EventCode = 3
  AND EventTime >= DATEADD(day, -1, GETDATE())
GROUP BY JSON_VALUE(EventData, '$.Source')
ORDER BY attempts DESC;

-- Динамика блокировок по часам
SELECT
    DATEPART(hour, EventTime) as hour_of_day,
    COUNT(*) as bans
FROM security_events.Events
WHERE Provider = 'IPBan'
  AND EventCode = 1
  AND EventTime >= DATEADD(day, -7, GETDATE())
GROUP BY DATEPART(hour, EventTime)
ORDER BY hour_of_day;
```

---

## Интеграция с Threat Intelligence

SIEM автоматически обогащает IPBan события через:

1. **AbuseIPDB** - проверка IP репутации
2. **VirusTotal** - проверка вредоносных IP
3. **GeoIP** - определение страны/города

### Playbook "IPBan Mass Attack Response"

При детекции массовой блокировки (Rule 11), автоматически запускается playbook:

1. **Action: Check Threat Intelligence**
   - Проверяет каждый заблокированный IP в AbuseIPDB
   - Добавляет данные о репутации в событие

2. **Action: Send Email**
   - Отправляет email SOC команде
   - Тема: "🚨 IPBan Mass Attack: 15 IPs blocked in 5 minutes"
   - Содержимое: список IP, страны, threat intel данные

3. **Action: Create Ticket**
   - Создает тикет в FreeScout
   - Приоритет: High
   - Категория: Security Incident
   - Описание: детали атаки

---

## Лучшие практики

### 1. Настройка whitelist

Всегда добавляйте в whitelist:
- Внутренние сети (192.168.0.0/16, 10.0.0.0/8)
- VPN адреса
- Офисные статические IP
- Административные IP

### 2. Мониторинг критичных аккаунтов

Создайте отдельный alert для администраторов:

```sql
INSERT INTO config.detection_rules (rule_name, description, is_enabled, severity, priority, rule_type, rule_logic, mitre_attack_tactic, mitre_attack_technique, created_by, tags)
VALUES (
  'IPBan: Admin account brute-force',
  'Попытки взлома администраторских аккаунтов',
  TRUE,
  4, -- Critical
  5,
  'simple',
  '{"provider": "IPBan", "event_code": 1, "target_user_in": ["administrator", "admin", "root", "sa"]}'::jsonb,
  'Initial Access',
  'T1110',
  1,
  '["ipban", "admin", "brute_force", "critical"]'::jsonb
);
```

### 3. Регулярная проверка

- Еженедельно проверяйте топ атакующих IP
- Ежемесячно анализируйте тренды атак
- Корректируйте whitelist по необходимости

### 4. Координация с firewall

IPBan работает на уровне Windows Firewall. Для дополнительной защиты:
- Настройте fail2ban на Linux серверах
- Используйте perimeter firewall для глобальных блокировок
- Интегрируйте с Cisco/Fortinet для network-wide blocking

---

## Дополнительные ресурсы

- **IPBan GitHub**: https://github.com/DigitalRuby/IPBan
- **IPBan Documentation**: https://github.com/DigitalRuby/IPBan/wiki
- **MITRE ATT&CK T1110**: Brute Force (https://attack.mitre.org/techniques/T1110/)

---

**Дата создания:** 2025-12-07
**Версия документа:** 1.0
**Автор:** SIEM Development Team
