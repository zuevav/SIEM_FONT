-- =====================================================================
-- SIEM SQL AGENT JOBS
-- Задания для автоматического обслуживания системы
-- =====================================================================
-- Требования: SQL Server Agent должен быть запущен
-- =====================================================================

USE msdb;
GO

PRINT 'Создание SQL Agent Jobs для SIEM...';
GO

-- =====================================================================
-- JOB 1: Ежедневная очистка старых данных
-- =====================================================================

-- Удаляем job если существует
IF EXISTS (SELECT 1 FROM msdb.dbo.sysjobs WHERE name = 'SIEM_DailyDataPurge')
    EXEC msdb.dbo.sp_delete_job @job_name = 'SIEM_DailyDataPurge';
GO

-- Создаём job
EXEC msdb.dbo.sp_add_job
    @job_name = 'SIEM_DailyDataPurge',
    @enabled = 1,
    @description = 'Ежедневная очистка событий старше retention period (по умолчанию 5 лет для соответствия требованиям ЦБ)',
    @category_name = 'Database Maintenance';
GO

-- Добавляем шаг выполнения
EXEC msdb.dbo.sp_add_jobstep
    @job_name = 'SIEM_DailyDataPurge',
    @step_name = 'Purge Old Data',
    @subsystem = 'TSQL',
    @database_name = 'SIEM_DB',
    @command = N'
        DECLARE @RetentionDays INT;

        -- Получаем retention period из настроек
        SELECT @RetentionDays = CAST(SettingValue AS INT)
        FROM SIEM_DB.config.Settings
        WHERE SettingKey = ''retention_days'';

        -- По умолчанию 5 лет (требование ЦБ)
        IF @RetentionDays IS NULL OR @RetentionDays < 1825
            SET @RetentionDays = 1825;

        -- Выполняем очистку
        EXEC SIEM_DB.compliance.PurgeOldData
            @RetentionDays = @RetentionDays,
            @BatchSize = 10000,
            @MaxIterations = 1000;
    ',
    @retry_attempts = 3,
    @retry_interval = 5;
GO

-- Расписание: каждый день в 02:00 (низкая нагрузка)
EXEC msdb.dbo.sp_add_schedule
    @schedule_name = 'Daily_2AM',
    @freq_type = 4, -- Daily
    @freq_interval = 1,
    @active_start_time = 020000;
GO

-- Привязываем расписание к job
EXEC msdb.dbo.sp_attach_schedule
    @job_name = 'SIEM_DailyDataPurge',
    @schedule_name = 'Daily_2AM';
GO

-- Добавляем сервер
EXEC msdb.dbo.sp_add_jobserver
    @job_name = 'SIEM_DailyDataPurge';
GO

PRINT '  ✓ Job "SIEM_DailyDataPurge" создан (запуск: ежедневно в 02:00)';
GO

-- =====================================================================
-- JOB 2: Обновление статистики и индексов
-- =====================================================================

IF EXISTS (SELECT 1 FROM msdb.dbo.sysjobs WHERE name = 'SIEM_WeeklyMaintenance')
    EXEC msdb.dbo.sp_delete_job @job_name = 'SIEM_WeeklyMaintenance';
GO

EXEC msdb.dbo.sp_add_job
    @job_name = 'SIEM_WeeklyMaintenance',
    @enabled = 1,
    @description = 'Еженедельное обслуживание: обновление статистики, перестроение фрагментированных индексов',
    @category_name = 'Database Maintenance';
GO

EXEC msdb.dbo.sp_add_jobstep
    @job_name = 'SIEM_WeeklyMaintenance',
    @step_name = 'Update Statistics',
    @subsystem = 'TSQL',
    @database_name = 'SIEM_DB',
    @command = N'
        -- Обновление статистики для критичных таблиц
        UPDATE STATISTICS SIEM_DB.security_events.Events WITH FULLSCAN;
        UPDATE STATISTICS SIEM_DB.incidents.Alerts WITH FULLSCAN;
        UPDATE STATISTICS SIEM_DB.assets.InstalledSoftware WITH FULLSCAN;

        PRINT ''Статистика обновлена'';
    ',
    @retry_attempts = 2,
    @retry_interval = 10;
GO

EXEC msdb.dbo.sp_add_jobstep
    @job_name = 'SIEM_WeeklyMaintenance',
    @step_name = 'Rebuild Fragmented Indexes',
    @subsystem = 'TSQL',
    @database_name = 'SIEM_DB',
    @command = N'
        -- Перестраиваем индексы с фрагментацией > 30%
        DECLARE @sql NVARCHAR(MAX);

        DECLARE index_cursor CURSOR FOR
        SELECT
            ''ALTER INDEX ['' + i.name + ''] ON ['' + s.name + ''].['' + t.name + ''] REBUILD WITH (ONLINE = OFF);''
        FROM sys.dm_db_index_physical_stats(DB_ID(''SIEM_DB''), NULL, NULL, NULL, ''LIMITED'') AS ips
        JOIN sys.indexes i ON ips.object_id = i.object_id AND ips.index_id = i.index_id
        JOIN sys.tables t ON i.object_id = t.object_id
        JOIN sys.schemas s ON t.schema_id = s.schema_id
        WHERE ips.avg_fragmentation_in_percent > 30
            AND i.name IS NOT NULL
            AND ips.page_count > 1000; -- Только для больших индексов

        OPEN index_cursor;
        FETCH NEXT FROM index_cursor INTO @sql;

        WHILE @@FETCH_STATUS = 0
        BEGIN
            EXEC sp_executesql @sql;
            FETCH NEXT FROM index_cursor INTO @sql;
        END;

        CLOSE index_cursor;
        DEALLOCATE index_cursor;

        PRINT ''Индексы перестроены'';
    ',
    @retry_attempts = 1,
    @retry_interval = 15;
GO

-- Расписание: каждое воскресенье в 03:00
EXEC msdb.dbo.sp_add_schedule
    @schedule_name = 'Weekly_Sunday_3AM',
    @freq_type = 8, -- Weekly
    @freq_interval = 1, -- Sunday
    @freq_recurrence_factor = 1,
    @active_start_time = 030000;
GO

EXEC msdb.dbo.sp_attach_schedule
    @job_name = 'SIEM_WeeklyMaintenance',
    @schedule_name = 'Weekly_Sunday_3AM';
GO

EXEC msdb.dbo.sp_add_jobserver
    @job_name = 'SIEM_WeeklyMaintenance';
GO

PRINT '  ✓ Job "SIEM_WeeklyMaintenance" создан (запуск: воскресенье в 03:00)';
GO

-- =====================================================================
-- JOB 3: Деактивация истёкших сессий
-- =====================================================================

IF EXISTS (SELECT 1 FROM msdb.dbo.sysjobs WHERE name = 'SIEM_CleanExpiredSessions')
    EXEC msdb.dbo.sp_delete_job @job_name = 'SIEM_CleanExpiredSessions';
GO

EXEC msdb.dbo.sp_add_job
    @job_name = 'SIEM_CleanExpiredSessions',
    @enabled = 1,
    @description = 'Очистка истёкших сессий пользователей (каждый час)',
    @category_name = 'Database Maintenance';
GO

EXEC msdb.dbo.sp_add_jobstep
    @job_name = 'SIEM_CleanExpiredSessions',
    @step_name = 'Deactivate Expired Sessions',
    @subsystem = 'TSQL',
    @database_name = 'SIEM_DB',
    @command = N'
        -- Деактивируем истёкшие сессии
        UPDATE SIEM_DB.config.Sessions
        SET IsActive = 0
        WHERE ExpiresAt < GETUTCDATE() AND IsActive = 1;

        DECLARE @DeactivatedCount INT = @@ROWCOUNT;

        -- Удаляем старые неактивные сессии (старше 30 дней)
        DELETE FROM SIEM_DB.config.Sessions
        WHERE IsActive = 0 AND CreatedAt < DATEADD(DAY, -30, GETUTCDATE());

        PRINT ''Деактивировано сессий: '' + CAST(@DeactivatedCount AS VARCHAR);
        PRINT ''Удалено старых сессий: '' + CAST(@@ROWCOUNT AS VARCHAR);
    ',
    @retry_attempts = 3,
    @retry_interval = 1;
GO

-- Расписание: каждый час
EXEC msdb.dbo.sp_add_schedule
    @schedule_name = 'Hourly',
    @freq_type = 4, -- Daily
    @freq_interval = 1,
    @freq_subday_type = 8, -- Hours
    @freq_subday_interval = 1;
GO

EXEC msdb.dbo.sp_attach_schedule
    @job_name = 'SIEM_CleanExpiredSessions',
    @schedule_name = 'Hourly';
GO

EXEC msdb.dbo.sp_add_jobserver
    @job_name = 'SIEM_CleanExpiredSessions';
GO

PRINT '  ✓ Job "SIEM_CleanExpiredSessions" создан (запуск: каждый час)';
GO

-- =====================================================================
-- JOB 4: Маркировка офлайн агентов
-- =====================================================================

IF EXISTS (SELECT 1 FROM msdb.dbo.sysjobs WHERE name = 'SIEM_MarkOfflineAgents')
    EXEC msdb.dbo.sp_delete_job @job_name = 'SIEM_MarkOfflineAgents';
GO

EXEC msdb.dbo.sp_add_job
    @job_name = 'SIEM_MarkOfflineAgents',
    @enabled = 1,
    @description = 'Маркировка агентов как offline если не было heartbeat',
    @category_name = 'Database Maintenance';
GO

EXEC msdb.dbo.sp_add_jobstep
    @job_name = 'SIEM_MarkOfflineAgents',
    @step_name = 'Mark Offline Agents',
    @subsystem = 'TSQL',
    @database_name = 'SIEM_DB',
    @command = N'
        DECLARE @ThresholdMinutes INT;

        -- Получаем порог из настроек
        SELECT @ThresholdMinutes = CAST(SettingValue AS INT)
        FROM SIEM_DB.config.Settings
        WHERE SettingKey = ''agent_offline_threshold_minutes'';

        IF @ThresholdMinutes IS NULL
            SET @ThresholdMinutes = 5;

        -- Маркируем агенты как offline
        UPDATE SIEM_DB.assets.Agents
        SET Status = ''offline''
        WHERE Status = ''online''
            AND LastSeen < DATEADD(MINUTE, -@ThresholdMinutes, GETUTCDATE());

        DECLARE @MarkedOffline INT = @@ROWCOUNT;

        IF @MarkedOffline > 0
        BEGIN
            -- Логируем если много агентов стали offline
            INSERT INTO SIEM_DB.compliance.AuditLog (Action, ObjectType, Details)
            VALUES (
                ''agents_marked_offline'',
                ''agent'',
                JSON_QUERY((SELECT @MarkedOffline AS count, @ThresholdMinutes AS threshold_minutes FOR JSON PATH, WITHOUT_ARRAY_WRAPPER))
            );

            PRINT ''Помечено offline агентов: '' + CAST(@MarkedOffline AS VARCHAR);
        END;
    ',
    @retry_attempts = 3,
    @retry_interval = 1;
GO

-- Расписание: каждые 5 минут
EXEC msdb.dbo.sp_add_schedule
    @schedule_name = 'Every_5_Minutes',
    @freq_type = 4, -- Daily
    @freq_interval = 1,
    @freq_subday_type = 4, -- Minutes
    @freq_subday_interval = 5;
GO

EXEC msdb.dbo.sp_attach_schedule
    @job_name = 'SIEM_MarkOfflineAgents',
    @schedule_name = 'Every_5_Minutes';
GO

EXEC msdb.dbo.sp_add_jobserver
    @job_name = 'SIEM_MarkOfflineAgents';
GO

PRINT '  ✓ Job "SIEM_MarkOfflineAgents" создан (запуск: каждые 5 минут)';
GO

-- =====================================================================
-- JOB 5: Backup базы данных (Transaction Log)
-- =====================================================================

IF EXISTS (SELECT 1 FROM msdb.dbo.sysjobs WHERE name = 'SIEM_TransactionLogBackup')
    EXEC msdb.dbo.sp_delete_job @job_name = 'SIEM_TransactionLogBackup';
GO

EXEC msdb.dbo.sp_add_job
    @job_name = 'SIEM_TransactionLogBackup',
    @enabled = 1,
    @description = 'Резервное копирование журнала транзакций каждый час',
    @category_name = 'Database Maintenance';
GO

EXEC msdb.dbo.sp_add_jobstep
    @job_name = 'SIEM_TransactionLogBackup',
    @step_name = 'Backup Transaction Log',
    @subsystem = 'TSQL',
    @database_name = 'SIEM_DB',
    @command = N'
        DECLARE @BackupPath NVARCHAR(500);
        DECLARE @FileName NVARCHAR(500);
        DECLARE @DateTime NVARCHAR(20);

        -- Формируем имя файла с датой и временем
        SET @DateTime = REPLACE(REPLACE(REPLACE(CONVERT(VARCHAR, GETDATE(), 120), ''-'', ''''), '' '', ''_''), '':'', '''');
        SET @BackupPath = ''D:\MSSQL\Backup\''; -- ИЗМЕНИТЬ НА СВОЙ ПУТЬ!
        SET @FileName = @BackupPath + ''SIEM_DB_Log_'' + @DateTime + ''.trn'';

        -- Backup
        BACKUP LOG SIEM_DB
        TO DISK = @FileName
        WITH COMPRESSION, STATS = 10;

        PRINT ''Transaction log backed up to: '' + @FileName;

        -- Удаляем старые backup файлы (старше 7 дней)
        EXECUTE master.dbo.xp_delete_file 0, @BackupPath, ''trn'', ''7d'';
    ',
    @retry_attempts = 2,
    @retry_interval = 5;
GO

-- Расписание: каждый час
EXEC msdb.dbo.sp_attach_schedule
    @job_name = 'SIEM_TransactionLogBackup',
    @schedule_name = 'Hourly';
GO

EXEC msdb.dbo.sp_add_jobserver
    @job_name = 'SIEM_TransactionLogBackup';
GO

PRINT '  ✓ Job "SIEM_TransactionLogBackup" создан (запуск: каждый час)';
PRINT '    ⚠ ВАЖНО: Укажите правильный путь для backup в шаге job!';
GO

-- =====================================================================
-- JOB 6: Полный backup базы данных
-- =====================================================================

IF EXISTS (SELECT 1 FROM msdb.dbo.sysjobs WHERE name = 'SIEM_FullBackup')
    EXEC msdb.dbo.sp_delete_job @job_name = 'SIEM_FullBackup';
GO

EXEC msdb.dbo.sp_add_job
    @job_name = 'SIEM_FullBackup',
    @enabled = 1,
    @description = 'Полное резервное копирование базы данных (еженедельно)',
    @category_name = 'Database Maintenance';
GO

EXEC msdb.dbo.sp_add_jobstep
    @job_name = 'SIEM_FullBackup',
    @step_name = 'Full Database Backup',
    @subsystem = 'TSQL',
    @database_name = 'SIEM_DB',
    @command = N'
        DECLARE @BackupPath NVARCHAR(500);
        DECLARE @FileName NVARCHAR(500);
        DECLARE @DateTime NVARCHAR(20);

        SET @DateTime = REPLACE(REPLACE(REPLACE(CONVERT(VARCHAR, GETDATE(), 120), ''-'', ''''), '' '', ''_''), '':'', '''');
        SET @BackupPath = ''D:\MSSQL\Backup\''; -- ИЗМЕНИТЬ НА СВОЙ ПУТЬ!
        SET @FileName = @BackupPath + ''SIEM_DB_Full_'' + @DateTime + ''.bak'';

        -- Full backup с сжатием
        BACKUP DATABASE SIEM_DB
        TO DISK = @FileName
        WITH COMPRESSION, STATS = 10, CHECKSUM;

        PRINT ''Full backup completed: '' + @FileName;

        -- Удаляем старые full backup (старше 30 дней)
        EXECUTE master.dbo.xp_delete_file 0, @BackupPath, ''bak'', ''30d'';
    ',
    @retry_attempts = 1,
    @retry_interval = 30;
GO

-- Расписание: каждое воскресенье в 01:00
EXEC msdb.dbo.sp_add_schedule
    @schedule_name = 'Weekly_Sunday_1AM',
    @freq_type = 8, -- Weekly
    @freq_interval = 1, -- Sunday
    @freq_recurrence_factor = 1,
    @active_start_time = 010000;
GO

EXEC msdb.dbo.sp_attach_schedule
    @job_name = 'SIEM_FullBackup',
    @schedule_name = 'Weekly_Sunday_1AM';
GO

EXEC msdb.dbo.sp_add_jobserver
    @job_name = 'SIEM_FullBackup';
GO

PRINT '  ✓ Job "SIEM_FullBackup" создан (запуск: воскресенье в 01:00)';
PRINT '    ⚠ ВАЖНО: Укажите правильный путь для backup в шаге job!';
GO

-- =====================================================================
-- ПРОВЕРКА СТАТУСА СОЗДАННЫХ JOBS
-- =====================================================================

PRINT '';
PRINT '═══════════════════════════════════════════════════════════════';
PRINT 'SQL Agent Jobs успешно созданы!';
PRINT '═══════════════════════════════════════════════════════════════';
PRINT '';
PRINT 'Список созданных jobs:';

SELECT
    j.name AS JobName,
    CASE j.enabled WHEN 1 THEN 'Enabled' ELSE 'Disabled' END AS Status,
    s.name AS ScheduleName,
    CASE s.freq_type
        WHEN 4 THEN 'Daily'
        WHEN 8 THEN 'Weekly'
        ELSE 'Other'
    END AS Frequency
FROM msdb.dbo.sysjobs j
LEFT JOIN msdb.dbo.sysjobschedules js ON j.job_id = js.job_id
LEFT JOIN msdb.dbo.sysschedules s ON js.schedule_id = s.schedule_id
WHERE j.name LIKE 'SIEM_%'
ORDER BY j.name;

PRINT '';
PRINT '⚠  ВАЖНО:';
PRINT '  1. Убедитесь что SQL Server Agent запущен';
PRINT '  2. Измените пути backup в jobs на актуальные';
PRINT '  3. Настройте уведомления на email при ошибках jobs (опционально)';
PRINT '  4. Проверьте расписания и адаптируйте под вашу инфраструктуру';
PRINT '';
GO
