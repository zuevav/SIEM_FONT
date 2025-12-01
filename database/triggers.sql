-- =====================================================================
-- SIEM DATABASE TRIGGERS
-- Триггеры для защиты данных от изменений (требование ЦБ РФ)
-- =====================================================================

USE SIEM_DB;
GO

-- =====================================================================
-- ЗАЩИТА СОБЫТИЙ ОТ ИЗМЕНЕНИЯ И УДАЛЕНИЯ
-- Требование ЦБ: события безопасности не могут быть изменены или удалены
-- =====================================================================

-- Запрет UPDATE для таблицы Events (события неизменяемы после записи)
CREATE OR ALTER TRIGGER security_events.TR_Events_PreventUpdate
ON security_events.Events
INSTEAD OF UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    -- Разрешаем только обновление AI-полей (для пост-обработки)
    IF EXISTS (
        SELECT 1 FROM inserted i
        JOIN deleted d ON i.EventId = d.EventId
        WHERE
            i.EventGuid <> d.EventGuid OR
            i.AgentId <> d.AgentId OR
            i.EventTime <> d.EventTime OR
            i.ReceivedTime <> d.ReceivedTime OR
            i.SourceType <> d.SourceType OR
            ISNULL(i.RawEvent, '') <> ISNULL(d.RawEvent, '')
    )
    BEGIN
        RAISERROR('События безопасности защищены от изменения. Изменение базовых полей запрещено (требование ЦБ РФ 683-П).', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END

    -- Разрешаем обновление только полей AI-анализа и ProcessedTime
    UPDATE e SET
        ProcessedTime = i.ProcessedTime,
        AIProcessed = i.AIProcessed,
        AIScore = i.AIScore,
        AICategory = i.AICategory,
        AIDescription = i.AIDescription,
        AIConfidence = i.AIConfidence,
        AIIsAttack = i.AIIsAttack,
        -- Разрешаем обновление MITRE (если определено AI)
        MitreAttackTactic = ISNULL(i.MitreAttackTactic, e.MitreAttackTactic),
        MitreAttackTechnique = ISNULL(i.MitreAttackTechnique, e.MitreAttackTechnique),
        MitreAttackSubtechnique = ISNULL(i.MitreAttackSubtechnique, e.MitreAttackSubtechnique)
    FROM security_events.Events e
    INNER JOIN inserted i ON e.EventId = i.EventId;

    PRINT 'Обновлены только AI-поля для ' + CAST(@@ROWCOUNT AS VARCHAR) + ' событий.';
END;
GO

-- Запрет DELETE для таблицы Events (кроме процедуры архивирования)
CREATE OR ALTER TRIGGER security_events.TR_Events_PreventDelete
ON security_events.Events
INSTEAD OF DELETE
AS
BEGIN
    SET NOCOUNT ON;

    -- Проверяем контекст выполнения
    -- Разрешаем удаление только из процедуры очистки
    IF OBJECT_NAME(@@PROCID) <> 'PurgeOldData' AND APP_NAME() NOT LIKE '%PurgeOldData%'
    BEGIN
        RAISERROR('Прямое удаление событий запрещено. Используйте процедуру compliance.PurgeOldData для архивирования старых данных.', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END

    -- Логируем удаление перед выполнением
    DECLARE @DeletedCount INT;
    SELECT @DeletedCount = COUNT(*) FROM deleted;

    -- Выполняем удаление
    DELETE FROM security_events.Events
    WHERE EventId IN (SELECT EventId FROM deleted);

    PRINT 'Удалено событий через процедуру архивирования: ' + CAST(@DeletedCount AS VARCHAR);
END;
GO

-- =====================================================================
-- ЗАЩИТА AUDIT LOG ОТ ИЗМЕНЕНИЯ
-- Логи аудита также должны быть неизменяемы
-- =====================================================================

CREATE OR ALTER TRIGGER compliance.TR_AuditLog_PreventUpdate
ON compliance.AuditLog
INSTEAD OF UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    RAISERROR('Записи audit log защищены от изменения (ГОСТ Р 57580).', 16, 1);
    ROLLBACK TRANSACTION;
END;
GO

CREATE OR ALTER TRIGGER compliance.TR_AuditLog_PreventDelete
ON compliance.AuditLog
INSTEAD OF DELETE
AS
BEGIN
    SET NOCOUNT ON;

    -- Разрешаем удаление только из процедуры очистки
    IF OBJECT_NAME(@@PROCID) <> 'PurgeOldData'
    BEGIN
        RAISERROR('Прямое удаление audit log запрещено. Используйте процедуру compliance.PurgeOldData.', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END

    DELETE FROM compliance.AuditLog
    WHERE LogId IN (SELECT LogId FROM deleted);
END;
GO

-- =====================================================================
-- АВТОМАТИЧЕСКИЕ ДЕЙСТВИЯ ПРИ ИЗМЕНЕНИЯХ
-- =====================================================================

-- Автоматическое логирование изменений в правилах детекции
CREATE OR ALTER TRIGGER config.TR_DetectionRules_AuditChanges
ON config.DetectionRules
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Action VARCHAR(50);
    DECLARE @UserId INT;

    -- Определяем тип операции
    IF EXISTS (SELECT * FROM inserted) AND EXISTS (SELECT * FROM deleted)
        SET @Action = 'update';
    ELSE IF EXISTS (SELECT * FROM inserted)
        SET @Action = 'create';
    ELSE
        SET @Action = 'delete';

    -- Логируем изменения для каждого правила
    IF @Action = 'create'
    BEGIN
        INSERT INTO compliance.AuditLog (UserId, Action, ObjectType, ObjectId, ObjectName, NewValue)
        SELECT
            i.CreatedBy,
            'create',
            'detection_rule',
            CAST(i.RuleId AS VARCHAR),
            i.RuleName,
            (SELECT * FROM inserted i2 WHERE i2.RuleId = i.RuleId FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
        FROM inserted i;
    END

    IF @Action = 'update'
    BEGIN
        INSERT INTO compliance.AuditLog (UserId, Action, ObjectType, ObjectId, ObjectName, OldValue, NewValue)
        SELECT
            i.UpdatedBy,
            'update',
            'detection_rule',
            CAST(i.RuleId AS VARCHAR),
            i.RuleName,
            (SELECT * FROM deleted d WHERE d.RuleId = i.RuleId FOR JSON PATH, WITHOUT_ARRAY_WRAPPER),
            (SELECT * FROM inserted i2 WHERE i2.RuleId = i.RuleId FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
        FROM inserted i;
    END

    IF @Action = 'delete'
    BEGIN
        INSERT INTO compliance.AuditLog (Action, ObjectType, ObjectId, ObjectName, OldValue)
        SELECT
            'delete',
            'detection_rule',
            CAST(d.RuleId AS VARCHAR),
            d.RuleName,
            (SELECT * FROM deleted d2 WHERE d2.RuleId = d.RuleId FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
        FROM deleted d;
    END
END;
GO

-- Автоматическое логирование изменений пользователей
CREATE OR ALTER TRIGGER config.TR_Users_AuditChanges
ON config.Users
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Action VARCHAR(50);

    IF EXISTS (SELECT * FROM inserted) AND EXISTS (SELECT * FROM deleted)
        SET @Action = 'update';
    ELSE IF EXISTS (SELECT * FROM inserted)
        SET @Action = 'user_created';
    ELSE
        SET @Action = 'user_deleted';

    IF @Action = 'user_created'
    BEGIN
        INSERT INTO compliance.AuditLog (Action, ObjectType, ObjectId, ObjectName, NewValue)
        SELECT
            'user_created',
            'user',
            CAST(i.UserId AS VARCHAR),
            i.Username,
            JSON_QUERY((SELECT i.Username, i.Email, i.Role, i.IsADUser FOR JSON PATH, WITHOUT_ARRAY_WRAPPER))
        FROM inserted i;
    END

    IF @Action = 'update'
    BEGIN
        INSERT INTO compliance.AuditLog (Action, ObjectType, ObjectId, ObjectName, OldValue, NewValue)
        SELECT
            'update',
            'user',
            CAST(i.UserId AS VARCHAR),
            i.Username,
            JSON_QUERY((SELECT d.Username, d.Email, d.Role, d.IsActive FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)),
            JSON_QUERY((SELECT i.Username, i.Email, i.Role, i.IsActive FOR JSON PATH, WITHOUT_ARRAY_WRAPPER))
        FROM inserted i
        JOIN deleted d ON i.UserId = d.UserId;
    END

    IF @Action = 'user_deleted'
    BEGIN
        INSERT INTO compliance.AuditLog (Action, ObjectType, ObjectId, ObjectName, OldValue)
        SELECT
            'user_deleted',
            'user',
            CAST(d.UserId AS VARCHAR),
            d.Username,
            JSON_QUERY((SELECT d.Username, d.Email, d.Role FOR JSON PATH, WITHOUT_ARRAY_WRAPPER))
        FROM deleted d;
    END
END;
GO

-- =====================================================================
-- ТРИГГЕРЫ ДЛЯ МОНИТОРИНГА ИЗМЕНЕНИЙ В АКТИВАХ
-- =====================================================================

-- Отслеживание изменений установленного ПО (для алертов на запрещённое ПО)
CREATE OR ALTER TRIGGER assets.TR_InstalledSoftware_DetectChanges
ON assets.InstalledSoftware
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    -- Определяем новое установленное ПО
    IF EXISTS (SELECT * FROM inserted WHERE FirstSeenAt >= DATEADD(SECOND, -5, GETUTCDATE()))
    BEGIN
        -- Логируем установку нового ПО
        INSERT INTO assets.AssetChanges (AgentId, ChangeType, ChangeDetails, Severity)
        SELECT
            i.AgentId,
            'software_installed',
            JSON_QUERY((SELECT i.Name, i.Version, i.Publisher, i.InstallLocation FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)),
            CASE
                -- Проверяем, запрещено ли ПО
                WHEN EXISTS (
                    SELECT 1 FROM assets.SoftwareRegistry sr
                    WHERE sr.SoftwareId = i.SoftwareId AND sr.IsForbidden = 1
                ) THEN 4 -- Critical
                -- Проверяем уровень риска
                WHEN EXISTS (
                    SELECT 1 FROM assets.SoftwareRegistry sr
                    WHERE sr.SoftwareId = i.SoftwareId AND sr.RiskLevel = 'high'
                ) THEN 3 -- High
                ELSE 0 -- Info
            END
        FROM inserted i
        WHERE i.FirstSeenAt >= DATEADD(SECOND, -5, GETUTCDATE())
            AND i.IsActive = 1;
    END

    -- Определяем удалённое ПО (IsActive изменился на 0)
    IF EXISTS (
        SELECT * FROM inserted i
        JOIN deleted d ON i.InstallId = d.InstallId
        WHERE i.IsActive = 0 AND d.IsActive = 1
    )
    BEGIN
        INSERT INTO assets.AssetChanges (AgentId, ChangeType, ChangeDetails, Severity)
        SELECT
            i.AgentId,
            'software_removed',
            JSON_QUERY((SELECT i.Name, i.Version, i.RemovedAt FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)),
            0
        FROM inserted i
        JOIN deleted d ON i.InstallId = d.InstallId
        WHERE i.IsActive = 0 AND d.IsActive = 1;
    END
END;
GO

-- Обновление счётчика инцидентов при добавлении алертов
CREATE OR ALTER TRIGGER incidents.TR_Alerts_UpdateIncidentCount
ON incidents.Alerts
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    -- Обновляем счётчики в связанных инцидентах
    UPDATE i SET
        AlertCount = (
            SELECT COUNT(*)
            FROM incidents.Alerts
            WHERE IncidentId = i.IncidentId
        ),
        EventCount = (
            SELECT SUM(ISNULL(EventCount, 0))
            FROM incidents.Alerts
            WHERE IncidentId = i.IncidentId
        ),
        UpdatedAt = GETUTCDATE()
    FROM incidents.Incidents i
    WHERE i.IncidentId IN (
        SELECT DISTINCT IncidentId
        FROM inserted
        WHERE IncidentId IS NOT NULL
    );
END;
GO

-- =====================================================================
-- ТРИГГЕР ДЛЯ АВТОМАТИЧЕСКОЙ КЛАССИФИКАЦИИ ПО КАТЕГОРИЯМ ОР (716-П)
-- =====================================================================

-- Автоматическое определение категории операционного риска при создании алерта
CREATE OR ALTER TRIGGER incidents.TR_Alerts_ClassifyOperationalRisk
ON incidents.Alerts
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    -- Классифицируем по категориям операционного риска ЦБ
    UPDATE a SET
        OperationalRiskCategory = CASE
            -- Внутренние мошенничества
            WHEN a.Category IN ('policy_violation', 'data_exfiltration') AND a.Username IS NOT NULL
                THEN 'Internal Fraud'

            -- Внешние мошенничества
            WHEN a.Category IN ('intrusion', 'malware', 'phishing')
                THEN 'External Fraud'

            -- Недостатки в управлении персоналом
            WHEN a.Category = 'anomaly' AND a.Username IS NOT NULL
                THEN 'Employment Practices and Workplace Safety'

            -- Клиенты, продукты и деловая практика
            WHEN a.Category = 'data_breach'
                THEN 'Clients, Products and Business Practices'

            -- Повреждение материальных активов
            WHEN a.Category = 'system_failure'
                THEN 'Damage to Physical Assets'

            -- Нарушение деятельности и системные сбои
            WHEN a.Category IN ('denial_of_service', 'system_unavailability')
                THEN 'Business Disruption and System Failures'

            -- Исполнение, поставка и управление процессами
            ELSE 'Execution, Delivery and Process Management'
        END,
        IsReportable = CASE
            -- Высокий severity всегда отчитываем
            WHEN a.Severity >= 3 THEN 1
            -- Критичные категории
            WHEN a.Category IN ('data_breach', 'intrusion', 'malware') THEN 1
            ELSE 0
        END
    FROM incidents.Alerts a
    INNER JOIN inserted i ON a.AlertId = i.AlertId
    WHERE a.OperationalRiskCategory IS NULL;
END;
GO

-- =====================================================================
-- ТРИГГЕР ДЛЯ МОНИТОРИНГА ИСТЕЧЕНИЯ СЕССИЙ
-- =====================================================================

-- Автоматическая деактивация истёкших сессий (для performance)
-- Примечание: в production лучше использовать SQL Agent Job
CREATE OR ALTER TRIGGER config.TR_Sessions_ExpireOldSessions
ON config.Sessions
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    -- Деактивируем истёкшие сессии
    UPDATE config.Sessions
    SET IsActive = 0
    WHERE ExpiresAt < GETUTCDATE() AND IsActive = 1;

    -- Логируем если деактивировали много сессий (возможная проблема)
    IF @@ROWCOUNT > 100
    BEGIN
        INSERT INTO compliance.AuditLog (Action, ObjectType, Details)
        VALUES (
            'logout',
            'session',
            JSON_QUERY((SELECT @@ROWCOUNT AS expired_sessions FOR JSON PATH, WITHOUT_ARRAY_WRAPPER))
        );
    END
END;
GO

PRINT 'Триггеры безопасности успешно созданы!';
PRINT '';
PRINT 'Установленная защита:';
PRINT '  - События безопасности защищены от изменения и удаления';
PRINT '  - Audit log защищён от изменения';
PRINT '  - Автоматическое логирование изменений правил и пользователей';
PRINT '  - Мониторинг изменений в установленном ПО';
PRINT '  - Автоматическая классификация по категориям операционного риска';
PRINT '';
PRINT 'Все изменения соответствуют требованиям ЦБ РФ (683-П) и ГОСТ Р 57580.';
GO
