-- =====================================================================
-- SIEM DATABASE SCHEMA FOR MS SQL SERVER
-- Соответствие требованиям ЦБ РФ: 683-П, 716-П, 747-П, ГОСТ Р 57580
-- =====================================================================
-- Версия: 1.0
-- Дата создания: 2025-12-01
-- Описание: Полная схема базы данных SIEM-системы с поддержкой
--           инвентаризации активов, событий безопасности, инцидентов
--           и экспорта для регулятора
-- =====================================================================

-- Создание базы данных
USE master;
GO

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'SIEM_DB')
BEGIN
    CREATE DATABASE SIEM_DB
    ON PRIMARY (
        NAME = 'SIEM_Data',
        FILENAME = 'D:\MSSQL\Data\SIEM_Data.mdf',
        SIZE = 10GB,
        FILEGROWTH = 1GB,
        MAXSIZE = 500GB
    )
    LOG ON (
        NAME = 'SIEM_Log',
        FILENAME = 'D:\MSSQL\Logs\SIEM_Log.ldf',
        SIZE = 2GB,
        FILEGROWTH = 512MB,
        MAXSIZE = 50GB
    );

    -- Настройки базы данных
    ALTER DATABASE SIEM_DB SET RECOVERY FULL;
    ALTER DATABASE SIEM_DB SET AUTO_UPDATE_STATISTICS_ASYNC ON;
    ALTER DATABASE SIEM_DB SET PAGE_VERIFY CHECKSUM;
END;
GO

USE SIEM_DB;
GO

-- =====================================================================
-- СОЗДАНИЕ СХЕМ ДЛЯ ОРГАНИЗАЦИИ ОБЪЕКТОВ
-- =====================================================================

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'security_events')
    EXEC('CREATE SCHEMA security_events');
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'config')
    EXEC('CREATE SCHEMA config');
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'incidents')
    EXEC('CREATE SCHEMA incidents');
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'assets')
    EXEC('CREATE SCHEMA assets');
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'compliance')
    EXEC('CREATE SCHEMA compliance');
GO

-- =====================================================================
-- ТАБЛИЦЫ КОНФИГУРАЦИИ И ПОЛЬЗОВАТЕЛЕЙ
-- =====================================================================

-- Таблица пользователей системы
CREATE TABLE config.Users (
    UserId INT IDENTITY(1,1) PRIMARY KEY,
    Username NVARCHAR(100) NOT NULL UNIQUE,
    Email NVARCHAR(255),
    PasswordHash VARCHAR(255), -- NULL если AD-аутентификация
    Role VARCHAR(20) NOT NULL DEFAULT 'viewer', -- admin, analyst, viewer
    IsADUser BIT DEFAULT 0,
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    LastLogin DATETIME2,
    Settings NVARCHAR(MAX), -- JSON с пользовательскими настройками
    CONSTRAINT CK_Users_Role CHECK (Role IN ('admin', 'analyst', 'viewer'))
);
GO

-- Индексы для пользователей
CREATE NONCLUSTERED INDEX IX_Users_Username ON config.Users(Username) WHERE IsActive = 1;
CREATE NONCLUSTERED INDEX IX_Users_Role ON config.Users(Role);
GO

-- Таблица сессий API
CREATE TABLE config.Sessions (
    SessionId UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    UserId INT NOT NULL REFERENCES config.Users(UserId),
    Token VARCHAR(500) NOT NULL,
    IPAddress VARCHAR(45),
    UserAgent NVARCHAR(500),
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    ExpiresAt DATETIME2 NOT NULL,
    IsActive BIT DEFAULT 1,
    CONSTRAINT CK_Sessions_ExpiresAt CHECK (ExpiresAt > CreatedAt)
);
GO

CREATE UNIQUE NONCLUSTERED INDEX IX_Sessions_Token ON config.Sessions(Token) WHERE IsActive = 1;
CREATE NONCLUSTERED INDEX IX_Sessions_UserId ON config.Sessions(UserId, CreatedAt DESC);
CREATE NONCLUSTERED INDEX IX_Sessions_Expires ON config.Sessions(ExpiresAt) WHERE IsActive = 1;
GO

-- Таблица настроек системы
CREATE TABLE config.Settings (
    SettingKey VARCHAR(100) PRIMARY KEY,
    SettingValue NVARCHAR(MAX),
    Description NVARCHAR(500),
    IsEncrypted BIT DEFAULT 0,
    UpdatedBy INT REFERENCES config.Users(UserId),
    UpdatedAt DATETIME2 DEFAULT GETUTCDATE()
);
GO

-- =====================================================================
-- ТАБЛИЦЫ АКТИВОВ И ИНВЕНТАРИЗАЦИИ
-- =====================================================================

-- Таблица агентов (хостов)
CREATE TABLE assets.Agents (
    AgentId UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    Hostname NVARCHAR(255) NOT NULL,
    FQDN NVARCHAR(500),
    IPAddress VARCHAR(45),
    MACAddress VARCHAR(17),

    -- Информация о системе
    OSVersion NVARCHAR(100),
    OSBuild NVARCHAR(50),
    OSArchitecture VARCHAR(10), -- x64, x86

    -- Домен Active Directory
    Domain NVARCHAR(255),
    OrganizationalUnit NVARCHAR(500),

    -- Оборудование
    Manufacturer NVARCHAR(100),
    Model NVARCHAR(100),
    SerialNumber NVARCHAR(100),
    CPUModel NVARCHAR(200),
    CPUCores INT,
    TotalRAM_MB BIGINT,
    TotalDisk_GB BIGINT,

    -- Статус агента
    AgentVersion VARCHAR(20),
    Status VARCHAR(20) DEFAULT 'offline', -- online, offline, error, installing
    LastSeen DATETIME2 DEFAULT GETUTCDATE(),
    LastInventory DATETIME2,
    LastReboot DATETIME2,

    -- Метаданные
    RegisteredAt DATETIME2 DEFAULT GETUTCDATE(),
    Configuration NVARCHAR(MAX), -- JSON конфиг
    Tags NVARCHAR(500), -- JSON array тегов
    Location NVARCHAR(200), -- Физическое расположение
    Owner NVARCHAR(200), -- Ответственный
    CriticalityLevel VARCHAR(20) DEFAULT 'medium', -- critical, high, medium, low

    CONSTRAINT CK_Agents_Status CHECK (Status IN ('online', 'offline', 'error', 'installing')),
    CONSTRAINT CK_Agents_Criticality CHECK (CriticalityLevel IN ('critical', 'high', 'medium', 'low'))
);
GO

-- Индексы для агентов
CREATE UNIQUE NONCLUSTERED INDEX IX_Agents_Hostname ON assets.Agents(Hostname);
CREATE NONCLUSTERED INDEX IX_Agents_Status ON assets.Agents(Status, LastSeen DESC);
CREATE NONCLUSTERED INDEX IX_Agents_LastSeen ON assets.Agents(LastSeen DESC);
CREATE NONCLUSTERED INDEX IX_Agents_Domain ON assets.Agents(Domain) WHERE Domain IS NOT NULL;
GO

-- Таблица категорий программного обеспечения
CREATE TABLE assets.SoftwareCategories (
    CategoryId INT IDENTITY(1,1) PRIMARY KEY,
    CategoryName VARCHAR(50) NOT NULL UNIQUE,
    Description NVARCHAR(500),
    DefaultRiskLevel VARCHAR(20) DEFAULT 'low', -- critical, high, medium, low
    RequiresLicense BIT DEFAULT 0,
    RequiresApproval BIT DEFAULT 0,
    CONSTRAINT CK_SoftwareCategories_Risk CHECK (DefaultRiskLevel IN ('critical', 'high', 'medium', 'low'))
);
GO

-- Справочник установленного ПО (уникальные продукты)
CREATE TABLE assets.SoftwareRegistry (
    SoftwareId INT IDENTITY(1,1) PRIMARY KEY,
    Name NVARCHAR(255) NOT NULL,
    NormalizedName NVARCHAR(255), -- Очищенное название для группировки
    Publisher NVARCHAR(255),
    CategoryId INT REFERENCES assets.SoftwareCategories(CategoryId),

    -- Классификация
    IsAllowed BIT DEFAULT 1, -- Разрешено ли использование
    IsForbidden BIT DEFAULT 0, -- Запрещено политикой безопасности
    RequiresLicense BIT DEFAULT 0,
    RiskLevel VARCHAR(20) DEFAULT 'low',

    -- MITRE ATT&CK (если ПО может использоваться в атаках)
    MitreRelevant BIT DEFAULT 0,
    MitreTechniques NVARCHAR(500), -- JSON array

    -- Метаданные
    FirstSeenAt DATETIME2 DEFAULT GETUTCDATE(),
    LastSeenAt DATETIME2 DEFAULT GETUTCDATE(),
    Notes NVARCHAR(MAX),

    CONSTRAINT CK_SoftwareRegistry_Risk CHECK (RiskLevel IN ('critical', 'high', 'medium', 'low'))
);
GO

CREATE NONCLUSTERED INDEX IX_SoftwareRegistry_Name ON assets.SoftwareRegistry(Name);
CREATE NONCLUSTERED INDEX IX_SoftwareRegistry_NormalizedName ON assets.SoftwareRegistry(NormalizedName);
CREATE NONCLUSTERED INDEX IX_SoftwareRegistry_Category ON assets.SoftwareRegistry(CategoryId);
CREATE NONCLUSTERED INDEX IX_SoftwareRegistry_Forbidden ON assets.SoftwareRegistry(IsForbidden) WHERE IsForbidden = 1;
GO

-- Таблица установленного ПО на хостах
CREATE TABLE assets.InstalledSoftware (
    InstallId BIGINT IDENTITY(1,1) PRIMARY KEY,
    AgentId UNIQUEIDENTIFIER NOT NULL REFERENCES assets.Agents(AgentId),
    SoftwareId INT REFERENCES assets.SoftwareRegistry(SoftwareId),

    -- Информация об установке
    Name NVARCHAR(255) NOT NULL, -- Оригинальное название из реестра
    Version NVARCHAR(100),
    Publisher NVARCHAR(255),
    InstallDate DATE,
    InstallLocation NVARCHAR(1000),
    UninstallString NVARCHAR(1000),
    EstimatedSize_KB BIGINT,

    -- Статус
    IsActive BIT DEFAULT 1, -- false если ПО было удалено
    FirstSeenAt DATETIME2 DEFAULT GETUTCDATE(),
    LastSeenAt DATETIME2 DEFAULT GETUTCDATE(),
    RemovedAt DATETIME2,

    -- Для отслеживания изменений
    CONSTRAINT UQ_InstalledSoftware_Agent_Name_Version UNIQUE (AgentId, Name, Version)
);
GO

CREATE NONCLUSTERED INDEX IX_InstalledSoftware_Agent ON assets.InstalledSoftware(AgentId, IsActive);
CREATE NONCLUSTERED INDEX IX_InstalledSoftware_Software ON assets.InstalledSoftware(SoftwareId);
CREATE NONCLUSTERED INDEX IX_InstalledSoftware_Active ON assets.InstalledSoftware(IsActive, LastSeenAt DESC);
GO

-- Таблица служб Windows
CREATE TABLE assets.WindowsServices (
    ServiceId BIGINT IDENTITY(1,1) PRIMARY KEY,
    AgentId UNIQUEIDENTIFIER NOT NULL REFERENCES assets.Agents(AgentId),

    ServiceName NVARCHAR(255) NOT NULL,
    DisplayName NVARCHAR(500),
    Status VARCHAR(20), -- running, stopped
    StartType VARCHAR(20), -- auto, manual, disabled
    ServiceAccount NVARCHAR(255),
    ExecutablePath NVARCHAR(1000),

    IsActive BIT DEFAULT 1,
    FirstSeenAt DATETIME2 DEFAULT GETUTCDATE(),
    LastSeenAt DATETIME2 DEFAULT GETUTCDATE(),

    CONSTRAINT CK_WindowsServices_Status CHECK (Status IN ('running', 'stopped', 'paused')),
    CONSTRAINT CK_WindowsServices_StartType CHECK (StartType IN ('auto', 'manual', 'disabled', 'automatic_delayed'))
);
GO

CREATE NONCLUSTERED INDEX IX_WindowsServices_Agent ON assets.WindowsServices(AgentId, IsActive);
CREATE NONCLUSTERED INDEX IX_WindowsServices_Running ON assets.WindowsServices(Status) WHERE Status = 'running';
GO

-- История изменений в активах (для аудита ЦБ)
CREATE TABLE assets.AssetChanges (
    ChangeId BIGINT IDENTITY(1,1) PRIMARY KEY,
    AgentId UNIQUEIDENTIFIER NOT NULL REFERENCES assets.Agents(AgentId),
    ChangeType VARCHAR(50) NOT NULL, -- software_installed, software_removed, service_added, etc
    ChangeDetails NVARCHAR(MAX), -- JSON с деталями
    DetectedAt DATETIME2 DEFAULT GETUTCDATE(),
    Severity TINYINT DEFAULT 0, -- 0-info, 1-low, 2-medium, 3-high, 4-critical

    CONSTRAINT CK_AssetChanges_ChangeType CHECK (ChangeType IN (
        'software_installed', 'software_removed', 'software_updated',
        'service_added', 'service_removed', 'service_changed',
        'config_changed', 'user_added', 'user_removed'
    ))
);
GO

CREATE NONCLUSTERED INDEX IX_AssetChanges_Agent ON assets.AssetChanges(AgentId, DetectedAt DESC);
CREATE NONCLUSTERED INDEX IX_AssetChanges_Type ON assets.AssetChanges(ChangeType, DetectedAt DESC);
CREATE NONCLUSTERED INDEX IX_AssetChanges_Critical ON assets.AssetChanges(Severity, DetectedAt DESC) WHERE Severity >= 3;
GO

-- =====================================================================
-- ПАРТИЦИОНИРОВАНИЕ ДЛЯ ТАБЛИЦЫ СОБЫТИЙ
-- =====================================================================

-- Функция партиционирования по месяцам (на 3 года вперёд)
CREATE PARTITION FUNCTION PF_EventsByMonth (DATETIME2)
AS RANGE RIGHT FOR VALUES (
    '2024-01-01', '2024-02-01', '2024-03-01', '2024-04-01', '2024-05-01', '2024-06-01',
    '2024-07-01', '2024-08-01', '2024-09-01', '2024-10-01', '2024-11-01', '2024-12-01',
    '2025-01-01', '2025-02-01', '2025-03-01', '2025-04-01', '2025-05-01', '2025-06-01',
    '2025-07-01', '2025-08-01', '2025-09-01', '2025-10-01', '2025-11-01', '2025-12-01',
    '2026-01-01', '2026-02-01', '2026-03-01', '2026-04-01', '2026-05-01', '2026-06-01',
    '2026-07-01', '2026-08-01', '2026-09-01', '2026-10-01', '2026-11-01', '2026-12-01',
    '2027-01-01', '2027-02-01', '2027-03-01', '2027-04-01', '2027-05-01', '2027-06-01',
    '2027-07-01', '2027-08-01', '2027-09-01', '2027-10-01', '2027-11-01', '2027-12-01'
);
GO

-- Схема партиционирования (все на PRIMARY, можно разнести по файловым группам)
CREATE PARTITION SCHEME PS_EventsByMonth
AS PARTITION PF_EventsByMonth ALL TO ([PRIMARY]);
GO

-- =====================================================================
-- ОСНОВНАЯ ТАБЛИЦА СОБЫТИЙ БЕЗОПАСНОСТИ (ПАРТИЦИОНИРОВАННАЯ)
-- =====================================================================

CREATE TABLE security_events.Events (
    EventId BIGINT IDENTITY(1,1),
    EventGuid UNIQUEIDENTIFIER DEFAULT NEWID(), -- Для гарантированной уникальности
    AgentId UNIQUEIDENTIFIER NOT NULL,

    -- Временные метки
    EventTime DATETIME2 NOT NULL, -- Время события на источнике
    ReceivedTime DATETIME2 DEFAULT GETUTCDATE(), -- Время получения сервером
    ProcessedTime DATETIME2, -- Время обработки AI

    -- Источник события
    SourceType VARCHAR(50) NOT NULL, -- windows_security, windows_system, sysmon, powershell, defender
    EventCode INT,
    Channel NVARCHAR(100),
    Provider NVARCHAR(100),
    Computer NVARCHAR(255), -- Имя хоста из события

    -- Нормализованные поля (ECS-подобные)
    Severity TINYINT DEFAULT 0, -- 0-info, 1-low, 2-medium, 3-high, 4-critical
    Category VARCHAR(50), -- authentication, process, network, file, registry, service
    Action VARCHAR(50), -- success, failure, created, deleted, modified, connected
    Outcome VARCHAR(20), -- success, failure, unknown

    -- Субъект (кто выполнил действие)
    SubjectUser NVARCHAR(200),
    SubjectDomain NVARCHAR(100),
    SubjectSid VARCHAR(100),
    SubjectLogonId VARCHAR(50),

    -- Объект (над чем выполнено действие)
    TargetUser NVARCHAR(200),
    TargetDomain NVARCHAR(100),
    TargetSid VARCHAR(100),
    TargetHost NVARCHAR(255),
    TargetIP VARCHAR(45),
    TargetPort INT,

    -- Процесс
    ProcessName NVARCHAR(500),
    ProcessId INT,
    ProcessPath NVARCHAR(1000),
    ProcessCommandLine NVARCHAR(MAX),
    ProcessHash VARCHAR(128), -- SHA256

    -- Родительский процесс
    ParentProcessName NVARCHAR(500),
    ParentProcessId INT,
    ParentProcessPath NVARCHAR(1000),
    ParentProcessCommandLine NVARCHAR(MAX),

    -- Сеть
    SourceIP VARCHAR(45),
    SourcePort INT,
    SourceHostname NVARCHAR(255),
    DestinationIP VARCHAR(45),
    DestinationPort INT,
    DestinationHostname NVARCHAR(255),
    Protocol VARCHAR(20), -- TCP, UDP, ICMP

    -- DNS (для Event ID 22 Sysmon)
    DNSQuery NVARCHAR(500),
    DNSResponse NVARCHAR(MAX), -- JSON array IP-адресов

    -- Файл
    FilePath NVARCHAR(1000),
    FileName NVARCHAR(255),
    FileHash VARCHAR(128), -- SHA256
    FileExtension VARCHAR(20),
    FileSize BIGINT,

    -- Реестр
    RegistryPath NVARCHAR(1000),
    RegistryKey NVARCHAR(500),
    RegistryValue NVARCHAR(MAX),
    RegistryValueType VARCHAR(50),

    -- Дополнительные поля
    Message NVARCHAR(MAX), -- Описание события
    RawEvent NVARCHAR(MAX), -- Исходное событие в JSON
    Tags NVARCHAR(500), -- JSON array тегов

    -- MITRE ATT&CK маппинг
    MitreAttackTactic VARCHAR(50),
    MitreAttackTechnique VARCHAR(20),
    MitreAttackSubtechnique VARCHAR(30),

    -- AI-анализ (Yandex GPT)
    AIProcessed BIT DEFAULT 0,
    AIScore DECIMAL(5,2), -- 0.00 - 100.00
    AICategory VARCHAR(100),
    AIDescription NVARCHAR(1000),
    AIConfidence DECIMAL(5,2), -- Уверенность AI в оценке
    AIIsAttack BIT,

    -- Геолокация (для внешних IP)
    GeoCountry VARCHAR(2), -- ISO код
    GeoCity NVARCHAR(100),

    -- Контрольная сумма для защиты от изменения (требование ЦБ)
    EventHash AS CONVERT(VARCHAR(64), HASHBYTES('SHA2_256',
        CONCAT(CAST(EventId AS VARCHAR), CAST(EventTime AS VARCHAR), CAST(AgentId AS VARCHAR), RawEvent)
    ), 2) PERSISTED,

    -- Ограничения
    CONSTRAINT PK_Events PRIMARY KEY CLUSTERED (EventTime, EventId),
    CONSTRAINT FK_Events_Agent FOREIGN KEY (AgentId) REFERENCES assets.Agents(AgentId),
    CONSTRAINT CK_Events_Severity CHECK (Severity BETWEEN 0 AND 4),
    CONSTRAINT CK_Events_Outcome CHECK (Outcome IN ('success', 'failure', 'unknown'))

) ON PS_EventsByMonth(EventTime);
GO

-- =====================================================================
-- ИНДЕКСЫ ДЛЯ ТАБЛИЦЫ СОБЫТИЙ
-- =====================================================================

-- Columnstore индекс для аналитических запросов (дашборды, отчёты)
CREATE NONCLUSTERED COLUMNSTORE INDEX NCCI_Events_Analytics
ON security_events.Events (
    EventTime, ReceivedTime, AgentId, Computer,
    Severity, Category, Action, Outcome,
    SubjectUser, SubjectDomain,
    TargetUser, TargetIP,
    ProcessName, ProcessPath,
    SourceIP, DestinationIP,
    MitreAttackTactic, MitreAttackTechnique,
    AIScore, AIIsAttack
);
GO

-- Индексы для частых запросов
CREATE NONCLUSTERED INDEX IX_Events_AgentId ON security_events.Events(AgentId, EventTime DESC);
CREATE NONCLUSTERED INDEX IX_Events_Severity ON security_events.Events(Severity, EventTime DESC) WHERE Severity >= 3;
CREATE NONCLUSTERED INDEX IX_Events_Category ON security_events.Events(Category, EventTime DESC) WHERE Category IS NOT NULL;
CREATE NONCLUSTERED INDEX IX_Events_SubjectUser ON security_events.Events(SubjectUser, EventTime DESC) WHERE SubjectUser IS NOT NULL;
CREATE NONCLUSTERED INDEX IX_Events_SourceIP ON security_events.Events(SourceIP, EventTime DESC) WHERE SourceIP IS NOT NULL;
CREATE NONCLUSTERED INDEX IX_Events_DestIP ON security_events.Events(DestinationIP, EventTime DESC) WHERE DestinationIP IS NOT NULL;
CREATE NONCLUSTERED INDEX IX_Events_ProcessName ON security_events.Events(ProcessName, EventTime DESC) WHERE ProcessName IS NOT NULL;
CREATE NONCLUSTERED INDEX IX_Events_AIProcessed ON security_events.Events(AIProcessed, EventTime) WHERE AIProcessed = 0;
CREATE NONCLUSTERED INDEX IX_Events_MITRE ON security_events.Events(MitreAttackTactic, MitreAttackTechnique, EventTime DESC) WHERE MitreAttackTactic IS NOT NULL;
CREATE UNIQUE NONCLUSTERED INDEX IX_Events_EventGuid ON security_events.Events(EventGuid);
GO

-- =====================================================================
-- ПРАВИЛА ДЕТЕКЦИИ
-- =====================================================================

CREATE TABLE config.DetectionRules (
    RuleId INT IDENTITY(1,1) PRIMARY KEY,
    RuleName NVARCHAR(200) NOT NULL UNIQUE,
    Description NVARCHAR(1000),
    IsEnabled BIT DEFAULT 1,

    -- Приоритет
    Severity TINYINT DEFAULT 2, -- severity алерта при срабатывании
    Priority INT DEFAULT 50, -- Порядок применения (меньше = раньше)

    -- Тип правила
    RuleType VARCHAR(20) NOT NULL, -- simple, threshold, correlation, sigma, ml
    RuleLogic NVARCHAR(MAX) NOT NULL, -- JSON с условиями или Sigma YAML

    -- Временные параметры для threshold/correlation
    TimeWindowMinutes INT,
    ThresholdCount INT,
    GroupByFields NVARCHAR(500), -- JSON array полей для группировки

    -- Условия
    SourceTypes NVARCHAR(500), -- JSON array типов источников
    EventCodes NVARCHAR(500), -- JSON array кодов событий
    Categories NVARCHAR(500), -- JSON array категорий

    -- Действия при срабатывании
    Actions NVARCHAR(MAX), -- JSON: [{type: "alert", ...}, {type: "notify", ...}]
    AutoEscalate BIT DEFAULT 0, -- Автоматически создавать инцидент

    -- MITRE ATT&CK маппинг
    MitreAttackTactic VARCHAR(50),
    MitreAttackTechnique VARCHAR(20),
    MitreAttackSubtechnique VARCHAR(30),

    -- Исключения (whitelist)
    Exceptions NVARCHAR(MAX), -- JSON с условиями исключений

    -- Статистика
    TotalMatches BIGINT DEFAULT 0,
    FalsePositives INT DEFAULT 0,
    LastMatch DATETIME2,

    -- Метаданные
    CreatedBy INT REFERENCES config.Users(UserId),
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    UpdatedBy INT REFERENCES config.Users(UserId),
    UpdatedAt DATETIME2,
    Tags NVARCHAR(500), -- JSON array

    CONSTRAINT CK_DetectionRules_RuleType CHECK (RuleType IN ('simple', 'threshold', 'correlation', 'sigma', 'ml')),
    CONSTRAINT CK_DetectionRules_Severity CHECK (Severity BETWEEN 0 AND 4)
);
GO

CREATE NONCLUSTERED INDEX IX_DetectionRules_Enabled ON config.DetectionRules(IsEnabled, Priority) WHERE IsEnabled = 1;
CREATE NONCLUSTERED INDEX IX_DetectionRules_MITRE ON config.DetectionRules(MitreAttackTactic, MitreAttackTechnique);
GO

-- =====================================================================
-- АЛЕРТЫ (СРАБОТАВШИЕ ПРАВИЛА)
-- =====================================================================

CREATE TABLE incidents.Alerts (
    AlertId BIGINT IDENTITY(1,1) PRIMARY KEY,
    AlertGuid UNIQUEIDENTIFIER DEFAULT NEWID(),
    RuleId INT REFERENCES config.DetectionRules(RuleId),

    -- Классификация
    Severity TINYINT NOT NULL,
    Title NVARCHAR(500) NOT NULL,
    Description NVARCHAR(MAX),
    Category VARCHAR(50), -- intrusion, malware, policy_violation, anomaly, recon

    -- Связанные события
    EventIds NVARCHAR(MAX), -- JSON array of EventIds
    EventCount INT DEFAULT 1,
    FirstEventTime DATETIME2,
    LastEventTime DATETIME2,

    -- Контекст (из событий)
    AgentId UNIQUEIDENTIFIER REFERENCES assets.Agents(AgentId),
    Hostname NVARCHAR(255),
    Username NVARCHAR(200),
    SourceIP VARCHAR(45),
    TargetIP VARCHAR(45),
    ProcessName NVARCHAR(500),

    -- MITRE ATT&CK
    MitreAttackTactic VARCHAR(50),
    MitreAttackTechnique VARCHAR(20),
    MitreAttackSubtechnique VARCHAR(30),

    -- Статус работы
    Status VARCHAR(20) DEFAULT 'new', -- new, acknowledged, investigating, resolved, false_positive
    AssignedTo INT REFERENCES config.Users(UserId),
    Priority TINYINT DEFAULT 2, -- 1-low, 2-medium, 3-high, 4-critical

    -- AI-анализ
    AIAnalysis NVARCHAR(MAX), -- JSON с анализом от Yandex GPT
    AIRecommendations NVARCHAR(MAX), -- Рекомендации по реагированию
    AIConfidence DECIMAL(5,2),

    -- Инцидент
    IncidentId INT, -- Связь с инцидентом (может быть NULL)

    -- Временные метки
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    AcknowledgedAt DATETIME2,
    ResolvedAt DATETIME2,
    UpdatedAt DATETIME2,

    -- Комментарии и история
    Comments NVARCHAR(MAX), -- JSON array комментариев
    ActionsTaken NVARCHAR(MAX), -- JSON array предпринятых действий

    -- Для отчётов ЦБ
    OperationalRiskCategory VARCHAR(100), -- Категория операционного риска (716-П)
    EstimatedDamage_RUB DECIMAL(15,2), -- Оценка ущерба
    IsReportable BIT DEFAULT 1, -- Требует отчёта регулятору

    CONSTRAINT CK_Alerts_Severity CHECK (Severity BETWEEN 0 AND 4),
    CONSTRAINT CK_Alerts_Status CHECK (Status IN ('new', 'acknowledged', 'investigating', 'resolved', 'false_positive')),
    CONSTRAINT CK_Alerts_Priority CHECK (Priority BETWEEN 1 AND 4)
);
GO

-- Индексы для алертов
CREATE NONCLUSTERED INDEX IX_Alerts_Status ON incidents.Alerts(Status, CreatedAt DESC);
CREATE NONCLUSTERED INDEX IX_Alerts_Severity ON incidents.Alerts(Severity DESC, CreatedAt DESC);
CREATE NONCLUSTERED INDEX IX_Alerts_AgentId ON incidents.Alerts(AgentId, CreatedAt DESC);
CREATE NONCLUSTERED INDEX IX_Alerts_AssignedTo ON incidents.Alerts(AssignedTo, Status);
CREATE NONCLUSTERED INDEX IX_Alerts_Incident ON incidents.Alerts(IncidentId) WHERE IncidentId IS NOT NULL;
CREATE NONCLUSTERED INDEX IX_Alerts_Unresolved ON incidents.Alerts(CreatedAt DESC) WHERE Status NOT IN ('resolved', 'false_positive');
CREATE UNIQUE NONCLUSTERED INDEX IX_Alerts_AlertGuid ON incidents.Alerts(AlertGuid);
GO

-- =====================================================================
-- ИНЦИДЕНТЫ (ГРУППЫ СВЯЗАННЫХ АЛЕРТОВ)
-- =====================================================================

CREATE TABLE incidents.Incidents (
    IncidentId INT IDENTITY(1,1) PRIMARY KEY,
    IncidentGuid UNIQUEIDENTIFIER DEFAULT NEWID(),

    -- Основная информация
    Title NVARCHAR(500) NOT NULL,
    Description NVARCHAR(MAX),
    Severity TINYINT NOT NULL, -- Максимальный severity среди алертов
    Category VARCHAR(50), -- intrusion, malware, data_breach, policy_violation, anomaly

    -- Связанные алерты
    AlertCount INT DEFAULT 0,
    EventCount INT DEFAULT 0,

    -- Затронутые системы
    AffectedAgents NVARCHAR(MAX), -- JSON array AgentIds
    AffectedUsers NVARCHAR(MAX), -- JSON array usernames
    AffectedAssets INT DEFAULT 0, -- Количество затронутых хостов

    -- Таймлайн
    StartTime DATETIME2, -- Время первого события
    EndTime DATETIME2, -- Время последнего события
    DetectedAt DATETIME2 DEFAULT GETUTCDATE(), -- Когда инцидент был обнаружен

    -- Статус работы
    Status VARCHAR(20) DEFAULT 'open', -- open, investigating, contained, resolved, closed
    AssignedTo INT REFERENCES config.Users(UserId),
    Priority TINYINT DEFAULT 2,

    -- AI-анализ инцидента
    AISummary NVARCHAR(MAX), -- Краткое описание
    AITimeline NVARCHAR(MAX), -- JSON timeline событий
    AIRootCause NVARCHAR(MAX), -- Предполагаемая причина
    AIRecommendations NVARCHAR(MAX), -- Рекомендации
    AIImpactAssessment NVARCHAR(MAX), -- Оценка воздействия

    -- MITRE ATT&CK (может быть несколько тактик/техник)
    MitreAttackTactics NVARCHAR(500), -- JSON array
    MitreAttackTechniques NVARCHAR(500), -- JSON array
    AttackChain NVARCHAR(MAX), -- JSON описание цепочки атаки

    -- Реагирование
    ContainmentActions NVARCHAR(MAX), -- JSON array действий по сдерживанию
    RemediationActions NVARCHAR(MAX), -- JSON array действий по устранению
    LessonsLearned NVARCHAR(MAX), -- Выводы

    -- Для отчётов ЦБ РФ
    OperationalRiskCategory VARCHAR(100), -- 716-П
    EstimatedDamage_RUB DECIMAL(15,2),
    ActualDamage_RUB DECIMAL(15,2),
    IsReportedToCBR BIT DEFAULT 0, -- Отчитались ли в ЦБ
    CBRReportDate DATETIME2,
    CBRIncidentNumber VARCHAR(100), -- Номер инцидента из ФинЦЕРТ

    -- Временные метки
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    UpdatedAt DATETIME2,
    ClosedAt DATETIME2,

    -- Комментарии и история
    WorkLog NVARCHAR(MAX), -- JSON array записей о работе

    CONSTRAINT CK_Incidents_Severity CHECK (Severity BETWEEN 0 AND 4),
    CONSTRAINT CK_Incidents_Status CHECK (Status IN ('open', 'investigating', 'contained', 'resolved', 'closed')),
    CONSTRAINT CK_Incidents_Priority CHECK (Priority BETWEEN 1 AND 4)
);
GO

-- Индексы для инцидентов
CREATE NONCLUSTERED INDEX IX_Incidents_Status ON incidents.Incidents(Status, Severity DESC, CreatedAt DESC);
CREATE NONCLUSTERED INDEX IX_Incidents_Severity ON incidents.Incidents(Severity DESC, CreatedAt DESC);
CREATE NONCLUSTERED INDEX IX_Incidents_AssignedTo ON incidents.Incidents(AssignedTo, Status);
CREATE NONCLUSTERED INDEX IX_Incidents_CBRReportable ON incidents.Incidents(IsReportedToCBR, CreatedAt DESC) WHERE IsReportedToCBR = 0;
CREATE UNIQUE NONCLUSTERED INDEX IX_Incidents_IncidentGuid ON incidents.Incidents(IncidentGuid);
GO

-- Обновление связи алертов с инцидентами
ALTER TABLE incidents.Alerts
ADD CONSTRAINT FK_Alerts_Incident FOREIGN KEY (IncidentId) REFERENCES incidents.Incidents(IncidentId);
GO

-- =====================================================================
-- ОТЧЁТЫ ДЛЯ ЦБ РФ И КОМПЛАЕНСА
-- =====================================================================

-- История экспортов для регулятора
CREATE TABLE compliance.CBRReports (
    ReportId INT IDENTITY(1,1) PRIMARY KEY,
    ReportGuid UNIQUEIDENTIFIER DEFAULT NEWID(),

    -- Тип отчёта
    ReportType VARCHAR(50) NOT NULL, -- form_0403203, fincert_notification, operational_risk, incident_report
    ReportPeriodStart DATETIME2,
    ReportPeriodEnd DATETIME2,

    -- Содержимое
    ReportData NVARCHAR(MAX), -- JSON с данными отчёта
    ReportFormat VARCHAR(20), -- json, xml, excel, pdf
    FileContent VARBINARY(MAX), -- Бинарный файл для Excel/PDF
    FileName NVARCHAR(255),
    FileHash VARCHAR(64), -- SHA256 для контроля целостности

    -- Связанные сущности
    IncidentIds NVARCHAR(MAX), -- JSON array
    AlertIds NVARCHAR(MAX), -- JSON array

    -- Статус
    Status VARCHAR(20) DEFAULT 'draft', -- draft, ready, sent, confirmed
    GeneratedBy INT REFERENCES config.Users(UserId),
    GeneratedAt DATETIME2 DEFAULT GETUTCDATE(),
    SentAt DATETIME2,
    SentBy INT REFERENCES config.Users(UserId),

    -- Метаданные
    Notes NVARCHAR(MAX),

    CONSTRAINT CK_CBRReports_Type CHECK (ReportType IN ('form_0403203', 'fincert_notification', 'operational_risk', 'incident_report', 'audit_export')),
    CONSTRAINT CK_CBRReports_Status CHECK (Status IN ('draft', 'ready', 'sent', 'confirmed'))
);
GO

CREATE NONCLUSTERED INDEX IX_CBRReports_Type ON compliance.CBRReports(ReportType, GeneratedAt DESC);
CREATE NONCLUSTERED INDEX IX_CBRReports_Status ON compliance.CBRReports(Status);
CREATE UNIQUE NONCLUSTERED INDEX IX_CBRReports_ReportGuid ON compliance.CBRReports(ReportGuid);
GO

-- Аудит изменений для соответствия ГОСТ Р 57580
CREATE TABLE compliance.AuditLog (
    LogId BIGINT IDENTITY(1,1) PRIMARY KEY,
    LogGuid UNIQUEIDENTIFIER DEFAULT NEWID(),

    -- Кто
    UserId INT REFERENCES config.Users(UserId),
    Username NVARCHAR(100),

    -- Что
    Action VARCHAR(50) NOT NULL, -- login, logout, create, update, delete, export, view
    ObjectType VARCHAR(50), -- event, alert, incident, rule, user, agent, setting
    ObjectId NVARCHAR(100),
    ObjectName NVARCHAR(255),

    -- Детали
    Details NVARCHAR(MAX), -- JSON с подробностями действия
    OldValue NVARCHAR(MAX), -- Старое значение (для update)
    NewValue NVARCHAR(MAX), -- Новое значение (для update)

    -- Контекст
    IPAddress VARCHAR(45),
    UserAgent NVARCHAR(500),
    SessionId UNIQUEIDENTIFIER,

    -- Результат
    Outcome VARCHAR(20) DEFAULT 'success', -- success, failure
    ErrorMessage NVARCHAR(1000),

    -- Время
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),

    -- Контрольная сумма для защиты от изменения
    LogHash AS CONVERT(VARCHAR(64), HASHBYTES('SHA2_256',
        CONCAT(CAST(LogId AS VARCHAR), CAST(CreatedAt AS VARCHAR), Action, ObjectType, Details)
    ), 2) PERSISTED,

    CONSTRAINT CK_AuditLog_Action CHECK (Action IN (
        'login', 'logout', 'login_failed',
        'create', 'update', 'delete', 'view',
        'export', 'import',
        'rule_triggered', 'alert_created', 'incident_escalated',
        'setting_changed', 'user_created', 'user_deleted',
        'report_generated', 'report_sent'
    )),
    CONSTRAINT CK_AuditLog_Outcome CHECK (Outcome IN ('success', 'failure'))
);
GO

-- Индексы для аудит лога
CREATE NONCLUSTERED INDEX IX_AuditLog_UserId ON compliance.AuditLog(UserId, CreatedAt DESC);
CREATE NONCLUSTERED INDEX IX_AuditLog_Action ON compliance.AuditLog(Action, CreatedAt DESC);
CREATE NONCLUSTERED INDEX IX_AuditLog_ObjectType ON compliance.AuditLog(ObjectType, ObjectId, CreatedAt DESC);
CREATE NONCLUSTERED INDEX IX_AuditLog_CreatedAt ON compliance.AuditLog(CreatedAt DESC);
CREATE UNIQUE NONCLUSTERED INDEX IX_AuditLog_LogGuid ON compliance.AuditLog(LogGuid);
GO

-- =====================================================================
-- ПРИМЕНЕНИЕ СЖАТИЯ ДЛЯ ЭКОНОМИИ МЕСТА (требование ЦБ - хранение 5 лет)
-- =====================================================================

-- Сжатие таблицы событий
ALTER TABLE security_events.Events REBUILD PARTITION = ALL WITH (DATA_COMPRESSION = PAGE);
GO

-- Сжатие columnstore индекса
ALTER INDEX NCCI_Events_Analytics ON security_events.Events REBUILD WITH (DATA_COMPRESSION = COLUMNSTORE_ARCHIVE);
GO

-- Сжатие других больших таблиц
ALTER TABLE incidents.Alerts REBUILD WITH (DATA_COMPRESSION = PAGE);
ALTER TABLE compliance.AuditLog REBUILD WITH (DATA_COMPRESSION = PAGE);
ALTER TABLE assets.InstalledSoftware REBUILD WITH (DATA_COMPRESSION = PAGE);
GO

-- =====================================================================
-- КОММЕНТАРИИ К ТАБЛИЦАМ ДЛЯ ДОКУМЕНТАЦИИ
-- =====================================================================

EXEC sys.sp_addextendedproperty
    @name = N'MS_Description',
    @value = N'Основная таблица событий безопасности. Партиционирована по месяцам. Хранение: минимум 5 лет (требование ЦБ 683-П).',
    @level0type = N'SCHEMA', @level0name = 'security_events',
    @level1type = N'TABLE', @level1name = 'Events';
GO

EXEC sys.sp_addextendedproperty
    @name = N'MS_Description',
    @value = N'Журнал аудита всех действий пользователей системы. Защищён контрольной суммой от изменений (ГОСТ Р 57580).',
    @level0type = N'SCHEMA', @level0name = 'compliance',
    @level1type = N'TABLE', @level1name = 'AuditLog';
GO

EXEC sys.sp_addextendedproperty
    @name = N'MS_Description',
    @value = N'История экспортов данных для ЦБ РФ. Хранит отчёты по формам 683-П, 716-П, 747-П с контрольными суммами.',
    @level0type = N'SCHEMA', @level0name = 'compliance',
    @level1type = N'TABLE', @level1name = 'CBRReports';
GO

-- =====================================================================
-- ЗАВЕРШЕНИЕ
-- =====================================================================

PRINT 'Схема базы данных SIEM_DB успешно создана!';
PRINT 'Создано:';
PRINT '  - 5 схем (security_events, config, incidents, assets, compliance)';
PRINT '  - 18 таблиц с индексами и ограничениями';
PRINT '  - Партиционирование для событий на 3 года';
PRINT '  - Columnstore индексы для аналитики';
PRINT '  - Защита от изменений через контрольные суммы';
PRINT '';
PRINT 'Следующий шаг: Запустить database/procedures.sql для создания хранимых процедур';
GO
