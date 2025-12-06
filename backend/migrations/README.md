# Database Migrations

This folder contains SQL migrations for the SIEM system database.

## Running Migrations

### Option 1: Manual Execution (Recommended for first time)

Connect to your SQL Server database and execute migrations in order:

```bash
# Using sqlcmd
sqlcmd -S localhost -U sa -P YourPassword -d SIEMDatabase -i migrations/001_create_system_settings.sql

# Or using SQL Server Management Studio (SSMS)
# Open the file and execute it
```

### Option 2: Using Python script

```bash
cd backend
python scripts/run_migrations.py
```

## Migration Files

- `001_create_system_settings.sql` - Creates SystemSettings, FreeScoutTickets, EmailNotifications, and ThreatIntelligence tables

## Tables Created

### config.SystemSettings
Stores all system settings (FreeScout, Email, AI, etc.) with encryption support for sensitive data.

### incidents.FreeScoutTickets
Tracks mapping between SIEM alerts/incidents and FreeScout tickets for synchronization.

### config.EmailNotifications
Logs all sent email notifications for audit trail.

### enrichment.ThreatIntelligence
Caches threat intelligence lookups (VirusTotal, AbuseIPDB, etc.) to avoid rate limiting.

## Post-Migration Steps

After running migrations, configure settings via the Settings page in the web UI:

1. **Email Configuration**
   - SMTP server, port, credentials
   - Test email delivery

2. **FreeScout Integration**
   - FreeScout URL, API key, Mailbox ID
   - Test connection

3. **AI Configuration**
   - Choose provider (DeepSeek/YandexGPT)
   - Add API keys

4. **Threat Intelligence**
   - Add VirusTotal API key
   - Add AbuseIPDB API key
