# FreeScout Integration Specification

## 📋 Overview

Integration between SIEM System and FreeScout helpdesk for automated ticket management, bidirectional synchronization, and communication tracking.

**FreeScout**: Open-source helpdesk and shared inbox (alternative to Help Scout, Zendesk)
**Available Module**: API & Webhooks Module
**Documentation**: https://freescout.net/module/api-webhooks/

> **Related Documentation:**
> - [Quick Installation Guide](QUICK_INSTALL.md) - Install SIEM system first
> - [Phase 1 Setup Guide](PHASE1_SETUP.md) - Quick configuration guide for FreeScout
> - [Market Analysis](MARKET_ANALYSIS.md) - Feature comparison

---

## 🎯 Goals

1. **Automated Ticket Creation** - Alerts/incidents automatically create FreeScout tickets
2. **Bidirectional Sync** - Status changes in FreeScout update SIEM, and vice versa
3. **Communication Tracking** - All analyst communications stored in both systems
4. **Context Preservation** - Full incident context available in ticket
5. **Reduced Manual Work** - No double data entry, automated workflows

---

## 🏗️ Architecture

```
┌─────────────────────┐          API/Webhooks          ┌──────────────────┐
│   SIEM Backend      │◄────────────────────────────►  │   FreeScout      │
│   (FastAPI)         │         HTTP/HTTPS             │   (Laravel)      │
└─────────────────────┘                                └──────────────────┘
         │                                                       │
         ├─ POST /tickets - Create ticket                       │
         ├─ GET /tickets/{id} - Get ticket status               │
         ├─ PATCH /tickets/{id} - Update ticket                 │
         ├─ POST /tickets/{id}/notes - Add note                 │
         │                                                       │
         ◄─ Webhook: ticket.created                             │
         ◄─ Webhook: ticket.updated                             │
         ◄─ Webhook: ticket.status_changed                      │
         ◄─ Webhook: ticket.note_added                          │
```

---

## 📡 FreeScout API Integration

### Configuration (`.env`)

```bash
# FreeScout Configuration
FREESCOUT_ENABLED=true
FREESCOUT_URL=https://helpdesk.example.com
FREESCOUT_API_KEY=your_api_key_here
FREESCOUT_MAILBOX_ID=1

# Ticket Creation Rules
FREESCOUT_AUTO_CREATE_ON_ALERT=true
FREESCOUT_AUTO_CREATE_SEVERITY_MIN=3  # High and Critical only
FREESCOUT_AUTO_CREATE_ON_INCIDENT=true

# Sync Settings
FREESCOUT_SYNC_INTERVAL_SECONDS=60
FREESCOUT_WEBHOOK_SECRET=webhook_secret_key
```

### API Endpoints Used

#### 1. Create Ticket (POST /api/conversations)

```python
{
    "type": "email",
    "mailboxId": 1,
    "subject": "SIEM Alert: Brute Force Attack Detected",
    "customer": {
        "email": "siem@example.com",
        "firstName": "SIEM",
        "lastName": "System"
    },
    "threads": [
        {
            "type": "customer",
            "text": "Alert details...",
            "customer": {
                "email": "siem@example.com"
            }
        }
    ],
    "tags": ["siem", "critical", "brute-force"],
    "customFields": {
        "alert_id": 12345,
        "severity": 4,
        "mitre_tactic": "Credential Access"
    }
}
```

**Response**:
```json
{
    "id": 789,
    "number": 456,
    "subject": "...",
    "status": 1,
    "state": 1,
    "type": "email",
    "url": "https://helpdesk.example.com/conversation/789"
}
```

#### 2. Get Ticket (GET /api/conversations/{id})

```python
response = requests.get(
    f"{FREESCOUT_URL}/api/conversations/{ticket_id}",
    headers={"X-FreeScout-API-Key": FREESCOUT_API_KEY}
)
```

**Response**:
```json
{
    "id": 789,
    "status": 2,  # 1=active, 2=pending, 3=closed
    "state": 2,   # 1=draft, 2=published, 3=deleted
    "assignee": {
        "id": 1,
        "firstName": "John",
        "lastName": "Doe"
    },
    "threads": [...]
}
```

#### 3. Update Ticket (PATCH /api/conversations/{id})

```python
{
    "status": 3,  # Close ticket
    "assignee": 2,
    "tags": ["resolved", "false-positive"]
}
```

#### 4. Add Note (POST /api/conversations/{id}/threads)

```python
{
    "type": "note",
    "text": "SIEM: Incident contained. Malicious process terminated.",
    "user": 1
}
```

---

## 🪝 Webhook Integration

### Webhook Receiver Endpoint

**SIEM Backend**: `POST /api/v1/integrations/freescout/webhook`

### FreeScout Webhook Configuration

In FreeScout Admin Panel → API & Webhooks:

```
Webhook URL: https://siem.example.com/api/v1/integrations/freescout/webhook
Secret Key: [same as FREESCOUT_WEBHOOK_SECRET]
Events:
  ✅ conversation.created
  ✅ conversation.updated
  ✅ conversation.status_changed
  ✅ conversation.assigned
  ✅ conversation.customer_replied
  ✅ conversation.note_added
```

### Webhook Events

#### 1. conversation.created
```json
{
    "event": "conversation.created",
    "data": {
        "conversation": {
            "id": 789,
            "number": 456,
            "subject": "...",
            "status": 1,
            "assignee_id": 1,
            "created_at": "2025-12-05T10:00:00Z"
        }
    },
    "timestamp": "2025-12-05T10:00:00Z",
    "signature": "sha256_hmac_signature"
}
```

**SIEM Action**: Store FreeScout ticket ID in Alert/Incident

#### 2. conversation.status_changed
```json
{
    "event": "conversation.status_changed",
    "data": {
        "conversation": {
            "id": 789,
            "status": 3,  # closed
            "previous_status": 2  # pending
        }
    }
}
```

**SIEM Action**:
- If FreeScout ticket closed → Mark SIEM alert as "resolved"
- If FreeScout ticket reopened → Mark SIEM alert as "acknowledged"

#### 3. conversation.note_added
```json
{
    "event": "conversation.note_added",
    "data": {
        "conversation_id": 789,
        "thread": {
            "type": "note",
            "text": "Analyst notes...",
            "created_by": 1,
            "created_at": "2025-12-05T10:15:00Z"
        }
    }
}
```

**SIEM Action**: Add to Alert/Incident work log

---

## 🗄️ Database Schema Changes

### New Tables

#### `freescout_tickets`
```sql
CREATE TABLE freescout_tickets (
    ticket_id SERIAL PRIMARY KEY,
    freescout_id INTEGER NOT NULL,  -- FreeScout conversation ID
    freescout_number INTEGER,        -- FreeScout ticket number
    alert_id INTEGER REFERENCES alerts(alert_id),
    incident_id INTEGER REFERENCES incidents(incident_id),
    ticket_url TEXT,
    status VARCHAR(20),  -- 'active', 'pending', 'closed'
    assignee_id INTEGER,
    assignee_name VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    synced_at TIMESTAMP,
    CONSTRAINT ticket_alert_or_incident CHECK (
        (alert_id IS NOT NULL AND incident_id IS NULL) OR
        (alert_id IS NULL AND incident_id IS NOT NULL)
    )
);

CREATE INDEX idx_freescout_tickets_alert ON freescout_tickets(alert_id);
CREATE INDEX idx_freescout_tickets_incident ON freescout_tickets(incident_id);
CREATE INDEX idx_freescout_tickets_freescout_id ON freescout_tickets(freescout_id);
```

#### `freescout_sync_log`
```sql
CREATE TABLE freescout_sync_log (
    log_id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES freescout_tickets(ticket_id),
    direction VARCHAR(10),  -- 'to_freescout', 'from_freescout'
    event_type VARCHAR(50),  -- 'create', 'update', 'status_change', 'note_added'
    payload JSONB,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Existing Table Updates

#### `alerts` table - Add column
```sql
ALTER TABLE alerts ADD COLUMN freescout_ticket_id INTEGER REFERENCES freescout_tickets(ticket_id);
CREATE INDEX idx_alerts_freescout_ticket ON alerts(freescout_ticket_id);
```

#### `incidents` table - Add column
```sql
ALTER TABLE incidents ADD COLUMN freescout_ticket_id INTEGER REFERENCES freescout_tickets(ticket_id);
CREATE INDEX idx_incidents_freescout_ticket ON incidents(freescout_ticket_id);
```

---

## 💻 Backend Implementation

### 1. FreeScout Client (`backend/app/services/freescout_client.py`)

```python
import requests
from typing import Dict, Any, Optional
import hmac
import hashlib
from app.config import settings

class FreeScoutClient:
    def __init__(self):
        self.base_url = settings.freescout_url
        self.api_key = settings.freescout_api_key
        self.mailbox_id = settings.freescout_mailbox_id

    def _headers(self) -> Dict[str, str]:
        return {
            "X-FreeScout-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    def create_ticket_from_alert(self, alert: Alert) -> Optional[Dict]:
        """Create FreeScout ticket from SIEM alert"""
        payload = {
            "type": "email",
            "mailboxId": self.mailbox_id,
            "subject": f"SIEM Alert #{alert.AlertId}: {alert.Title}",
            "customer": {
                "email": "siem@example.com",
                "firstName": "SIEM",
                "lastName": "System"
            },
            "threads": [{
                "type": "customer",
                "text": self._format_alert_body(alert),
                "customer": {"email": "siem@example.com"}
            }],
            "tags": self._get_alert_tags(alert),
            "customFields": {
                "alert_id": alert.AlertId,
                "severity": alert.Severity,
                "computer": alert.Computer,
                "mitre_tactic": alert.MitreAttackTactic
            }
        }

        response = requests.post(
            f"{self.base_url}/api/conversations",
            headers=self._headers(),
            json=payload
        )

        if response.status_code == 201:
            return response.json()
        else:
            logger.error(f"Failed to create FreeScout ticket: {response.text}")
            return None

    def _format_alert_body(self, alert: Alert) -> str:
        """Format alert details as HTML for ticket"""
        return f"""
<h2>Alert Details</h2>
<ul>
  <li><strong>Alert ID:</strong> {alert.AlertId}</li>
  <li><strong>Title:</strong> {alert.Title}</li>
  <li><strong>Severity:</strong> {self._severity_name(alert.Severity)}</li>
  <li><strong>Computer:</strong> {alert.Computer}</li>
  <li><strong>Username:</strong> {alert.Username}</li>
  <li><strong>Source IP:</strong> {alert.SourceIP}</li>
  <li><strong>First Seen:</strong> {alert.FirstSeenAt}</li>
  <li><strong>Event Count:</strong> {alert.EventCount}</li>
</ul>

<h3>Description</h3>
<p>{alert.Description}</p>

<h3>MITRE ATT&CK</h3>
<ul>
  <li><strong>Tactic:</strong> {alert.MitreAttackTactic}</li>
  <li><strong>Technique:</strong> {alert.MitreAttackTechnique}</li>
</ul>

<p><a href="https://siem.example.com/alerts/{alert.AlertId}">View in SIEM</a></p>
"""

    def update_ticket_status(self, ticket_id: int, status: str) -> bool:
        """Update FreeScout ticket status"""
        status_map = {
            'open': 1,
            'pending': 2,
            'closed': 3
        }

        payload = {"status": status_map.get(status, 1)}

        response = requests.patch(
            f"{self.base_url}/api/conversations/{ticket_id}",
            headers=self._headers(),
            json=payload
        )

        return response.status_code == 200

    def add_note(self, ticket_id: int, note: str, user_id: int = 1) -> bool:
        """Add note to FreeScout ticket"""
        payload = {
            "type": "note",
            "text": note,
            "user": user_id
        }

        response = requests.post(
            f"{self.base_url}/api/conversations/{ticket_id}/threads",
            headers=self._headers(),
            json=payload
        )

        return response.status_code == 201

    @staticmethod
    def verify_webhook_signature(payload: bytes, signature: str) -> bool:
        """Verify webhook signature"""
        expected = hmac.new(
            settings.freescout_webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)
```

### 2. Webhook Handler (`backend/app/api/v1/integrations/freescout.py`)

```python
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.freescout_client import FreeScoutClient
from app.models.incident import Alert, Incident

router = APIRouter()

@router.post("/webhook")
async def freescout_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Receive webhooks from FreeScout
    """
    # Verify signature
    body = await request.body()
    signature = request.headers.get("X-FreeScout-Signature", "")

    if not FreeScoutClient.verify_webhook_signature(body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )

    # Parse webhook
    data = await request.json()
    event_type = data.get("event")
    conversation = data.get("data", {}).get("conversation", {})

    # Handle different events
    if event_type == "conversation.status_changed":
        handle_status_change(db, conversation)
    elif event_type == "conversation.note_added":
        handle_note_added(db, data)
    elif event_type == "conversation.assigned":
        handle_assignment(db, conversation)

    return {"success": True}

def handle_status_change(db: Session, conversation: Dict):
    """Sync FreeScout ticket status to SIEM alert"""
    freescout_id = conversation.get("id")
    new_status = conversation.get("status")

    # Find linked ticket
    ticket = db.query(FreeScoutTicket).filter(
        FreeScoutTicket.freescout_id == freescout_id
    ).first()

    if not ticket:
        return

    # Update SIEM alert status
    if ticket.alert_id:
        alert = db.query(Alert).filter(Alert.AlertId == ticket.alert_id).first()
        if alert and new_status == 3:  # closed
            alert.Status = "resolved"
            alert.Resolution = "resolved"
            db.commit()
```

---

## 🎨 Frontend Integration

### Alerts Page Updates

Add "Create Ticket" button:

```typescript
const handleCreateTicket = async (alertId: number) => {
  try {
    const result = await apiService.createFreeScoutTicket(alertId)
    message.success(`Ticket #${result.ticket_number} created`)
    // Refresh alert to show ticket link
    loadAlert(alertId)
  } catch (error) {
    message.error('Failed to create ticket')
  }
}
```

### Display Ticket Link

```typescript
{alert.freescout_ticket_url && (
  <Alert
    message="FreeScout Ticket"
    description={
      <a href={alert.freescout_ticket_url} target="_blank">
        View Ticket #{alert.freescout_ticket_number}
      </a>
    }
    type="info"
    showIcon
  />
)}
```

---

## 🧪 Testing Plan

### 1. Unit Tests
- FreeScout client API calls
- Webhook signature verification
- Ticket creation from alert
- Status sync logic

### 2. Integration Tests
- SIEM Alert → FreeScout Ticket creation
- FreeScout status change → SIEM alert update
- Bidirectional sync
- Webhook handling

### 3. E2E Test Scenarios

**Scenario 1: Alert to Resolution**
1. SIEM detects brute force attack → Creates alert
2. Alert triggers FreeScout ticket creation
3. Analyst assigns ticket to himself in FreeScout
4. Analyst adds investigation notes in FreeScout
5. SIEM receives note webhook → Adds to work log
6. Analyst closes ticket in FreeScout
7. SIEM receives closed webhook → Marks alert as resolved

**Scenario 2: Manual Ticket Creation**
1. Analyst views alert in SIEM
2. Clicks "Create Ticket" button
3. Ticket created in FreeScout with alert context
4. Ticket URL displayed in SIEM alert

**Scenario 3: Incident Workflow**
1. Multiple alerts correlated into incident
2. Incident auto-creates FreeScout ticket
3. All related alerts linked to same ticket
4. Incident status updates sync to FreeScout

---

## 📊 Metrics & Monitoring

### Success Metrics
- **Ticket Creation Rate**: 95%+ of high/critical alerts create tickets
- **Sync Latency**: < 5 seconds from FreeScout event to SIEM update
- **Sync Success Rate**: 99%+ successful syncs
- **Manual Ticket Creation**: < 5% (most should be automatic)

### Monitoring

```python
# Prometheus metrics
freescout_tickets_created_total = Counter('freescout_tickets_created_total')
freescout_sync_errors_total = Counter('freescout_sync_errors_total')
freescout_webhook_latency_seconds = Histogram('freescout_webhook_latency_seconds')
```

---

## 🔐 Security Considerations

1. **API Key Storage**: Store FreeScout API key in `.env`, never in code
2. **Webhook Signature**: Always verify HMAC signature
3. **HTTPS Only**: FreeScout webhook URL must use HTTPS
4. **Rate Limiting**: Limit API calls to prevent abuse
5. **Data Sanitization**: Sanitize HTML in ticket bodies

---

## 📚 Documentation

### Admin Guide
- How to configure FreeScout integration
- How to obtain API key
- How to set up webhooks
- How to test connection

### User Guide
- How to create tickets from alerts
- How to view ticket status in SIEM
- How status sync works
- Best practices

---

## 🚀 Deployment Checklist

- [ ] FreeScout API & Webhooks Module installed
- [ ] FreeScout API key generated
- [ ] SIEM `.env` configured with FreeScout settings
- [ ] Database migrations run
- [ ] FreeScout webhook configured with SIEM URL
- [ ] Webhook secret key set in both systems
- [ ] HTTPS certificate valid for webhook URL
- [ ] Test ticket creation works
- [ ] Test webhook delivery works
- [ ] Test status sync both directions
- [ ] Monitor logs for errors

---

**Implementation Priority**: Phase 1 - Week 1 (3 days)

**Dependencies**:
- FreeScout instance running
- API & Webhooks Module purchased/installed
- HTTPS endpoint for webhooks

**Author**: SIEM Development Team
**Last Updated**: 2025-12-05
