-- ============================================================================
-- Migration: 001_create_system_settings.sql
-- Description: Create SystemSettings table and FreeScoutTickets table
-- Date: 2024-12-06
-- ============================================================================

-- ============================================================================
-- Create SystemSettings table
-- ============================================================================

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'SystemSettings' AND schema_id = SCHEMA_ID('config'))
BEGIN
    CREATE TABLE config.SystemSettings (
        SettingId INT IDENTITY(1,1) PRIMARY KEY,
        SettingKey NVARCHAR(100) NOT NULL UNIQUE,
        SettingValue NVARCHAR(MAX),
        SettingType NVARCHAR(50) DEFAULT 'string', -- string, boolean, integer, json
        Category NVARCHAR(50), -- freescout, email, ai, threat_intel, system
        Description NVARCHAR(MAX),
        IsEncrypted BIT DEFAULT 0,
        CreatedAt DATETIME DEFAULT GETUTCDATE(),
        UpdatedAt DATETIME
    );

    -- Indexes
    CREATE INDEX IX_SystemSettings_Key ON config.SystemSettings(SettingKey);
    CREATE INDEX IX_SystemSettings_Category ON config.SystemSettings(Category);

    PRINT 'Table config.SystemSettings created successfully';
END
ELSE
BEGIN
    PRINT 'Table config.SystemSettings already exists, skipping...';
END
GO

-- ============================================================================
-- Create FreeScoutTickets table
-- ============================================================================

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'FreeScoutTickets' AND schema_id = SCHEMA_ID('incidents'))
BEGIN
    CREATE TABLE incidents.FreeScoutTickets (
        TicketId INT IDENTITY(1,1) PRIMARY KEY,
        FreeScoutConversationId INT NOT NULL,
        FreeScoutConversationNumber INT NOT NULL,
        AlertId INT NULL,
        IncidentId INT NULL,
        TicketUrl NVARCHAR(500),
        TicketStatus NVARCHAR(20), -- active, closed, spam
        TicketSubject NVARCHAR(500),
        CreatedAt DATETIME DEFAULT GETUTCDATE(),
        UpdatedAt DATETIME,
        LastSyncedAt DATETIME,

        -- Foreign keys
        CONSTRAINT FK_FreeScoutTickets_Alert FOREIGN KEY (AlertId)
            REFERENCES incidents.Alerts(AlertId) ON DELETE SET NULL,
        CONSTRAINT FK_FreeScoutTickets_Incident FOREIGN KEY (IncidentId)
            REFERENCES incidents.Incidents(IncidentId) ON DELETE SET NULL
    );

    -- Indexes
    CREATE UNIQUE INDEX IX_FreeScoutTickets_ConversationId ON incidents.FreeScoutTickets(FreeScoutConversationId);
    CREATE INDEX IX_FreeScoutTickets_AlertId ON incidents.FreeScoutTickets(AlertId);
    CREATE INDEX IX_FreeScoutTickets_IncidentId ON incidents.FreeScoutTickets(IncidentId);
    CREATE INDEX IX_FreeScoutTickets_Status ON incidents.FreeScoutTickets(TicketStatus);

    PRINT 'Table incidents.FreeScoutTickets created successfully';
END
ELSE
BEGIN
    PRINT 'Table incidents.FreeScoutTickets already exists, skipping...';
END
GO

-- ============================================================================
-- Insert default settings
-- ============================================================================

-- FreeScout settings
IF NOT EXISTS (SELECT * FROM config.SystemSettings WHERE SettingKey = 'freescout_enabled')
BEGIN
    INSERT INTO config.SystemSettings (SettingKey, SettingValue, SettingType, Category, Description)
    VALUES ('freescout_enabled', 'false', 'boolean', 'freescout', 'Enable FreeScout integration');
END

IF NOT EXISTS (SELECT * FROM config.SystemSettings WHERE SettingKey = 'freescout_auto_create_on_alert')
BEGIN
    INSERT INTO config.SystemSettings (SettingKey, SettingValue, SettingType, Category, Description)
    VALUES ('freescout_auto_create_on_alert', 'false', 'boolean', 'freescout', 'Automatically create tickets for alerts');
END

IF NOT EXISTS (SELECT * FROM config.SystemSettings WHERE SettingKey = 'freescout_auto_create_severity_min')
BEGIN
    INSERT INTO config.SystemSettings (SettingKey, SettingValue, SettingType, Category, Description)
    VALUES ('freescout_auto_create_severity_min', '3', 'integer', 'freescout', 'Minimum severity for auto-ticket creation (0-4)');
END

-- Email settings
IF NOT EXISTS (SELECT * FROM config.SystemSettings WHERE SettingKey = 'smtp_enabled')
BEGIN
    INSERT INTO config.SystemSettings (SettingKey, SettingValue, SettingType, Category, Description)
    VALUES ('smtp_enabled', 'false', 'boolean', 'email', 'Enable email notifications');
END

IF NOT EXISTS (SELECT * FROM config.SystemSettings WHERE SettingKey = 'smtp_port')
BEGIN
    INSERT INTO config.SystemSettings (SettingKey, SettingValue, SettingType, Category, Description)
    VALUES ('smtp_port', '587', 'integer', 'email', 'SMTP server port');
END

IF NOT EXISTS (SELECT * FROM config.SystemSettings WHERE SettingKey = 'smtp_use_tls')
BEGIN
    INSERT INTO config.SystemSettings (SettingKey, SettingValue, SettingType, Category, Description)
    VALUES ('smtp_use_tls', 'true', 'boolean', 'email', 'Use TLS for SMTP connection');
END

IF NOT EXISTS (SELECT * FROM config.SystemSettings WHERE SettingKey = 'email_alert_recipients')
BEGIN
    INSERT INTO config.SystemSettings (SettingKey, SettingValue, SettingType, Category, Description)
    VALUES ('email_alert_recipients', '', 'string', 'email', 'Comma-separated list of email recipients for alert notifications');
END

IF NOT EXISTS (SELECT * FROM config.SystemSettings WHERE SettingKey = 'email_alert_min_severity')
BEGIN
    INSERT INTO config.SystemSettings (SettingKey, SettingValue, SettingType, Category, Description)
    VALUES ('email_alert_min_severity', '3', 'integer', 'email', 'Minimum severity for alert email notifications (0-4, default: 3=High)');
END

-- AI settings
IF NOT EXISTS (SELECT * FROM config.SystemSettings WHERE SettingKey = 'ai_provider')
BEGIN
    INSERT INTO config.SystemSettings (SettingKey, SettingValue, SettingType, Category, Description)
    VALUES ('ai_provider', 'deepseek', 'string', 'ai', 'AI provider: deepseek, yandex_gpt, or none');
END

IF NOT EXISTS (SELECT * FROM config.SystemSettings WHERE SettingKey = 'ai_auto_analyze_alerts')
BEGIN
    INSERT INTO config.SystemSettings (SettingKey, SettingValue, SettingType, Category, Description)
    VALUES ('ai_auto_analyze_alerts', 'true', 'boolean', 'ai', 'Automatically analyze alerts with AI');
END

IF NOT EXISTS (SELECT * FROM config.SystemSettings WHERE SettingKey = 'ai_auto_analyze_severity_min')
BEGIN
    INSERT INTO config.SystemSettings (SettingKey, SettingValue, SettingType, Category, Description)
    VALUES ('ai_auto_analyze_severity_min', '3', 'integer', 'ai', 'Minimum severity for AI analysis (0-4)');
END

-- Threat Intelligence settings
IF NOT EXISTS (SELECT * FROM config.SystemSettings WHERE SettingKey = 'threat_intel_enabled')
BEGIN
    INSERT INTO config.SystemSettings (SettingKey, SettingValue, SettingType, Category, Description)
    VALUES ('threat_intel_enabled', 'false', 'boolean', 'threat_intel', 'Enable threat intelligence lookups');
END

PRINT 'Default settings inserted successfully';
GO

-- ============================================================================
-- Create EmailNotifications table for tracking sent emails
-- ============================================================================

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'EmailNotifications' AND schema_id = SCHEMA_ID('config'))
BEGIN
    CREATE TABLE config.EmailNotifications (
        NotificationId INT IDENTITY(1,1) PRIMARY KEY,
        RecipientEmail NVARCHAR(255) NOT NULL,
        Subject NVARCHAR(500),
        Body NVARCHAR(MAX),
        AlertId INT NULL,
        IncidentId INT NULL,
        NotificationType NVARCHAR(50), -- alert, incident, system, test
        Status NVARCHAR(20), -- sent, failed, pending
        ErrorMessage NVARCHAR(MAX),
        SentAt DATETIME,
        CreatedAt DATETIME DEFAULT GETUTCDATE(),

        -- Foreign keys
        CONSTRAINT FK_EmailNotifications_Alert FOREIGN KEY (AlertId)
            REFERENCES incidents.Alerts(AlertId) ON DELETE SET NULL,
        CONSTRAINT FK_EmailNotifications_Incident FOREIGN KEY (IncidentId)
            REFERENCES incidents.Incidents(IncidentId) ON DELETE SET NULL
    );

    -- Indexes
    CREATE INDEX IX_EmailNotifications_AlertId ON config.EmailNotifications(AlertId);
    CREATE INDEX IX_EmailNotifications_IncidentId ON config.EmailNotifications(IncidentId);
    CREATE INDEX IX_EmailNotifications_Status ON config.EmailNotifications(Status);
    CREATE INDEX IX_EmailNotifications_CreatedAt ON config.EmailNotifications(CreatedAt);

    PRINT 'Table config.EmailNotifications created successfully';
END
ELSE
BEGIN
    PRINT 'Table config.EmailNotifications already exists, skipping...';
END
GO

-- ============================================================================
-- Create ThreatIntelligence table for caching threat intel lookups
-- ============================================================================

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ThreatIntelligence' AND schema_id = SCHEMA_ID('enrichment'))
BEGIN
    -- Create enrichment schema if it doesn't exist
    IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'enrichment')
    BEGIN
        EXEC('CREATE SCHEMA enrichment');
        PRINT 'Schema enrichment created successfully';
    END

    CREATE TABLE enrichment.ThreatIntelligence (
        IntelId INT IDENTITY(1,1) PRIMARY KEY,
        Indicator NVARCHAR(500) NOT NULL, -- IP, domain, hash, etc.
        IndicatorType NVARCHAR(50), -- ip, domain, file_hash, url
        Source NVARCHAR(50), -- virustotal, abuseipdb, alienvault, etc.
        IsMalicious BIT,
        ThreatScore INT, -- 0-100
        Categories NVARCHAR(MAX), -- JSON array of categories
        Tags NVARCHAR(MAX), -- JSON array of tags
        RawData NVARCHAR(MAX), -- JSON with full response
        FirstSeen DATETIME DEFAULT GETUTCDATE(),
        LastChecked DATETIME DEFAULT GETUTCDATE(),
        CheckCount INT DEFAULT 1,

        -- For rate limiting and caching
        CacheExpiresAt DATETIME
    );

    -- Indexes
    CREATE UNIQUE INDEX IX_ThreatIntelligence_Indicator_Source ON enrichment.ThreatIntelligence(Indicator, Source);
    CREATE INDEX IX_ThreatIntelligence_Type ON enrichment.ThreatIntelligence(IndicatorType);
    CREATE INDEX IX_ThreatIntelligence_IsMalicious ON enrichment.ThreatIntelligence(IsMalicious);
    CREATE INDEX IX_ThreatIntelligence_LastChecked ON enrichment.ThreatIntelligence(LastChecked);

    PRINT 'Table enrichment.ThreatIntelligence created successfully';
END
ELSE
BEGIN
    PRINT 'Table enrichment.ThreatIntelligence already exists, skipping...';
END
GO

PRINT '============================================================================';
PRINT 'Migration 001_create_system_settings.sql completed successfully!';
PRINT '============================================================================';
