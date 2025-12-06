-- ============================================================================
-- Migration: 002_create_saved_searches.sql
-- Description: Create SavedSearches table for storing user search filters
-- Date: 2024-12-06
-- ============================================================================

-- ============================================================================
-- Create SavedSearches table
-- ============================================================================

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'SavedSearches' AND schema_id = SCHEMA_ID('config'))
BEGIN
    CREATE TABLE config.SavedSearches (
        SavedSearchId INT IDENTITY(1,1) PRIMARY KEY,
        Name NVARCHAR(255) NOT NULL,
        Description NVARCHAR(MAX),
        SearchType NVARCHAR(20) NOT NULL, -- events, alerts, incidents
        Filters NVARCHAR(MAX) NOT NULL, -- JSON string with filter parameters
        UserId INT NOT NULL,
        IsShared BIT DEFAULT 0 NOT NULL, -- If true, all users can see this search
        CreatedAt DATETIME DEFAULT GETUTCDATE() NOT NULL,
        UpdatedAt DATETIME DEFAULT GETUTCDATE() NOT NULL,

        -- Foreign keys
        CONSTRAINT FK_SavedSearches_User FOREIGN KEY (UserId)
            REFERENCES config.Users(UserId) ON DELETE CASCADE,

        -- Constraints
        CONSTRAINT CHK_SavedSearches_SearchType
            CHECK (SearchType IN ('events', 'alerts', 'incidents'))
    );

    -- Indexes
    CREATE INDEX IX_SavedSearches_Name ON config.SavedSearches(Name);
    CREATE INDEX IX_SavedSearches_SearchType ON config.SavedSearches(SearchType);
    CREATE INDEX IX_SavedSearches_UserId ON config.SavedSearches(UserId);
    CREATE INDEX IX_SavedSearches_IsShared ON config.SavedSearches(IsShared);
    CREATE INDEX IX_SavedSearches_CreatedAt ON config.SavedSearches(CreatedAt DESC);

    PRINT 'Table config.SavedSearches created successfully';
END
ELSE
BEGIN
    PRINT 'Table config.SavedSearches already exists, skipping...';
END
GO

-- ============================================================================
-- Create trigger to auto-update UpdatedAt
-- ============================================================================

IF NOT EXISTS (SELECT * FROM sys.triggers WHERE name = 'TR_SavedSearches_UpdatedAt')
BEGIN
    EXEC('
    CREATE TRIGGER config.TR_SavedSearches_UpdatedAt
    ON config.SavedSearches
    AFTER UPDATE
    AS
    BEGIN
        SET NOCOUNT ON;
        UPDATE config.SavedSearches
        SET UpdatedAt = GETUTCDATE()
        FROM config.SavedSearches s
        INNER JOIN inserted i ON s.SavedSearchId = i.SavedSearchId;
    END
    ');

    PRINT 'Trigger config.TR_SavedSearches_UpdatedAt created successfully';
END
ELSE
BEGIN
    PRINT 'Trigger config.TR_SavedSearches_UpdatedAt already exists, skipping...';
END
GO

PRINT '============================================================================';
PRINT 'Migration 002_create_saved_searches.sql completed successfully';
PRINT '============================================================================';
