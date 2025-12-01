# SIEM Database - MS SQL Server

Схема базы данных для SIEM-системы с соответствием требованиям ЦБ РФ (683-П, 716-П, 747-П, ГОСТ Р 57580).

## 📋 Содержание

- [Обзор](#обзор)
- [Требования](#требования)
- [Установка](#установка)
- [Структура базы данных](#структура-базы-данных)
- [Безопасность и соответствие](#безопасность-и-соответствие)
- [Обслуживание](#обслуживание)
- [Производительность](#производительность)

## 🎯 Обзор

База данных SIEM_DB включает:

- **18 таблиц** для событий безопасности, алертов, инцидентов, активов, отчётности
- **Партиционирование** событий по месяцам (3 года вперёд)
- **Columnstore индексы** для быстрой аналитики
- **Сжатие данных** (PAGE/COLUMNSTORE_ARCHIVE)
- **Триггеры защиты** от изменения/удаления критичных данных
- **Хранимые процедуры** для высокопроизводительных операций
- **SQL Agent Jobs** для автоматического обслуживания

### Ключевые особенности

✅ **Соответствие ЦБ РФ:**
- Хранение событий минимум 5 лет (683-П)
- Неизменяемость событий и audit log (ГОСТ Р 57580)
- Классификация по категориям операционного риска (716-П)
- Экспорт для ФинЦЕРТ и форма 0403203 (747-П)

✅ **Производительность:**
- Обработка 10,000+ событий/сек
- Columnstore для быстрых аналитических запросов
- Партиционирование для оптимизации хранения
- Batch-вставка событий

✅ **Безопасность:**
- Контрольные суммы (SHA256) для защиты целостности
- Запрет UPDATE/DELETE на события и audit log
- Полный аудит всех действий пользователей
- RBAC (admin, analyst, viewer)

## 📦 Требования

### Минимальные системные требования

- **MS SQL Server:** 2017+ (Standard или Enterprise)
- **Версия:** Рекомендуется 2019/2022 для лучшей производительности
- **Редакция:** Standard (минимум) / Enterprise (рекомендуется для Columnstore)
- **RAM:** Минимум 16 GB (рекомендуется 32+ GB)
- **Диск:**
  - Data: 500 GB+ SSD (для высокой нагрузки записи)
  - Log: 50 GB+ SSD
  - Backup: 1 TB+ (зависит от retention)
- **CPU:** 4+ ядра

### Необходимые компоненты

- SQL Server Agent (для автоматических задач)
- Full-Text Search (опционально, для расширенного поиска)

## 🚀 Установка

### Шаг 1: Подготовка сервера

```powershell
# Проверка версии SQL Server
SELECT @@VERSION;

# Проверка доступной памяти
SELECT
    physical_memory_kb / 1024 / 1024 AS RAM_GB
FROM sys.dm_os_sys_info;

# Проверка дисков
EXEC xp_fixeddrives;
```

### Шаг 2: Создание схемы базы данных

**⚠️ ВАЖНО:** Отредактируйте `schema.sql` перед выполнением!

Измените пути к файлам данных и логов:

```sql
-- В файле schema.sql найдите и измените:
FILENAME = 'D:\MSSQL\Data\SIEM_Data.mdf'  -- Ваш путь
FILENAME = 'D:\MSSQL\Logs\SIEM_Log.ldf'   -- Ваш путь
```

Выполните скрипты в следующем порядке:

```powershell
# 1. Создание схемы и таблиц
sqlcmd -S localhost -i schema.sql -o schema_output.log

# 2. Создание хранимых процедур
sqlcmd -S localhost -i procedures.sql -o procedures_output.log

# 3. Создание триггеров защиты
sqlcmd -S localhost -i triggers.sql -o triggers_output.log

# 4. Загрузка начальных данных
sqlcmd -S localhost -i seed.sql -o seed_output.log

# 5. Создание SQL Agent Jobs
sqlcmd -S localhost -i jobs.sql -o jobs_output.log
```

Или через SQL Server Management Studio (SSMS):
1. Откройте файл `schema.sql`
2. Измените пути к файлам
3. Выполните (F5)
4. Повторите для остальных файлов по порядку

### Шаг 3: Создание пользователя приложения

```sql
USE master;
GO

-- Создание SQL Login для приложения
CREATE LOGIN siem_app WITH PASSWORD = 'СИЛЬНЫЙ_ПАРОЛЬ_ЗДЕСЬ';
GO

USE SIEM_DB;
GO

-- Создание пользователя в БД
CREATE USER siem_app FOR LOGIN siem_app;
GO

-- Выдача прав
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::security_events TO siem_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::config TO siem_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::incidents TO siem_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::assets TO siem_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::compliance TO siem_app;

-- Права на выполнение процедур
GRANT EXECUTE TO siem_app;
GO

PRINT 'Пользователь siem_app создан и настроен';
```

### Шаг 4: Проверка установки

```sql
USE SIEM_DB;
GO

-- Проверка созданных таблиц
SELECT
    s.name AS SchemaName,
    t.name AS TableName,
    p.rows AS RowCount
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.partitions p ON t.object_id = p.object_id
WHERE p.index_id IN (0,1)
ORDER BY s.name, t.name;

-- Проверка пользователей по умолчанию
SELECT UserId, Username, Role, IsActive FROM config.Users;

-- Проверка настроек
SELECT SettingKey, SettingValue FROM config.Settings WHERE SettingKey IN (
    'retention_days', 'ai_enabled', 'cbr_reporting_enabled'
);

-- Проверка правил детекции
SELECT RuleId, RuleName, IsEnabled, Severity FROM config.DetectionRules;

-- Проверка SQL Agent Jobs
SELECT name, enabled FROM msdb.dbo.sysjobs WHERE name LIKE 'SIEM_%';
```

## 📊 Структура базы данных

### Схемы

| Схема | Назначение |
|-------|-----------|
| `security_events` | События безопасности (основная таблица) |
| `config` | Конфигурация (пользователи, правила, настройки) |
| `incidents` | Алерты и инциденты |
| `assets` | Активы и инвентаризация ПО |
| `compliance` | Отчётность для ЦБ РФ и audit log |

### Основные таблицы

#### security_events.Events
Главная таблица событий безопасности. Партиционирована по месяцам.

**Размер:** ~10-50 млн записей на 100 хостов в месяц
**Хранение:** 5 лет (1825 дней)
**Индексы:** 10 nonclustered + 1 columnstore

Ключевые поля:
- `EventId` (BIGINT) - PK
- `EventGuid` (UNIQUEIDENTIFIER) - Глобально уникальный
- `EventTime` (DATETIME2) - Время события (для партиционирования)
- `AgentId` (UNIQUEIDENTIFIER) - FK к assets.Agents
- `Severity` (TINYINT) - 0-info, 1-low, 2-medium, 3-high, 4-critical
- `Category` (VARCHAR) - Категория события
- `RawEvent` (NVARCHAR(MAX)) - Исходное событие JSON
- `AIScore`, `AIDescription` - Результаты AI-анализа
- `EventHash` (computed) - SHA256 для защиты целостности

#### assets.Agents
Зарегистрированные агенты (хосты).

**Размер:** 100-10,000 записей

Ключевые поля:
- `AgentId` (UNIQUEIDENTIFIER) - PK
- `Hostname`, `FQDN`, `IPAddress`
- `OSVersion`, `Domain`
- `Status` (VARCHAR) - online, offline, error
- `LastSeen` (DATETIME2) - Последний heartbeat

#### assets.InstalledSoftware
Установленное ПО на всех хостах.

**Размер:** 50-500 записей на хост

Используется для:
- Инвентаризации активов
- Детекции запрещённого ПО
- Отчётов о лицензиях
- Алертов на изменения

#### incidents.Alerts
Сработавшие правила детекции.

**Размер:** 1,000-100,000 в месяц

Ключевые поля:
- `AlertId` (BIGINT) - PK
- `RuleId` (INT) - FK к config.DetectionRules
- `Severity`, `Title`, `Description`
- `EventIds` (JSON) - Связанные события
- `Status` - new, acknowledged, investigating, resolved, false_positive
- `AssignedTo` (INT) - FK к config.Users
- `AIAnalysis`, `AIRecommendations` - Анализ от Yandex GPT

#### incidents.Incidents
Группы связанных алертов.

**Размер:** 10-1,000 в месяц

Используется для:
- Корреляции алертов
- Timeline инцидентов
- Отчётов для ЦБ РФ
- Расследований

#### compliance.CBRReports
История экспортов для ЦБ РФ.

**Хранение:** Постоянное (не удаляется)

Форматы:
- `form_0403203` - Форма 0403203
- `fincert_notification` - Уведомление в ФинЦЕРТ
- `operational_risk` - Отчёт по операционным рискам
- `incident_report` - Детальный отчёт об инциденте

#### compliance.AuditLog
Журнал всех действий пользователей.

**Размер:** ~1-10 млн записей в год
**Хранение:** 5 лет (требование ЦБ)
**Защита:** Запрет UPDATE/DELETE (триггеры)

## 🔒 Безопасность и соответствие

### Защита от изменений (триггеры)

```sql
-- Триггер запрета изменения событий
CREATE TRIGGER TR_Events_PreventUpdate
-- Разрешено только обновление AI-полей после обработки
-- Базовые поля (EventTime, AgentId, RawEvent) защищены

-- Триггер запрета удаления событий
CREATE TRIGGER TR_Events_PreventDelete
-- Удаление только через процедуру compliance.PurgeOldData

-- Триггер защиты audit log
CREATE TRIGGER TR_AuditLog_PreventUpdate
-- Audit log полностью неизменяем
```

### Контрольные суммы

```sql
-- События
EventHash = HASHBYTES('SHA2_256', EventId + EventTime + AgentId + RawEvent)

-- Audit log
LogHash = HASHBYTES('SHA2_256', LogId + CreatedAt + Action + Details)

-- Используется для проверки целостности при экспорте в ЦБ
```

### Роли пользователей

| Роль | Права |
|------|-------|
| `admin` | Полный доступ, управление пользователями, настройками |
| `analyst` | Просмотр событий, создание/редактирование алертов и инцидентов |
| `viewer` | Только просмотр событий и отчётов (read-only) |

## 🔧 Обслуживание

### SQL Agent Jobs

| Job | Расписание | Назначение |
|-----|-----------|-----------|
| `SIEM_DailyDataPurge` | Ежедневно 02:00 | Очистка событий старше retention period |
| `SIEM_WeeklyMaintenance` | Воскресенье 03:00 | Обновление статистики, rebuild индексов |
| `SIEM_CleanExpiredSessions` | Каждый час | Удаление истёкших сессий |
| `SIEM_MarkOfflineAgents` | Каждые 5 минут | Маркировка неактивных агентов |
| `SIEM_TransactionLogBackup` | Каждый час | Backup журнала транзакций |
| `SIEM_FullBackup` | Воскресенье 01:00 | Полный backup БД |

### Ручное обслуживание

```sql
-- Очистка старых данных
EXEC compliance.PurgeOldData @RetentionDays = 1825; -- 5 лет

-- Обновление статистики
UPDATE STATISTICS security_events.Events WITH FULLSCAN;

-- Проверка фрагментации индексов
SELECT
    OBJECT_NAME(ips.object_id) AS TableName,
    i.name AS IndexName,
    ips.avg_fragmentation_in_percent
FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') ips
JOIN sys.indexes i ON ips.object_id = i.object_id AND ips.index_id = i.index_id
WHERE ips.avg_fragmentation_in_percent > 10
ORDER BY ips.avg_fragmentation_in_percent DESC;

-- Rebuild фрагментированного индекса
ALTER INDEX IX_Events_AgentId ON security_events.Events REBUILD;
```

### Мониторинг размера БД

```sql
-- Размер таблиц
SELECT
    s.name AS SchemaName,
    t.name AS TableName,
    SUM(a.total_pages) * 8 / 1024 AS SizeMB,
    SUM(p.rows) AS RowCount
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.indexes i ON t.object_id = i.object_id
JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
JOIN sys.allocation_units a ON p.partition_id = a.container_id
GROUP BY s.name, t.name
ORDER BY SUM(a.total_pages) DESC;

-- Размер БД
EXEC sp_spaceused;

-- Размер log файла
DBCC SQLPERF(LOGSPACE);
```

## ⚡ Производительность

### Оптимизация запросов

**Используйте columnstore индекс для аналитики:**

```sql
-- Хороший запрос (использует columnstore)
SELECT
    Severity,
    Category,
    COUNT(*) AS EventCount
FROM security_events.Events
WHERE EventTime >= DATEADD(DAY, -7, GETUTCDATE())
GROUP BY Severity, Category;

-- Плохой запрос (требует полного сканирования RawEvent)
SELECT * FROM security_events.Events
WHERE RawEvent LIKE '%malware%';
```

**Используйте хранимые процедуры:**

```sql
-- Вместо сложного SELECT из приложения
EXEC security_events.GetDashboardStats @Hours = 24;

-- Batch insert вместо отдельных INSERT
EXEC security_events.InsertEventsBatch @Events = @JsonArray;
```

### Индексы

Созданные индексы оптимизированы для частых запросов:

- `IX_Events_AgentId` - события по хосту
- `IX_Events_Severity` - критичные события
- `IX_Events_SubjectUser` - события пользователя
- `IX_Events_SourceIP` - события по IP
- `NCCI_Events_Analytics` - columnstore для дашбордов

### Партиционирование

События партиционированы по месяцам. Преимущества:

- Быстрое удаление старых данных (DROP PARTITION вместо DELETE)
- Параллельные запросы к разным партициям
- Возможность архивации по партициям

```sql
-- Просмотр партиций
SELECT
    p.partition_number,
    f.name AS filegroup_name,
    p.rows AS row_count,
    au.total_pages * 8 / 1024 AS size_mb
FROM sys.partitions p
JOIN sys.allocation_units au ON p.partition_id = au.container_id
JOIN sys.filegroups f ON au.data_space_id = f.data_space_id
WHERE p.object_id = OBJECT_ID('security_events.Events')
ORDER BY p.partition_number;
```

## 📝 Примеры использования

### Поиск событий

```sql
-- Поиск с фильтрацией
EXEC security_events.SearchEvents
    @StartTime = '2025-12-01 00:00:00',
    @EndTime = '2025-12-01 23:59:59',
    @MinSeverity = 3, -- High и Critical
    @SubjectUser = 'john.doe',
    @Limit = 100;
```

### Создание алерта

```sql
DECLARE @AlertGuid UNIQUEIDENTIFIER;

EXEC incidents.CreateAlert
    @RuleId = 1,
    @Severity = 4,
    @Title = 'Brute force attack detected',
    @Description = 'Multiple failed login attempts from user john.doe',
    @EventIds = '[12345, 12346, 12347]',
    @AgentId = '...',
    @Username = 'john.doe',
    @AlertGuid = @AlertGuid OUTPUT;

SELECT @AlertGuid AS CreatedAlert;
```

### Статистика для дашборда

```sql
-- Полная статистика за последние 24 часа
EXEC security_events.GetDashboardStats @Hours = 24;

-- Возвращает 7 result sets:
-- 1. Общая статистика
-- 2. События по часам
-- 3. По категориям
-- 4. Топ хостов
-- 5. Статистика алертов
-- 6. Активные инциденты
-- 7. Топ MITRE тактики
```

### Экспорт для ЦБ

```sql
-- Создание отчёта 0403203
DECLARE @ReportData NVARCHAR(MAX) = (
    SELECT
        i.IncidentId,
        i.Title,
        i.Severity,
        i.StartTime,
        i.OperationalRiskCategory,
        i.EstimatedDamage_RUB
    FROM incidents.Incidents i
    WHERE i.Status NOT IN ('closed')
        AND i.IsReportedToCBR = 0
        AND i.Severity >= 3
    FOR JSON PATH
);

INSERT INTO compliance.CBRReports (
    ReportType, ReportData, ReportFormat, Status
) VALUES (
    'form_0403203', @ReportData, 'json', 'draft'
);
```

## 🆘 Troubleshooting

### Проблемы с производительностью

```sql
-- Проверка активных запросов
SELECT
    session_id,
    status,
    command,
    cpu_time,
    total_elapsed_time,
    reads,
    writes,
    TEXT
FROM sys.dm_exec_requests
CROSS APPLY sys.dm_exec_sql_text(sql_handle)
WHERE database_id = DB_ID('SIEM_DB');

-- Проверка блокировок
SELECT * FROM sys.dm_tran_locks
WHERE resource_database_id = DB_ID('SIEM_DB');

-- Top 10 медленных запросов
SELECT TOP 10
    qs.execution_count,
    qs.total_elapsed_time / qs.execution_count AS avg_time_ms,
    SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
        ((CASE qs.statement_end_offset
            WHEN -1 THEN DATALENGTH(st.text)
            ELSE qs.statement_end_offset
        END - qs.statement_start_offset)/2) + 1) AS query_text
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
ORDER BY avg_time_ms DESC;
```

### Проблемы с местом на диске

```sql
-- Shrink log file (ОСТОРОЖНО в production!)
USE SIEM_DB;
GO
DBCC SHRINKFILE (SIEM_Log, 2048); -- Shrink to 2 GB

-- Переключение на Simple Recovery (если не нужен point-in-time recovery)
ALTER DATABASE SIEM_DB SET RECOVERY SIMPLE;
```

## 📞 Поддержка

При возникновении проблем:

1. Проверьте SQL Server Error Log
2. Проверьте SQL Agent Job History
3. Проверьте audit log: `SELECT TOP 100 * FROM compliance.AuditLog ORDER BY CreatedAt DESC`
4. Обратитесь к документации MS SQL Server

---

**Версия:** 1.0
**Дата:** 2025-12-01
**Соответствие:** ЦБ РФ 683-П, 716-П, 747-П, ГОСТ Р 57580
