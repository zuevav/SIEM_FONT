# Phase 1 Setup Guide

Complete setup guide for Phase 1 features: Settings, Email Notifications, FreeScout Integration, and Threat Intelligence.

## Table of Contents

1. [Database Migration](#1-database-migration)
2. [Email Notifications](#2-email-notifications)
3. [FreeScout Integration](#3-freescout-integration)
4. [Threat Intelligence](#4-threat-intelligence)
5. [GeoIP Enrichment](#5-geoip-enrichment)
6. [System Updates](#6-system-updates)
7. [Testing](#7-testing)

---

## 1. Database Migration

Run the SQL migration to create required tables:

```bash
# Using sqlcmd (Linux/macOS)
sqlcmd -S localhost -U sa -P YourPassword -d SIEMDatabase \
  -i backend/migrations/001_create_system_settings.sql

# Using SQL Server Management Studio (Windows)
# Open backend/migrations/001_create_system_settings.sql and execute
```

**Tables created:**
- `config.SystemSettings` - All system settings with encryption
- `incidents.FreeScoutTickets` - FreeScout ticket tracking
- `config.EmailNotifications` - Email audit log
- `enrichment.ThreatIntelligence` - Threat intel cache

**Verify migration:**
```sql
SELECT COUNT(*) FROM config.SystemSettings;
-- Should return ~15 rows with default settings
```

---

## 2. Email Notifications

### 2.1 SMTP Configuration

Navigate to **Settings → Email Notifications** tab:

**Gmail Example:**
```
SMTP Host: smtp.gmail.com
SMTP Port: 587
Username: your-email@gmail.com
Password: your-app-password  # NOT your Gmail password!
From Email: siem@yourcompany.com
Use TLS: ✓ Enabled
```

> **Gmail App Password:** Google requires App Passwords for SMTP. Generate one at https://myaccount.google.com/apppasswords

**Yandex Mail Example:**
```
SMTP Host: smtp.yandex.ru
SMTP Port: 587
Username: your-email@yandex.ru
Password: your-password
From Email: siem@yourcompany.com
Use TLS: ✓ Enabled
```

**Mail.ru Example:**
```
SMTP Host: smtp.mail.ru
SMTP Port: 465 or 587
Username: your-email@mail.ru
Password: your-password
From Email: siem@yourcompany.com
Use TLS: ✓ Enabled
```

### 2.2 Recipients Configuration

**Add recipients (comma-separated):**
```
admin@company.com, security@company.com, soc@company.com
```

**Min Severity:** `3` (High and Critical only)

### 2.3 Test Email

1. Click **"Send Test Email"** button
2. Enter recipient email
3. Check inbox for test email
4. If failed, check error message

**Common issues:**
- ❌ "Authentication failed" → Wrong username/password
- ❌ "Connection refused" → Wrong host/port
- ❌ "TLS error" → Disable TLS or use port 465

### 2.4 Email Templates

Emails include:
- ✅ Severity badge (color-coded)
- ✅ Alert title and description
- ✅ Context (hostname, username, IP, process)
- ✅ MITRE ATT&CK tactics/techniques
- ✅ AI recommendations
- ✅ Threat intelligence results (if available)
- ✅ GeoIP location (if available)
- ✅ Direct link to alert in SIEM UI

**Automatic sending:**
Emails are sent automatically when:
- Alert severity ≥ configured threshold (default: 3 = High)
- SMTP is enabled
- Recipients are configured

---

## 3. FreeScout Integration

### 3.1 Prerequisites

1. **FreeScout instance** running (https://freescout.net)
2. **API & Webhooks Module** installed
3. **API Key** generated

### 3.2 Generate API Key

1. Login to FreeScout as admin
2. Go to **Manage → Settings → API**
3. Click **"Generate New API Key"**
4. Copy the key (starts with `fs_`)

### 3.3 Configuration

Navigate to **Settings → FreeScout Integration** tab:

```
FreeScout URL: https://helpdesk.yourcompany.com
API Key: fs_xxxxxxxxxxxxxxxxxxxxxxxx
Mailbox ID: 1
Auto-create tickets: ✓ Enabled
Min Severity: 3 (High and Critical only)
```

**Find Mailbox ID:**
```bash
curl -X GET "https://helpdesk.yourcompany.com/api/mailboxes" \
  -H "X-FreeScout-API-Key: fs_xxxxxxxxxxxxxxxxxxxxxxxx"
```

### 3.4 Test Connection

1. Click **"Test Connection"** button
2. Should show: `✓ Connected successfully. Found X mailbox(es)`
3. Displays mailbox name and ID

### 3.5 Webhook Configuration (Optional)

For bidirectional sync (FreeScout → SIEM):

1. Go to FreeScout **Manage → Settings → Webhooks**
2. Add new webhook:
   ```
   URL: https://your-siem.com/api/v1/integrations/freescout/webhook
   Events: conversation.status_changed, conversation.note_added
   Secret: (generate random string)
   ```
3. Update SIEM settings with webhook secret

### 3.6 Ticket Creation

**Automatic:**
When alert severity ≥ threshold, ticket is created automatically with:
- Subject: `[SIEM Alert #123] Alert Title`
- Alert details, context, MITRE ATT&CK, AI recommendations
- Tags: `siem`, `severity-high`, `category-name`
- Custom fields: `alert_id`, `severity`

**Manual:**
In alert details page, click **"Create FreeScout Ticket"** button

---

## 4. Threat Intelligence

### 4.1 Get API Keys

#### VirusTotal (Recommended)
1. Register at https://www.virustotal.com/gui/join-us
2. Free tier: 4 requests/minute (500/day)
3. Go to **Profile → API Key**
4. Copy API key

#### AbuseIPDB (Recommended)
1. Register at https://www.abuseipdb.com/register
2. Free tier: 1,000 requests/day
3. Go to **Account → API**
4. Copy API key

### 4.2 Configuration

Navigate to **Settings → Threat Intelligence** tab:

```
Enable Threat Intelligence: ✓
VirusTotal API Key: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AbuseIPDB API Key: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 4.3 Automatic Enrichment

When enabled, every new alert is automatically enriched:

**For SourceIP and TargetIP:**
1. ✅ VirusTotal IP reputation check
2. ✅ AbuseIPDB abuse confidence score
3. ✅ GeoIP location lookup
4. ✅ Results stored in `alert.AIAnalysis` JSON field
5. ✅ Cached for 24 hours

**Example enrichment data:**
```json
{
  "threat_intel": {
    "source_ip_intel": {
      "is_malicious": true,
      "max_threat_score": 85,
      "sources": {
        "virustotal": {
          "malicious_count": 12,
          "suspicious_count": 3,
          "categories": ["malware", "phishing"]
        },
        "abuseipdb": {
          "abuse_confidence_score": 92,
          "total_reports": 45
        }
      }
    },
    "source_ip_geoip": {
      "country_name": "Russia",
      "city": "Moscow",
      "latitude": 55.7558,
      "longitude": 37.6173
    }
  }
}
```

### 4.4 Manual Lookup

**API Endpoints:**
```bash
# Lookup IP
curl -X POST "http://localhost:8000/api/v1/enrichment/lookup/ip" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ip_address": "1.2.3.4"}'

# Lookup file hash
curl -X POST "http://localhost:8000/api/v1/enrichment/lookup/hash" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"file_hash": "44d88612fea8a8f36de82e1278abb02f"}'

# GeoIP only
curl "http://localhost:8000/api/v1/enrichment/geoip/8.8.8.8" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4.5 Cache Management

**Cache table:** `enrichment.ThreatIntelligence`

**View cache:**
```sql
SELECT
    Indicator,
    IndicatorType,
    Source,
    IsMalicious,
    ThreatScore,
    CheckCount,
    LastChecked
FROM enrichment.ThreatIntelligence
ORDER BY LastChecked DESC
LIMIT 20;
```

**Clear expired cache:**
```sql
DELETE FROM enrichment.ThreatIntelligence
WHERE CacheExpiresAt < GETUTCDATE();
```

---

## 5. GeoIP Enrichment

### 5.1 Download GeoLite2 Database

**Option 1: MaxMind Account (Recommended)**
1. Register at https://www.maxmind.com/en/geolite2/signup
2. Login → **Download Databases**
3. Download **GeoLite2 City** (MMDB format)
4. Extract `GeoLite2-City.mmdb`

**Option 2: Direct Download (may require account)**
```bash
# Download latest GeoLite2-City
wget https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb

# Or use curl
curl -L -o GeoLite2-City.mmdb \
  https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb
```

### 5.2 Install Database

**Docker (recommended):**
```bash
# Copy to docker volume
docker cp GeoLite2-City.mmdb siem-backend:/app/data/GeoLite2-City.mmdb

# Or mount volume in docker-compose.yml
volumes:
  - ./data/GeoLite2-City.mmdb:/app/data/GeoLite2-City.mmdb
```

**Linux system paths:**
```bash
# Option 1: /usr/share/GeoIP/
sudo mkdir -p /usr/share/GeoIP
sudo cp GeoLite2-City.mmdb /usr/share/GeoIP/

# Option 2: /var/lib/GeoIP/
sudo mkdir -p /var/lib/GeoIP
sudo cp GeoLite2-City.mmdb /var/lib/GeoIP/
```

### 5.3 Verify Installation

```bash
# Check service status
curl "http://localhost:8000/api/v1/enrichment/status" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Expected response:
{
  "threat_intelligence": {...},
  "geoip": {
    "available": true,
    "db_path": "/app/data/GeoLite2-City.mmdb"
  }
}
```

### 5.4 Update Database (Recommended Monthly)

MaxMind updates GeoLite2 monthly. Set up cron job:

```bash
# /etc/cron.monthly/update-geoip.sh
#!/bin/bash
curl -L -o /tmp/GeoLite2-City.mmdb \
  https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb

mv /tmp/GeoLite2-City.mmdb /usr/share/GeoIP/GeoLite2-City.mmdb

# Restart backend to reload database
docker restart siem-backend
```

---

## 6. System Updates

### 6.1 Check for Updates

Navigate to **Settings → System Updates** tab:

1. Click **"Check for Updates"**
2. Shows current version, git branch, commits behind
3. Displays changelog if updates available

### 6.2 Automatic Update

**⚠️ WARNING:** This will restart the backend service!

1. Click **"Update Now"** button
2. Confirms action
3. Progress modal shows:
   - Git pull
   - Docker image rebuild
   - Container restart
4. Page reloads after completion

**Manual update (if automatic fails):**
```bash
cd /path/to/SIEM_FONT
git pull origin main
docker-compose up -d --build
```

---

## 7. Testing

### 7.1 Test Email Notifications

Create test alert with high severity:

```bash
curl -X POST "http://localhost:8000/api/v1/alerts" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "severity": 4,
    "title": "Test High Severity Alert",
    "description": "Testing email notification",
    "category": "Test",
    "source_ip": "1.2.3.4"
  }'
```

**Expected:**
- ✅ Email sent to configured recipients
- ✅ Email contains alert details
- ✅ Entry in `config.EmailNotifications` table

### 7.2 Test FreeScout Integration

Create test alert with high severity (same as above).

**Expected:**
- ✅ Ticket created in FreeScout
- ✅ Entry in `incidents.FreeScoutTickets` table
- ✅ Ticket contains alert details

### 7.3 Test Threat Intelligence

Create alert with known malicious IP:

```bash
curl -X POST "http://localhost:8000/api/v1/alerts" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "severity": 3,
    "title": "Test Threat Intel",
    "description": "Testing threat intelligence enrichment",
    "category": "Test",
    "source_ip": "185.220.101.1"
  }'
```

**Expected:**
- ✅ Alert enriched with threat intel
- ✅ `alert.AIAnalysis` contains threat intel data
- ✅ Entry in `enrichment.ThreatIntelligence` cache
- ✅ Email/ticket includes threat intel results

### 7.4 Test GeoIP

Manual lookup:

```bash
curl "http://localhost:8000/api/v1/enrichment/geoip/8.8.8.8" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected response:**
```json
{
  "ip": "8.8.8.8",
  "country_code": "US",
  "country_name": "United States",
  "city": "Mountain View",
  "latitude": 37.386,
  "longitude": -122.0838,
  "timezone": "America/Los_Angeles"
}
```

---

## Troubleshooting

### Email not sending

1. Check SMTP settings in Settings UI
2. Click "Test Email" button
3. Check logs: `docker logs siem-backend | grep -i smtp`
4. Verify firewall allows outbound SMTP (port 587/465)

### FreeScout tickets not creating

1. Verify API key is correct
2. Check FreeScout URL (no trailing slash)
3. Test connection in Settings UI
4. Check logs: `docker logs siem-backend | grep -i freescout`

### Threat intel not working

1. Verify API keys are valid
2. Check rate limits (VT: 4/min, AbuseIPDB: 1000/day)
3. Enable threat intel in Settings
4. Check logs: `docker logs siem-backend | grep -i "threat intel"`

### GeoIP not available

1. Download GeoLite2-City.mmdb
2. Copy to `/usr/share/GeoIP/` or `/app/data/`
3. Restart backend: `docker restart siem-backend`
4. Check status: `/api/v1/enrichment/status`

---

## Next Steps

✅ Phase 1 Complete! You now have:
- Email notifications for critical alerts
- FreeScout ticket auto-creation
- Threat intelligence enrichment
- GeoIP location tracking
- System update mechanism

**Phase 2 (Optional):**
- Advanced threat hunting
- Custom detection rules
- SOAR playbooks
- Advanced reporting
