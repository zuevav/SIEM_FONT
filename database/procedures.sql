-- =====================================================================
-- SIEM STORED PROCEDURES AND FUNCTIONS
-- Хранимые процедуры для высокопроизводительной работы
-- =====================================================================

USE SIEM_DB;
GO

-- =====================================================================
-- ПРОЦЕДУРЫ ДЛЯ РАБОТЫ С СОБЫТИЯМИ
-- =====================================================================

-- Массовая вставка событий (используется агентами)
CREATE OR ALTER PROCEDURE security_events.InsertEventsBatch
    @Events NVARCHAR(MAX) -- JSON array событий
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Вставка событий из JSON
        INSERT INTO security_events.Events (
            AgentId, EventTime, SourceType, EventCode, Channel, Provider, Computer,
            Severity, Category, Action, Outcome,
            SubjectUser, SubjectDomain, SubjectSid, SubjectLogonId,
            TargetUser, TargetDomain, TargetHost, TargetIP, TargetPort,
            ProcessName, ProcessId, ProcessPath, ProcessCommandLine, ProcessHash,
            ParentProcessName, ParentProcessId, ParentProcessPath, ParentProcessCommandLine,
            SourceIP, SourcePort, SourceHostname,
            DestinationIP, DestinationPort, DestinationHostname, Protocol,
            DNSQuery, DNSResponse,
            FilePath, FileName, FileHash, FileExtension, FileSize,
            RegistryPath, RegistryKey, RegistryValue, RegistryValueType,
            Message, RawEvent, Tags,
            MitreAttackTactic, MitreAttackTechnique, MitreAttackSubtechnique,
            GeoCountry, GeoCity
        )
        SELECT
            CAST(AgentId AS UNIQUEIDENTIFIER),
            CAST(EventTime AS DATETIME2),
            SourceType, EventCode, Channel, Provider, Computer,
            ISNULL(Severity, 0), Category, Action, Outcome,
            SubjectUser, SubjectDomain, SubjectSid, SubjectLogonId,
            TargetUser, TargetDomain, TargetHost, TargetIP, TargetPort,
            ProcessName, ProcessId, ProcessPath, ProcessCommandLine, ProcessHash,
            ParentProcessName, ParentProcessId, ParentProcessPath, ParentProcessCommandLine,
            SourceIP, SourcePort, SourceHostname,
            DestinationIP, DestinationPort, DestinationHostname, Protocol,
            DNSQuery, DNSResponse,
            FilePath, FileName, FileHash, FileExtension, FileSize,
            RegistryPath, RegistryKey, RegistryValue, RegistryValueType,
            Message, RawEvent, Tags,
            MitreAttackTactic, MitreAttackTechnique, MitreAttackSubtechnique,
            GeoCountry, GeoCity
        FROM OPENJSON(@Events)
        WITH (
            AgentId NVARCHAR(36),
            EventTime NVARCHAR(30),
            SourceType VARCHAR(50),
            EventCode INT,
            Channel NVARCHAR(100),
            Provider NVARCHAR(100),
            Computer NVARCHAR(255),
            Severity TINYINT,
            Category VARCHAR(50),
            Action VARCHAR(50),
            Outcome VARCHAR(20),
            SubjectUser NVARCHAR(200),
            SubjectDomain NVARCHAR(100),
            SubjectSid VARCHAR(100),
            SubjectLogonId VARCHAR(50),
            TargetUser NVARCHAR(200),
            TargetDomain NVARCHAR(100),
            TargetHost NVARCHAR(255),
            TargetIP VARCHAR(45),
            TargetPort INT,
            ProcessName NVARCHAR(500),
            ProcessId INT,
            ProcessPath NVARCHAR(1000),
            ProcessCommandLine NVARCHAR(MAX),
            ProcessHash VARCHAR(128),
            ParentProcessName NVARCHAR(500),
            ParentProcessId INT,
            ParentProcessPath NVARCHAR(1000),
            ParentProcessCommandLine NVARCHAR(MAX),
            SourceIP VARCHAR(45),
            SourcePort INT,
            SourceHostname NVARCHAR(255),
            DestinationIP VARCHAR(45),
            DestinationPort INT,
            DestinationHostname NVARCHAR(255),
            Protocol VARCHAR(20),
            DNSQuery NVARCHAR(500),
            DNSResponse NVARCHAR(MAX),
            FilePath NVARCHAR(1000),
            FileName NVARCHAR(255),
            FileHash VARCHAR(128),
            FileExtension VARCHAR(20),
            FileSize BIGINT,
            RegistryPath NVARCHAR(1000),
            RegistryKey NVARCHAR(500),
            RegistryValue NVARCHAR(MAX),
            RegistryValueType VARCHAR(50),
            Message NVARCHAR(MAX),
            RawEvent NVARCHAR(MAX),
            Tags NVARCHAR(500),
            MitreAttackTactic VARCHAR(50),
            MitreAttackTechnique VARCHAR(20),
            MitreAttackSubtechnique VARCHAR(30),
            GeoCountry VARCHAR(2),
            GeoCity NVARCHAR(100)
        );

        DECLARE @InsertedCount INT = @@ROWCOUNT;

        COMMIT TRANSACTION;

        SELECT @InsertedCount AS InsertedCount, 'success' AS Status;

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;

        SELECT
            0 AS InsertedCount,
            'error' AS Status,
            ERROR_MESSAGE() AS ErrorMessage,
            ERROR_NUMBER() AS ErrorNumber;
    END CATCH;
END;
GO

-- Поиск событий с фильтрацией
CREATE OR ALTER PROCEDURE security_events.SearchEvents
    @StartTime DATETIME2 = NULL,
    @EndTime DATETIME2 = NULL,
    @AgentId UNIQUEIDENTIFIER = NULL,
    @MinSeverity TINYINT = NULL,
    @Categories NVARCHAR(500) = NULL, -- JSON array
    @SubjectUser NVARCHAR(200) = NULL,
    @SourceIP VARCHAR(45) = NULL,
    @ProcessName NVARCHAR(500) = NULL,
    @SearchText NVARCHAR(500) = NULL, -- Полнотекстовый поиск
    @Offset INT = 0,
    @Limit INT = 100
AS
BEGIN
    SET NOCOUNT ON;

    -- Установка параметров по умолчанию
    IF @StartTime IS NULL SET @StartTime = DATEADD(DAY, -1, GETUTCDATE());
    IF @EndTime IS NULL SET @EndTime = GETUTCDATE();
    IF @Limit > 10000 SET @Limit = 10000; -- Защита от слишком больших выборок

    SELECT
        e.EventId,
        e.EventGuid,
        e.AgentId,
        a.Hostname,
        e.EventTime,
        e.ReceivedTime,
        e.SourceType,
        e.EventCode,
        e.Severity,
        e.Category,
        e.Action,
        e.Outcome,
        e.SubjectUser,
        e.SubjectDomain,
        e.TargetUser,
        e.TargetIP,
        e.ProcessName,
        e.SourceIP,
        e.DestinationIP,
        e.Message,
        e.MitreAttackTactic,
        e.MitreAttackTechnique,
        e.AIScore,
        e.AICategory,
        e.AIDescription
    FROM security_events.Events e
    LEFT JOIN assets.Agents a ON e.AgentId = a.AgentId
    WHERE
        e.EventTime BETWEEN @StartTime AND @EndTime
        AND (@AgentId IS NULL OR e.AgentId = @AgentId)
        AND (@MinSeverity IS NULL OR e.Severity >= @MinSeverity)
        AND (@SubjectUser IS NULL OR e.SubjectUser LIKE '%' + @SubjectUser + '%')
        AND (@SourceIP IS NULL OR e.SourceIP = @SourceIP)
        AND (@ProcessName IS NULL OR e.ProcessName LIKE '%' + @ProcessName + '%')
        AND (@SearchText IS NULL OR
             e.Message LIKE '%' + @SearchText + '%' OR
             e.ProcessCommandLine LIKE '%' + @SearchText + '%')
        AND (@Categories IS NULL OR e.Category IN (
            SELECT value FROM OPENJSON(@Categories)
        ))
    ORDER BY e.EventTime DESC
    OFFSET @Offset ROWS
    FETCH NEXT @Limit ROWS ONLY;

    -- Возвращаем общее количество
    SELECT COUNT(*) AS TotalCount
    FROM security_events.Events e
    WHERE
        e.EventTime BETWEEN @StartTime AND @EndTime
        AND (@AgentId IS NULL OR e.AgentId = @AgentId)
        AND (@MinSeverity IS NULL OR e.Severity >= @MinSeverity)
        AND (@SubjectUser IS NULL OR e.SubjectUser LIKE '%' + @SubjectUser + '%')
        AND (@SourceIP IS NULL OR e.SourceIP = @SourceIP)
        AND (@ProcessName IS NULL OR e.ProcessName LIKE '%' + @ProcessName + '%')
        AND (@Categories IS NULL OR e.Category IN (
            SELECT value FROM OPENJSON(@Categories)
        ));
END;
GO

-- Получение детальной информации о событии
CREATE OR ALTER PROCEDURE security_events.GetEventDetails
    @EventId BIGINT = NULL,
    @EventGuid UNIQUEIDENTIFIER = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        e.*,
        a.Hostname,
        a.FQDN,
        a.Domain,
        a.Location
    FROM security_events.Events e
    LEFT JOIN assets.Agents a ON e.AgentId = a.AgentId
    WHERE
        (@EventId IS NOT NULL AND e.EventId = @EventId)
        OR (@EventGuid IS NOT NULL AND e.EventGuid = @EventGuid);
END;
GO

-- =====================================================================
-- ПРОЦЕДУРЫ ДЛЯ ДАШБОРДА И СТАТИСТИКИ
-- =====================================================================

-- Получение статистики для главного дашборда
CREATE OR ALTER PROCEDURE security_events.GetDashboardStats
    @Hours INT = 24
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @FromTime DATETIME2 = DATEADD(HOUR, -@Hours, GETUTCDATE());

    -- 1. Общая статистика событий
    SELECT
        COUNT(*) AS TotalEvents,
        SUM(CASE WHEN Severity = 4 THEN 1 ELSE 0 END) AS CriticalEvents,
        SUM(CASE WHEN Severity = 3 THEN 1 ELSE 0 END) AS HighEvents,
        SUM(CASE WHEN Severity = 2 THEN 1 ELSE 0 END) AS MediumEvents,
        SUM(CASE WHEN Severity = 1 THEN 1 ELSE 0 END) AS LowEvents,
        COUNT(DISTINCT AgentId) AS ActiveAgents,
        SUM(CASE WHEN AIIsAttack = 1 THEN 1 ELSE 0 END) AS PotentialAttacks
    FROM security_events.Events
    WHERE EventTime >= @FromTime;

    -- 2. События по часам (для графика timeline)
    SELECT
        DATEADD(HOUR, DATEDIFF(HOUR, 0, EventTime), 0) AS Hour,
        Severity,
        COUNT(*) AS EventCount
    FROM security_events.Events
    WHERE EventTime >= @FromTime
    GROUP BY DATEADD(HOUR, DATEDIFF(HOUR, 0, EventTime), 0), Severity
    ORDER BY Hour, Severity;

    -- 3. Распределение по категориям
    SELECT
        ISNULL(Category, 'unknown') AS Category,
        COUNT(*) AS EventCount,
        SUM(CASE WHEN Severity >= 3 THEN 1 ELSE 0 END) AS HighSeverityCount
    FROM security_events.Events
    WHERE EventTime >= @FromTime
    GROUP BY Category
    ORDER BY EventCount DESC;

    -- 4. Топ-10 хостов по количеству событий высокой важности
    SELECT TOP 10
        a.AgentId,
        a.Hostname,
        a.Status,
        COUNT(*) AS EventCount,
        SUM(CASE WHEN e.Severity >= 3 THEN 1 ELSE 0 END) AS HighSeverityCount,
        MAX(e.EventTime) AS LastEvent
    FROM assets.Agents a
    LEFT JOIN security_events.Events e ON a.AgentId = e.AgentId AND e.EventTime >= @FromTime
    GROUP BY a.AgentId, a.Hostname, a.Status
    HAVING COUNT(*) > 0
    ORDER BY HighSeverityCount DESC, EventCount DESC;

    -- 5. Статистика алертов
    SELECT
        COUNT(*) AS TotalAlerts,
        SUM(CASE WHEN Status = 'new' THEN 1 ELSE 0 END) AS NewAlerts,
        SUM(CASE WHEN Status = 'investigating' THEN 1 ELSE 0 END) AS InvestigatingAlerts,
        SUM(CASE WHEN Severity >= 3 THEN 1 ELSE 0 END) AS CriticalAlerts
    FROM incidents.Alerts
    WHERE CreatedAt >= @FromTime;

    -- 6. Активные инциденты
    SELECT
        COUNT(*) AS TotalIncidents,
        SUM(CASE WHEN Status = 'open' THEN 1 ELSE 0 END) AS OpenIncidents,
        SUM(CASE WHEN Status = 'investigating' THEN 1 ELSE 0 END) AS InvestigatingIncidents,
        SUM(CASE WHEN Severity >= 3 THEN 1 ELSE 0 END) AS CriticalIncidents
    FROM incidents.Incidents
    WHERE Status NOT IN ('closed', 'resolved');

    -- 7. Топ MITRE ATT&CK тактики
    SELECT TOP 10
        MitreAttackTactic,
        COUNT(*) AS EventCount
    FROM security_events.Events
    WHERE EventTime >= @FromTime
        AND MitreAttackTactic IS NOT NULL
    GROUP BY MitreAttackTactic
    ORDER BY EventCount DESC;
END;
GO

-- Статистика для определённого агента
CREATE OR ALTER PROCEDURE assets.GetAgentStatistics
    @AgentId UNIQUEIDENTIFIER,
    @Hours INT = 24
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @FromTime DATETIME2 = DATEADD(HOUR, -@Hours, GETUTCDATE());

    -- Информация об агенте
    SELECT
        a.*,
        (SELECT COUNT(*) FROM assets.InstalledSoftware WHERE AgentId = a.AgentId AND IsActive = 1) AS InstalledSoftwareCount,
        (SELECT COUNT(*) FROM assets.WindowsServices WHERE AgentId = a.AgentId AND IsActive = 1) AS ServicesCount
    FROM assets.Agents a
    WHERE a.AgentId = @AgentId;

    -- События за период
    SELECT
        Severity,
        Category,
        COUNT(*) AS EventCount
    FROM security_events.Events
    WHERE AgentId = @AgentId AND EventTime >= @FromTime
    GROUP BY Severity, Category
    ORDER BY Severity DESC, EventCount DESC;

    -- Последние события
    SELECT TOP 50
        EventTime,
        SourceType,
        EventCode,
        Severity,
        Category,
        Message
    FROM security_events.Events
    WHERE AgentId = @AgentId
    ORDER BY EventTime DESC;
END;
GO

-- =====================================================================
-- ПРОЦЕДУРЫ ДЛЯ ИНВЕНТАРИЗАЦИИ АКТИВОВ
-- =====================================================================

-- Обновление информации об агенте
CREATE OR ALTER PROCEDURE assets.UpdateAgentInfo
    @AgentId UNIQUEIDENTIFIER,
    @Hostname NVARCHAR(255),
    @FQDN NVARCHAR(500) = NULL,
    @IPAddress VARCHAR(45) = NULL,
    @MACAddress VARCHAR(17) = NULL,
    @OSVersion NVARCHAR(100) = NULL,
    @OSBuild NVARCHAR(50) = NULL,
    @OSArchitecture VARCHAR(10) = NULL,
    @Domain NVARCHAR(255) = NULL,
    @OrganizationalUnit NVARCHAR(500) = NULL,
    @Manufacturer NVARCHAR(100) = NULL,
    @Model NVARCHAR(100) = NULL,
    @SerialNumber NVARCHAR(100) = NULL,
    @CPUModel NVARCHAR(200) = NULL,
    @CPUCores INT = NULL,
    @TotalRAM_MB BIGINT = NULL,
    @TotalDisk_GB BIGINT = NULL,
    @AgentVersion VARCHAR(20) = NULL,
    @LastReboot DATETIME2 = NULL,
    @Configuration NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        -- Попытка обновления существующего агента
        UPDATE assets.Agents SET
            Hostname = @Hostname,
            FQDN = ISNULL(@FQDN, FQDN),
            IPAddress = ISNULL(@IPAddress, IPAddress),
            MACAddress = ISNULL(@MACAddress, MACAddress),
            OSVersion = ISNULL(@OSVersion, OSVersion),
            OSBuild = ISNULL(@OSBuild, OSBuild),
            OSArchitecture = ISNULL(@OSArchitecture, OSArchitecture),
            Domain = ISNULL(@Domain, Domain),
            OrganizationalUnit = ISNULL(@OrganizationalUnit, OrganizationalUnit),
            Manufacturer = ISNULL(@Manufacturer, Manufacturer),
            Model = ISNULL(@Model, Model),
            SerialNumber = ISNULL(@SerialNumber, SerialNumber),
            CPUModel = ISNULL(@CPUModel, CPUModel),
            CPUCores = ISNULL(@CPUCores, CPUCores),
            TotalRAM_MB = ISNULL(@TotalRAM_MB, TotalRAM_MB),
            TotalDisk_GB = ISNULL(@TotalDisk_GB, TotalDisk_GB),
            AgentVersion = ISNULL(@AgentVersion, AgentVersion),
            LastReboot = ISNULL(@LastReboot, LastReboot),
            Configuration = ISNULL(@Configuration, Configuration),
            Status = 'online',
            LastSeen = GETUTCDATE()
        WHERE AgentId = @AgentId;

        -- Если не найден, создаём новый
        IF @@ROWCOUNT = 0
        BEGIN
            INSERT INTO assets.Agents (
                AgentId, Hostname, FQDN, IPAddress, MACAddress,
                OSVersion, OSBuild, OSArchitecture,
                Domain, OrganizationalUnit,
                Manufacturer, Model, SerialNumber,
                CPUModel, CPUCores, TotalRAM_MB, TotalDisk_GB,
                AgentVersion, LastReboot, Configuration,
                Status, LastSeen
            ) VALUES (
                @AgentId, @Hostname, @FQDN, @IPAddress, @MACAddress,
                @OSVersion, @OSBuild, @OSArchitecture,
                @Domain, @OrganizationalUnit,
                @Manufacturer, @Model, @SerialNumber,
                @CPUModel, @CPUCores, @TotalRAM_MB, @TotalDisk_GB,
                @AgentVersion, @LastReboot, @Configuration,
                'online', GETUTCDATE()
            );
        END;

        SELECT 'success' AS Status, @AgentId AS AgentId;

    END TRY
    BEGIN CATCH
        SELECT
            'error' AS Status,
            ERROR_MESSAGE() AS ErrorMessage;
    END CATCH;
END;
GO

-- Массовое обновление установленного ПО
CREATE OR ALTER PROCEDURE assets.UpdateInstalledSoftware
    @AgentId UNIQUEIDENTIFIER,
    @SoftwareList NVARCHAR(MAX) -- JSON array
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Помечаем всё текущее ПО как неактивное
        UPDATE assets.InstalledSoftware
        SET IsActive = 0, RemovedAt = GETUTCDATE()
        WHERE AgentId = @AgentId AND IsActive = 1;

        -- Вставляем или активируем ПО из нового списка
        MERGE assets.InstalledSoftware AS target
        USING (
            SELECT
                @AgentId AS AgentId,
                Name, Version, Publisher,
                CAST(InstallDate AS DATE) AS InstallDate,
                InstallLocation, UninstallString, EstimatedSize_KB
            FROM OPENJSON(@SoftwareList)
            WITH (
                Name NVARCHAR(255),
                Version NVARCHAR(100),
                Publisher NVARCHAR(255),
                InstallDate NVARCHAR(20),
                InstallLocation NVARCHAR(1000),
                UninstallString NVARCHAR(1000),
                EstimatedSize_KB BIGINT
            )
        ) AS source
        ON target.AgentId = source.AgentId
           AND target.Name = source.Name
           AND ISNULL(target.Version, '') = ISNULL(source.Version, '')
        WHEN MATCHED THEN
            UPDATE SET
                IsActive = 1,
                LastSeenAt = GETUTCDATE(),
                RemovedAt = NULL,
                Publisher = source.Publisher,
                InstallDate = ISNULL(source.InstallDate, target.InstallDate),
                InstallLocation = ISNULL(source.InstallLocation, target.InstallLocation)
        WHEN NOT MATCHED THEN
            INSERT (AgentId, Name, Version, Publisher, InstallDate,
                    InstallLocation, UninstallString, EstimatedSize_KB, IsActive)
            VALUES (source.AgentId, source.Name, source.Version, source.Publisher,
                    source.InstallDate, source.InstallLocation, source.UninstallString,
                    source.EstimatedSize_KB, 1);

        -- Обновляем время последней инвентаризации
        UPDATE assets.Agents
        SET LastInventory = GETUTCDATE()
        WHERE AgentId = @AgentId;

        COMMIT TRANSACTION;

        SELECT 'success' AS Status, @@ROWCOUNT AS AffectedRows;

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SELECT 'error' AS Status, ERROR_MESSAGE() AS ErrorMessage;
    END CATCH;
END;
GO

-- =====================================================================
-- ПРОЦЕДУРЫ ДЛЯ РАБОТЫ С АЛЕРТАМИ И ИНЦИДЕНТАМИ
-- =====================================================================

-- Создание алерта
CREATE OR ALTER PROCEDURE incidents.CreateAlert
    @RuleId INT,
    @Severity TINYINT,
    @Title NVARCHAR(500),
    @Description NVARCHAR(MAX) = NULL,
    @Category VARCHAR(50) = NULL,
    @EventIds NVARCHAR(MAX) = NULL, -- JSON array
    @AgentId UNIQUEIDENTIFIER = NULL,
    @Hostname NVARCHAR(255) = NULL,
    @Username NVARCHAR(200) = NULL,
    @SourceIP VARCHAR(45) = NULL,
    @MitreAttackTactic VARCHAR(50) = NULL,
    @MitreAttackTechnique VARCHAR(20) = NULL,
    @AlertGuid UNIQUEIDENTIFIER OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        SET @AlertGuid = NEWID();

        -- Получаем время первого и последнего события
        DECLARE @FirstEventTime DATETIME2, @LastEventTime DATETIME2, @EventCount INT;

        IF @EventIds IS NOT NULL
        BEGIN
            SELECT
                @FirstEventTime = MIN(EventTime),
                @LastEventTime = MAX(EventTime),
                @EventCount = COUNT(*)
            FROM security_events.Events
            WHERE EventId IN (SELECT value FROM OPENJSON(@EventIds));
        END

        INSERT INTO incidents.Alerts (
            AlertGuid, RuleId, Severity, Title, Description, Category,
            EventIds, EventCount, FirstEventTime, LastEventTime,
            AgentId, Hostname, Username, SourceIP,
            MitreAttackTactic, MitreAttackTechnique,
            Status, Priority
        ) VALUES (
            @AlertGuid, @RuleId, @Severity, @Title, @Description, @Category,
            @EventIds, ISNULL(@EventCount, 1), @FirstEventTime, @LastEventTime,
            @AgentId, @Hostname, @Username, @SourceIP,
            @MitreAttackTactic, @MitreAttackTechnique,
            'new', @Severity
        );

        -- Обновляем статистику правила
        UPDATE config.DetectionRules
        SET TotalMatches = TotalMatches + 1,
            LastMatch = GETUTCDATE()
        WHERE RuleId = @RuleId;

        SELECT
            'success' AS Status,
            @AlertGuid AS AlertGuid,
            SCOPE_IDENTITY() AS AlertId;

    END TRY
    BEGIN CATCH
        SELECT
            'error' AS Status,
            ERROR_MESSAGE() AS ErrorMessage;
    END CATCH;
END;
GO

-- Создание инцидента из алертов
CREATE OR ALTER PROCEDURE incidents.CreateIncidentFromAlerts
    @AlertIds NVARCHAR(MAX), -- JSON array
    @Title NVARCHAR(500),
    @Description NVARCHAR(MAX) = NULL,
    @AssignedTo INT = NULL,
    @IncidentGuid UNIQUEIDENTIFIER OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRANSACTION;

        SET @IncidentGuid = NEWID();

        -- Собираем информацию из алертов
        DECLARE @MaxSeverity TINYINT, @AlertCount INT, @EventCount INT;
        DECLARE @StartTime DATETIME2, @EndTime DATETIME2;
        DECLARE @Category VARCHAR(50);
        DECLARE @AffectedAgents NVARCHAR(MAX);
        DECLARE @AffectedUsers NVARCHAR(MAX);
        DECLARE @MitreTactics NVARCHAR(500);
        DECLARE @MitreTechniques NVARCHAR(500);

        SELECT
            @MaxSeverity = MAX(Severity),
            @AlertCount = COUNT(*),
            @EventCount = SUM(ISNULL(EventCount, 0)),
            @StartTime = MIN(FirstEventTime),
            @EndTime = MAX(LastEventTime),
            @Category = MIN(Category),
            @AffectedAgents = (
                SELECT DISTINCT AgentId
                FROM incidents.Alerts
                WHERE AlertId IN (SELECT value FROM OPENJSON(@AlertIds))
                    AND AgentId IS NOT NULL
                FOR JSON AUTO
            ),
            @AffectedUsers = (
                SELECT DISTINCT Username
                FROM incidents.Alerts
                WHERE AlertId IN (SELECT value FROM OPENJSON(@AlertIds))
                    AND Username IS NOT NULL
                FOR JSON AUTO
            ),
            @MitreTactics = (
                SELECT DISTINCT MitreAttackTactic
                FROM incidents.Alerts
                WHERE AlertId IN (SELECT value FROM OPENJSON(@AlertIds))
                    AND MitreAttackTactic IS NOT NULL
                FOR JSON AUTO
            ),
            @MitreTechniques = (
                SELECT DISTINCT MitreAttackTechnique
                FROM incidents.Alerts
                WHERE AlertId IN (SELECT value FROM OPENJSON(@AlertIds))
                    AND MitreAttackTechnique IS NOT NULL
                FOR JSON AUTO
            )
        FROM incidents.Alerts
        WHERE AlertId IN (SELECT value FROM OPENJSON(@AlertIds));

        -- Создаём инцидент
        INSERT INTO incidents.Incidents (
            IncidentGuid, Title, Description, Severity, Category,
            AlertCount, EventCount,
            AffectedAgents, AffectedUsers,
            AffectedAssets, -- будет COUNT(DISTINCT AgentId)
            StartTime, EndTime,
            Status, AssignedTo, Priority,
            MitreAttackTactics, MitreAttackTechniques
        ) VALUES (
            @IncidentGuid, @Title, @Description, @MaxSeverity, @Category,
            @AlertCount, @EventCount,
            @AffectedAgents, @AffectedUsers,
            (SELECT COUNT(DISTINCT AgentId) FROM incidents.Alerts WHERE AlertId IN (SELECT value FROM OPENJSON(@AlertIds))),
            @StartTime, @EndTime,
            'open', @AssignedTo, @MaxSeverity,
            @MitreTactics, @MitreTechniques
        );

        DECLARE @IncidentId INT = SCOPE_IDENTITY();

        -- Связываем алерты с инцидентом
        UPDATE incidents.Alerts
        SET IncidentId = @IncidentId,
            UpdatedAt = GETUTCDATE()
        WHERE AlertId IN (SELECT value FROM OPENJSON(@AlertIds));

        COMMIT TRANSACTION;

        SELECT
            'success' AS Status,
            @IncidentGuid AS IncidentGuid,
            @IncidentId AS IncidentId;

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SELECT
            'error' AS Status,
            ERROR_MESSAGE() AS ErrorMessage;
    END CATCH;
END;
GO

-- =====================================================================
-- ПРОЦЕДУРЫ ДЛЯ ОЧИСТКИ ДАННЫХ (ТРЕБОВАНИЕ ЦБ - ХРАНЕНИЕ 5 ЛЕТ)
-- =====================================================================

-- Очистка старых данных с учётом требований регулятора
CREATE OR ALTER PROCEDURE compliance.PurgeOldData
    @RetentionDays INT = 1825, -- 5 лет по умолчанию (требование ЦБ)
    @BatchSize INT = 10000,
    @MaxIterations INT = 1000
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @CutoffDate DATETIME2 = DATEADD(DAY, -@RetentionDays, GETUTCDATE());
    DECLARE @DeletedEvents BIGINT = 0;
    DECLARE @DeletedAlerts INT = 0;
    DECLARE @Iteration INT = 0;
    DECLARE @RowsDeleted INT;

    PRINT 'Начало очистки данных старше ' + CAST(@RetentionDays AS VARCHAR) + ' дней...';
    PRINT 'Дата отсечения: ' + CAST(@CutoffDate AS VARCHAR);

    -- Удаление событий батчами (чтобы не блокировать таблицу надолго)
    WHILE @Iteration < @MaxIterations
    BEGIN
        DELETE TOP (@BatchSize) FROM security_events.Events
        WHERE EventTime < @CutoffDate;

        SET @RowsDeleted = @@ROWCOUNT;
        SET @DeletedEvents = @DeletedEvents + @RowsDeleted;

        IF @RowsDeleted = 0 BREAK;

        SET @Iteration = @Iteration + 1;

        -- Пауза для снижения нагрузки
        WAITFOR DELAY '00:00:02';

        IF @Iteration % 10 = 0
            PRINT 'Удалено ' + CAST(@DeletedEvents AS VARCHAR) + ' событий...';
    END;

    -- Удаление старых resolved/false_positive алертов
    DELETE FROM incidents.Alerts
    WHERE Status IN ('resolved', 'false_positive')
        AND ResolvedAt < @CutoffDate;

    SET @DeletedAlerts = @@ROWCOUNT;

    -- Удаление старых записей audit log (только успешные операции, ошибки храним дольше)
    DELETE FROM compliance.AuditLog
    WHERE CreatedAt < @CutoffDate
        AND Outcome = 'success'
        AND Action NOT IN ('login_failed', 'export'); -- Неудачные попытки входа и экспорты храним дольше

    -- Логирование в audit
    INSERT INTO compliance.AuditLog (Action, ObjectType, Details, Outcome)
    VALUES (
        'purge_old_data',
        'maintenance',
        JSON_QUERY((SELECT
            @RetentionDays AS retention_days,
            @DeletedEvents AS deleted_events,
            @DeletedAlerts AS deleted_alerts,
            @CutoffDate AS cutoff_date
        FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)),
        'success'
    );

    PRINT 'Очистка завершена:';
    PRINT '  - Удалено событий: ' + CAST(@DeletedEvents AS VARCHAR);
    PRINT '  - Удалено алертов: ' + CAST(@DeletedAlerts AS VARCHAR);

    SELECT
        @DeletedEvents AS DeletedEvents,
        @DeletedAlerts AS DeletedAlerts,
        @CutoffDate AS CutoffDate,
        'success' AS Status;
END;
GO

-- =====================================================================
-- ФУНКЦИИ ДЛЯ АУДИТА
-- =====================================================================

-- Логирование действий пользователя
CREATE OR ALTER PROCEDURE compliance.LogAuditEvent
    @UserId INT,
    @Action VARCHAR(50),
    @ObjectType VARCHAR(50) = NULL,
    @ObjectId NVARCHAR(100) = NULL,
    @ObjectName NVARCHAR(255) = NULL,
    @Details NVARCHAR(MAX) = NULL,
    @OldValue NVARCHAR(MAX) = NULL,
    @NewValue NVARCHAR(MAX) = NULL,
    @IPAddress VARCHAR(45) = NULL,
    @UserAgent NVARCHAR(500) = NULL,
    @SessionId UNIQUEIDENTIFIER = NULL,
    @Outcome VARCHAR(20) = 'success',
    @ErrorMessage NVARCHAR(1000) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Username NVARCHAR(100);
    SELECT @Username = Username FROM config.Users WHERE UserId = @UserId;

    INSERT INTO compliance.AuditLog (
        UserId, Username, Action, ObjectType, ObjectId, ObjectName,
        Details, OldValue, NewValue,
        IPAddress, UserAgent, SessionId,
        Outcome, ErrorMessage
    ) VALUES (
        @UserId, @Username, @Action, @ObjectType, @ObjectId, @ObjectName,
        @Details, @OldValue, @NewValue,
        @IPAddress, @UserAgent, @SessionId,
        @Outcome, @ErrorMessage
    );
END;
GO

PRINT 'Хранимые процедуры успешно созданы!';
GO
