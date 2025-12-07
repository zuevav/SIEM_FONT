# File Integrity Monitoring (FIM) - Настройка и использование

## Обзор

File Integrity Monitoring (FIM) - это функция мониторинга изменений файлов и реестра Windows в реальном времени для детекции несанкционированных модификаций, backdoors, и persistence механизмов.

SIEM использует **Sysmon** для FIM мониторинга:
- Создание/удаление файлов в критичных директориях
- Модификация ключей автозапуска Windows
- Изменения системных файлов (hosts, Task Scheduler)
- Хеширование файлов для integrity verification

---

## Архитектура FIM

```
┌──────────────────────────────────────────────────────────────┐
│                    Windows Host                               │
│                                                               │
│  ┌──────────────┐        ┌────────────────────────────┐      │
│  │   Sysmon     │───────>│  Windows Event Log         │      │
│  │              │        │  (Sysmon/Operational)      │      │
│  │  Event 11    │        └────────────────────────────┘      │
│  │  Event 23    │                     │                      │
│  │  Event 26    │                     ▼                      │
│  │  Event 12-14 │        ┌────────────────────────────┐      │
│  └──────────────┘        │   SIEM Windows Agent       │      │
│                          │   (Go collector)           │      │
│                          └────────────────────────────┘      │
└────────────────────────────────┬─────────────────────────────┘
                                 │
                                 ▼ HTTPS/JSON
                ┌────────────────────────────────────┐
                │        SIEM Backend                │
                │   ┌────────────────────────┐      │
                │   │  FIM API Endpoints     │      │
                │   │  /api/v1/fim/events    │      │
                │   │  /api/v1/fim/stats     │      │
                │   └────────────────────────┘      │
                │   ┌────────────────────────┐      │
                │   │  Detection Rules       │      │
                │   │  (6 FIM rules)         │      │
                │   └────────────────────────┘      │
                │   ┌────────────────────────┐      │
                │   │  SOAR Playbooks        │      │
                │   │  (FIM Response)        │      │
                │   └────────────────────────┘      │
                └────────────────────────────────────┘
                                 │
                                 ▼
                ┌────────────────────────────────────┐
                │        SIEM Frontend UI            │
                │   /fim - FIM Events Viewer         │
                │   - Statistics Dashboard           │
                │   - File/Registry changes table    │
                │   - Filtering and search           │
                └────────────────────────────────────┘
```

---

## Установка и настройка Sysmon

### Шаг 1: Скачивание Sysmon

```powershell
# Скачайте Sysmon с официального сайта
Invoke-WebRequest -Uri "https://download.sysinternals.com/files/Sysmon.zip" -OutFile "C:\Temp\Sysmon.zip"

# Распакуйте
Expand-Archive -Path "C:\Temp\Sysmon.zip" -DestinationPath "C:\Temp\Sysmon"
```

### Шаг 2: Скачивание конфигурации Sysmon

Рекомендуется использовать **SwiftOnSecurity Sysmon Config** - проверенную конфигурацию для FIM:

```powershell
# Скачайте конфигурацию
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/SwiftOnSecurity/sysmon-config/master/sysmonconfig-export.xml" -OutFile "C:\Temp\sysmonconfig.xml"
```

### Шаг 3: Установка Sysmon

```powershell
# Откройте PowerShell как Администратор
cd C:\Temp\Sysmon

# Установите Sysmon с конфигурацией
.\Sysmon64.exe -accepteula -i C:\Temp\sysmonconfig.xml

# Проверьте установку
Get-Service Sysmon64

# Проверьте Event Log
Get-WinEvent -LogName "Microsoft-Windows-Sysmon/Operational" -MaxEvents 10
```

### Шаг 4: Кастомная конфигурация для FIM (опционально)

Создайте `C:\Sysmon\sysmon-fim-config.xml` для фокусировки на FIM:

```xml
<Sysmon schemaversion="4.90">
  <EventFiltering>

    <!-- Event ID 11: File Created -->
    <FileCreate onmatch="include">
      <!-- Системные директории -->
      <TargetFilename condition="begin with">C:\Windows\System32\</TargetFilename>
      <TargetFilename condition="begin with">C:\Windows\SysWOW64\</TargetFilename>
      <TargetFilename condition="begin with">C:\Program Files\</TargetFilename>
      <TargetFilename condition="begin with">C:\Program Files (x86)\</TargetFilename>

      <!-- Temp директории (exe, dll, scr) -->
      <TargetFilename condition="contains">\Temp\</TargetFilename>
      <TargetFilename condition="contains">\AppData\Local\Temp\</TargetFilename>

      <!-- Критичные файлы -->
      <TargetFilename condition="end with">\drivers\etc\hosts</TargetFilename>
      <TargetFilename condition="end with">\System32\Tasks\</TargetFilename>

      <!-- Исполняемые файлы -->
      <TargetFilename condition="end with">.exe</TargetFilename>
      <TargetFilename condition="end with">.dll</TargetFilename>
      <TargetFilename condition="end with">.sys</TargetFilename>
      <TargetFilename condition="end with">.scr</TargetFilename>
      <TargetFilename condition="end with">.bat</TargetFilename>
      <TargetFilename condition="end with">.cmd</TargetFilename>
      <TargetFilename condition="end with">.ps1</TargetFilename>
    </FileCreate>

    <!-- Event ID 23: File Delete -->
    <FileDelete onmatch="include">
      <TargetFilename condition="begin with">C:\Windows\System32\</TargetFilename>
      <TargetFilename condition="begin with">C:\Windows\SysWOW64\</TargetFilename>
    </FileDelete>

    <!-- Event ID 26: File Delete Detected -->
    <FileDeleteDetected onmatch="include">
      <TargetFilename condition="begin with">C:\Windows\System32\</TargetFilename>
      <TargetFilename condition="begin with">C:\Program Files\</TargetFilename>
    </FileDeleteDetected>

    <!-- Event ID 12: Registry Object Added/Deleted -->
    <RegistryEvent onmatch="include">
      <!-- Автозапуск -->
      <TargetObject condition="contains">\CurrentVersion\Run</TargetObject>
      <TargetObject condition="contains">\CurrentVersion\RunOnce</TargetObject>
      <TargetObject condition="contains">\Winlogon\</TargetObject>
      <TargetObject condition="contains">\Explorer\</TargetObject>

      <!-- Services -->
      <TargetObject condition="contains">CurrentControlSet\Services\</TargetObject>

      <!-- Image File Execution Options (debugger hijacking) -->
      <TargetObject condition="contains">\Image File Execution Options\</TargetObject>
    </RegistryEvent>

    <!-- Event ID 13: Registry Value Set -->
    <RegistryEvent onmatch="include">
      <TargetObject condition="contains">\CurrentVersion\Run</TargetObject>
      <TargetObject condition="contains">\CurrentVersion\RunOnce</TargetObject>
      <TargetObject condition="contains">\Winlogon\</TargetObject>
    </RegistryEvent>

    <!-- Event ID 14: Registry Key Renamed -->
    <RegistryEvent onmatch="include">
      <TargetObject condition="contains">\CurrentVersion\Run</TargetObject>
    </RegistryEvent>

    <!-- Event ID 1: Process Creation (с хешами для корреляции) -->
    <ProcessCreate onmatch="include">
      <Image condition="begin with">C:\Windows\Temp\</Image>
      <Image condition="contains">\AppData\Local\Temp\</Image>
    </ProcessCreate>

    <!-- Event ID 3: Network Connection (корреляция с файлами) -->
    <NetworkConnect onmatch="include">
      <DestinationPort condition="is">4444</DestinationPort>
      <DestinationPort condition="is">5555</DestinationPort>
    </NetworkConnect>

  </EventFiltering>
</Sysmon>
```

Примените конфигурацию:

```powershell
.\Sysmon64.exe -c C:\Sysmon\sysmon-fim-config.xml
```

---

## Sysmon Event IDs для FIM

| Event ID | Описание | Данные | Использование |
|----------|----------|--------|---------------|
| **1** | Process Creation | Image, CommandLine, Hashes, ParentImage | Корреляция процессов с файлами |
| **3** | Network Connection | SourceIP, DestinationIP, DestinationPort | Корреляция сетевых подключений |
| **11** | File Created | TargetFilename, Hashes, CreationUtcTime | **Основной FIM - создание файлов** |
| **12** | Registry Object Added/Deleted | TargetObject, EventType (CreateKey/DeleteKey) | **Реестр - создание/удаление ключей** |
| **13** | Registry Value Set | TargetObject, Details (значение) | **Реестр - установка значений** |
| **14** | Registry Key Renamed | TargetObject, NewName | **Реестр - переименование** |
| **23** | File Deleted | TargetFilename, Hashes, Archived | **FIM - удаление файлов (archived)** |
| **26** | File Delete Detected | TargetFilename, Hashes | **FIM - обнаружено удаление** |

---

## SIEM Detection Rules для FIM

SIEM содержит 6 правил детекции для FIM:

### Rule 14: Создание файла в системной папке

```sql
rule_id: 14
rule_name: "Sysmon FIM: Создание файла в системной папке"
severity: High (3)
rule_type: simple
rule_logic: {
  "provider": "Sysmon",
  "event_code": 11,
  "file_path_contains": [
    "\\Windows\\System32\\",
    "\\Windows\\SysWOW64\\",
    "\\Windows\\",
    "\\Program Files\\"
  ]
}
mitre_tactic: Persistence
mitre_technique: T1543
```

### Rule 15: Удаление системного файла

```sql
rule_id: 15
rule_name: "Sysmon FIM: Удаление системного файла"
severity: Critical (4)
rule_type: simple
rule_logic: {
  "provider": "Sysmon",
  "event_code": 23,
  "file_path_contains": [
    "\\Windows\\System32\\",
    "\\Windows\\SysWOW64\\"
  ]
}
mitre_tactic: Defense Evasion
mitre_technique: T1070.004
```

### Rule 16: Изменение автозапуска через реестр

```sql
rule_id: 16
rule_name: "Sysmon FIM: Изменение автозапуска через реестр"
severity: High (3)
rule_type: simple
rule_logic: {
  "provider": "Sysmon",
  "event_code": 13,
  "registry_key_contains": [
    "\\CurrentVersion\\Run",
    "\\CurrentVersion\\RunOnce",
    "\\Winlogon\\",
    "\\Explorer\\"
  ]
}
mitre_tactic: Persistence
mitre_technique: T1547.001
```

### Rule 17: Исполняемый файл в Temp

```sql
rule_id: 17
rule_name: "Sysmon FIM: Исполняемый файл в Temp"
severity: Medium (2)
rule_type: simple
rule_logic: {
  "provider": "Sysmon",
  "event_code": 11,
  "file_path_contains": ["\\Temp\\", "\\AppData\\Local\\Temp\\"],
  "file_path_ends_with": [".exe", ".dll", ".scr", ".bat", ".ps1"]
}
mitre_tactic: Execution
mitre_technique: T1204
```

### Rule 18: Изменение hosts файла

```sql
rule_id: 18
rule_name: "Sysmon FIM: Изменение файла hosts"
severity: High (3)
rule_type: simple
rule_logic: {
  "provider": "Sysmon",
  "event_code": 11,
  "file_path_contains": ["\\system32\\drivers\\etc\\hosts"]
}
mitre_tactic: Defense Evasion
mitre_technique: T1565.001
```

### Rule 19: Создание планировщика задач

```sql
rule_id: 19
rule_name: "Sysmon FIM: Новая задача в планировщике"
severity: High (3)
rule_type: simple
rule_logic: {
  "provider": "Sysmon",
  "event_code": 11,
  "file_path_contains": ["\\Windows\\System32\\Tasks\\"]
}
mitre_tactic: Persistence
mitre_technique: T1053.005
```

---

## SIEM UI - File Integrity Monitoring

### Доступ к FIM UI

1. Откройте SIEM Web UI: `http://siem-server:3000`
2. Перейдите в **SOAR** → **FIM**
3. Или напрямую: `http://siem-server:3000/fim`

### Возможности UI

#### 1. Statistics Dashboard

Карточки со статистикой:
- **Всего событий** - общее количество FIM событий
- **Критичных изменений** - события с severity >= 3
- **Файлов создано** - Event ID 11
- **Файлов удалено** - Event ID 23 + 26

#### 2. Фильтры

- **Период**: Последний час / 6 часов / 24 часа / 3 дня / Неделя
- **Тип события**:
  - Файл создан (Event ID 11)
  - Файл удален (Event ID 23, 26)
  - Ключ реестра создан/удален (Event ID 12)
  - Значение реестра установлено (Event ID 13)
  - Ключ реестра переименован (Event ID 14)
- **Путь файла или реестра** - частичное совпадение
- **Процесс** - имя процесса, создавшего изменение
- **Хост** - hostname

#### 3. Таблица событий

Колонки:
- **Время** - timestamp события
- **Тип** - тип FIM события с иконкой
- **Хост** - hostname
- **Путь** - путь к файлу или ключу реестра
- **Процесс** - процесс, создавший изменение
- **Пользователь** - пользователь
- **Severity** - уровень критичности
- **Действия** - кнопка "Детали"

#### 4. Модальное окно деталей

Подробная информация о событии:
- Event ID, Event Type, Hostname, Agent ID
- Severity, Category, Message
- **Файл**: путь, хеш (SHA256/MD5)
- **Реестр**: ключ, значение, детали, операция
- **Процесс**: имя, PID, command line
- **Пользователь**: target user, subject user
- **Raw event data** (JSON)

### Пример использования

**Сценарий: Поиск изменений в автозапуске**

1. Откройте **/fim**
2. Фильтры:
   - Период: Последние 24 часа
   - Тип события: "Значение реестра установлено"
   - Путь: "Run" (частичное совпадение)
3. Нажмите "Обновить"
4. В таблице увидите все изменения в ключах автозапуска
5. Кликните "Детали" для просмотра:
   - Какой процесс внес изменение
   - Какое значение было установлено
   - Какой пользователь это сделал
   - Полный путь в реестре

---

## SOAR Playbook для FIM

### Playbook 8: FIM Critical File Change Response

При детекции критичного изменения файла/реестра (Rule 14-19), автоматически запускается playbook:

#### Триггеры:
- Severity: High (3) или Critical (4)
- MITRE Tactics: Persistence, Defense Evasion

#### Действия:

1. **Action: Send Email**
   - Кому: SOC команда
   - Тема: "🔒 FIM Alert: Critical file/registry change detected"
   - Содержимое:
     - Тип изменения (file created/deleted, registry modified)
     - Путь файла/реестра
     - Процесс и пользователь
     - Хост и время
     - Хеш файла (если доступен)

2. **Action: Create Ticket**
   - Система: FreeScout
   - Приоритет: High
   - Категория: File Integrity Monitoring
   - Описание: Детали FIM события

3. **Action: Send Slack Notification**
   - Канал: #security-alerts
   - Формат: 🔒 FIM: {file_path} modified by {process_name} on {hostname}

#### Approval не требуется
Playbook выполняется автоматически для уведомлений. Для блокирующих действий (kill process, quarantine file) требуется approval.

---

## Интерпретация FIM событий

### File Created (Event ID 11)

**Легитимные случаи:**
- Обновление Windows/software
- Антивирус создает карантинные файлы
- Пользователь устанавливает программу

**Подозрительные случаи:**
- .exe файл создан в C:\Windows\System32 не системным процессом
- Файл создан в Temp с подозрительным именем (random.exe)
- Скрипт .ps1/.bat создан в системной папке

**Пример alert:**
```
Sysmon FIM: File created: C:\Windows\System32\evil.exe
Process: powershell.exe
User: DOMAIN\user
Hash: SHA256=abc123...
Action: Investigate - potentially malware installation
```

### Registry Value Set (Event ID 13)

**Легитимные случаи:**
- Установка программы добавляет себя в автозапуск
- Пользователь настраивает Startup applications

**Подозрительные случаи:**
- Неизвестный процесс добавляет значение в Run/RunOnce
- Winlogon\Shell изменен не системой
- Explorer\Run добавлен скрипт .vbs/.js

**Пример alert:**
```
Sysmon FIM: Registry value set: HKLM\Software\Microsoft\Windows\CurrentVersion\Run\Malware
Value: C:\Users\Public\malware.exe
Process: cmd.exe
User: DOMAIN\user
Action: Investigate - potential persistence mechanism
```

### File Deleted (Event ID 23)

**Легитимные случаи:**
- Windows Update удаляет старые файлы
- Антивирус удаляет вредоносные файлы
- Деинсталляция программы

**Подозрительные случаи:**
- Удаление критичных системных файлов
- Массовое удаление файлов (ransomware)
- Удаление логов безопасности

**Пример alert:**
```
Sysmon FIM: System file deleted: C:\Windows\System32\important.dll
Process: malware.exe
User: DOMAIN\user
Action: CRITICAL - investigate immediately, possible sabotage
```

---

## Корреляция FIM с другими событиями

### Сценарий 1: Malware Persistence

**Цепочка событий:**
1. **Sysmon Event 11**: Создан файл `C:\Users\Public\backdoor.exe`
2. **Sysmon Event 13**: Добавлен ключ реестра `Run\Backdoor = C:\Users\Public\backdoor.exe`
3. **Sysmon Event 1**: Процесс `backdoor.exe` запущен
4. **Sysmon Event 3**: `backdoor.exe` подключается к C2 сервер 1.2.3.4:4444

**SIEM автоматически:**
- Создает alert "Sysmon FIM: Изменение автозапуска через реестр" (Rule 16)
- Корелирует с network connection
- Создает incident "Malware Persistence Detected"
- Запускает SOAR playbook "Kill Suspicious Process"

### Сценарий 2: DNS Hijacking

**Цепочка событий:**
1. **Sysmon Event 11**: Изменен файл `C:\Windows\System32\drivers\etc\hosts`
2. Добавлена запись: `127.0.0.1 bank.com`
3. **Windows Event 4663**: Object Access to hosts file
4. **Network Events**: Попытки подключения к bank.com блокируются

**SIEM автоматически:**
- Создает alert "Sysmon FIM: Изменение файла hosts" (Rule 18)
- Отправляет email SOC команде
- Создает тикет в FreeScout
- Рекомендует проверить содержимое hosts файла

### Сценарий 3: Scheduled Task Backdoor

**Цепочка событий:**
1. **Sysmon Event 11**: Создан файл `C:\Windows\System32\Tasks\UpdateCheck`
2. **Windows Event 4698**: Scheduled task created
3. **Sysmon Event 1**: Через час запущен процесс из task
4. **Sysmon Event 3**: Процесс подключается к внешнему IP

**SIEM автоматически:**
- Создает alert "Sysmon FIM: Новая задача в планировщике" (Rule 19)
- Коррелирует с Event 4698
- Создает incident "Suspicious Scheduled Task"
- Запускает playbook "FIM Critical File Change Response"

---

## Baseline и Whitelist

### Создание baseline

Для снижения false positives, создайте baseline легитимных изменений:

```sql
-- Создайте таблицу baseline
CREATE TABLE fim.file_baseline (
  id SERIAL PRIMARY KEY,
  file_path VARCHAR(500) NOT NULL,
  file_hash VARCHAR(128),
  process_name VARCHAR(255),
  last_seen TIMESTAMP NOT NULL DEFAULT NOW(),
  change_count INTEGER DEFAULT 1,
  is_whitelisted BOOLEAN DEFAULT FALSE
);

-- Наполните baseline из исторических данных (за последние 7 дней)
INSERT INTO fim.file_baseline (file_path, file_hash, process_name, last_seen, change_count, is_whitelisted)
SELECT
  FilePath,
  EventData->>'FileHash' as file_hash,
  ProcessName,
  MAX(EventTime) as last_seen,
  COUNT(*) as change_count,
  FALSE
FROM security_events.Events
WHERE SourceType = 'Sysmon'
  AND EventCode IN (11, 23, 26)
  AND EventTime >= NOW() - INTERVAL '7 days'
GROUP BY FilePath, EventData->>'FileHash', ProcessName
HAVING COUNT(*) > 5;  -- Только частые изменения

-- Whitelist известных процессов
UPDATE fim.file_baseline
SET is_whitelisted = TRUE
WHERE process_name IN (
  'MsMpEng.exe',        -- Windows Defender
  'TrustedInstaller.exe',
  'svchost.exe',
  'System',
  'msiexec.exe',        -- Windows Installer
  'wuauclt.exe'         -- Windows Update
);
```

### Применение whitelist в detection rules

Модифицируйте rules для исключения whitelisted процессов:

```sql
UPDATE config.detection_rules
SET rule_logic = jsonb_set(
  rule_logic,
  '{process_name_not_in}',
  '["MsMpEng.exe", "TrustedInstaller.exe", "svchost.exe", "System", "msiexec.exe", "wuauclt.exe"]'::jsonb
)
WHERE rule_id IN (14, 15, 16, 17, 18, 19);
```

---

## Troubleshooting

### Проблема: Sysmon события не появляются в SIEM

**Решение:**

1. Проверьте, что Sysmon служба запущена:
```powershell
Get-Service Sysmon64
```

2. Проверьте Event Log вручную:
```powershell
Get-WinEvent -LogName "Microsoft-Windows-Sysmon/Operational" -MaxEvents 10
```

3. Проверьте конфигурацию Sysmon:
```powershell
.\Sysmon64.exe -c
```

4. Проверьте, что SIEM Agent собирает Sysmon события:
```powershell
Get-Content "C:\ProgramData\SIEM\logs\agent.log" -Tail 50 | Select-String "Sysmon"
```

### Проблема: Слишком много FIM событий (шум)

**Решение:**

1. Настройте Sysmon конфигурацию для фильтрации:
```xml
<FileCreate onmatch="exclude">
  <!-- Исключите временные файлы браузеров -->
  <TargetFilename condition="contains">\AppData\Local\Google\Chrome\</TargetFilename>
  <TargetFilename condition="contains">\AppData\Local\Mozilla\Firefox\</TargetFilename>

  <!-- Исключите логи -->
  <TargetFilename condition="end with">.log</TargetFilename>
  <TargetFilename condition="end with">.tmp</TargetFilename>
</FileCreate>
```

2. Отключите менее критичные правила:
```sql
UPDATE config.detection_rules
SET is_enabled = FALSE
WHERE rule_id = 17;  -- Temp files rule
```

3. Увеличьте severity threshold для alerting

### Проблема: Не хватает дискового пространства (Event Log)

**Решение:**

1. Увеличьте размер Sysmon Event Log:
```powershell
wevtutil sl "Microsoft-Windows-Sysmon/Operational" /ms:1073741824  # 1 GB
```

2. Настройте автоочистку старых событий:
```powershell
wevtutil sl "Microsoft-Windows-Sysmon/Operational" /rt:false /ab:true
```

3. Агрегируйте события в SIEM и очищайте локальный лог

---

## Лучшие практики

### 1. Постепенное внедрение

- **Неделя 1**: Мониторинг без alerting (сбор baseline)
- **Неделя 2**: Включить alerting только на Critical severity
- **Неделя 3**: Добавить High severity alerts
- **Неделя 4**: Включить все правила

### 2. Регулярный review

- Еженедельно проверяйте топ файлов/процессов
- Ежемесячно обновляйте whitelist
- Квартально пересматривайте detection rules

### 3. Корреляция с другими событиями

FIM наиболее эффективен в связке с:
- Windows Security events (4663 Object Access, 4698 Scheduled Task)
- PowerShell logging
- Network connections
- Process creation

### 4. Retention policy

- FIM события могут генерировать большой объем данных
- Рекомендуется хранить:
  - Critical severity: 1 год
  - High severity: 6 месяцев
  - Medium/Low: 30 дней
- Агрегированную статистику: 5 лет (требование ЦБ РФ)

---

## Запросы для аналитики

### Топ файлов по количеству создания

```sql
SELECT
  FilePath,
  COUNT(*) as create_count,
  COUNT(DISTINCT ProcessName) as unique_processes,
  COUNT(DISTINCT Hostname) as unique_hosts
FROM security_events.Events
WHERE SourceType = 'Sysmon'
  AND EventCode = 11
  AND EventTime >= NOW() - INTERVAL '7 days'
GROUP BY FilePath
ORDER BY create_count DESC
LIMIT 20;
```

### Топ процессов, изменяющих реестр

```sql
SELECT
  ProcessName,
  COUNT(*) as registry_changes,
  COUNT(DISTINCT EventData->>'TargetObject') as unique_keys
FROM security_events.Events
WHERE SourceType = 'Sysmon'
  AND EventCode IN (12, 13, 14)
  AND EventTime >= NOW() - INTERVAL '1 day'
GROUP BY ProcessName
ORDER BY registry_changes DESC
LIMIT 20;
```

### Новые файлы в системных папках

```sql
SELECT
  EventTime,
  Hostname,
  FilePath,
  ProcessName,
  TargetUser,
  EventData->>'FileHash' as file_hash
FROM security_events.Events
WHERE SourceType = 'Sysmon'
  AND EventCode = 11
  AND (
    FilePath LIKE 'C:\Windows\System32\%' OR
    FilePath LIKE 'C:\Windows\SysWOW64\%'
  )
  AND EventTime >= NOW() - INTERVAL '1 day'
ORDER BY EventTime DESC;
```

---

## Дополнительные ресурсы

- **Sysmon Download**: https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon
- **SwiftOnSecurity Config**: https://github.com/SwiftOnSecurity/sysmon-config
- **Sysmon Community Guide**: https://github.com/trustedsec/SysmonCommunityGuide
- **MITRE ATT&CK**: https://attack.mitre.org/

---

**Дата создания:** 2025-12-07
**Версия документа:** 1.0
**Автор:** SIEM Development Team
