# Спецификация интеграции с FreeScout

## Обзор

Интеграция между SIEM системой и helpdesk FreeScout для автоматического управления тикетами, двусторонней синхронизации и отслеживания коммуникаций.

**FreeScout**: Open-source helpdesk и общий почтовый ящик (альтернатива Help Scout, Zendesk)
**Используемый модуль**: API & Webhooks Module
**Документация**: https://freescout.net/module/api-webhooks/

> **Связанная документация:**
> - [Руководство по быстрой установке](QUICK_INSTALL.md) - Сначала установите SIEM систему
> - [Руководство по настройке Phase 1](PHASE1_SETUP.md) - Быстрая настройка FreeScout
> - [Анализ рынка](MARKET_ANALYSIS.md) - Сравнение функций

---

## Цели

1. **Автоматическое создание тикетов** - Алерты/инциденты автоматически создают тикеты в FreeScout
2. **Двусторонняя синхронизация** - Изменения статуса в FreeScout обновляют SIEM и наоборот
3. **Отслеживание коммуникаций** - Все коммуникации аналитиков хранятся в обеих системах
4. **Сохранение контекста** - Полный контекст инцидента доступен в тикете
5. **Снижение ручной работы** - Нет двойного ввода данных, автоматизированные рабочие процессы

---

## Архитектура

```
┌─────────────────────┐          API/Webhooks          ┌──────────────────┐
│   SIEM Backend      │◄────────────────────────────►  │   FreeScout      │
│   (FastAPI)         │         HTTP/HTTPS             │   (Laravel)      │
└─────────────────────┘                                └──────────────────┘
         │                                                       │
         ├─ POST /tickets - Создать тикет                       │
         ├─ GET /tickets/{id} - Получить статус тикета          │
         ├─ PATCH /tickets/{id} - Обновить тикет                │
         ├─ POST /tickets/{id}/notes - Добавить заметку         │
         │                                                       │
         ◄─ Webhook: ticket.created                             │
         ◄─ Webhook: ticket.updated                             │
         ◄─ Webhook: ticket.status_changed                      │
         ◄─ Webhook: ticket.note_added                          │
```

---

## Интеграция с API FreeScout

### Конфигурация (`.env`)

```bash
# Настройки FreeScout
FREESCOUT_ENABLED=true
FREESCOUT_URL=https://helpdesk.example.com
FREESCOUT_API_KEY=your_api_key_here
FREESCOUT_MAILBOX_ID=1

# Правила создания тикетов
FREESCOUT_AUTO_CREATE_ON_ALERT=true
FREESCOUT_AUTO_CREATE_SEVERITY_MIN=3  # Только High и Critical
FREESCOUT_AUTO_CREATE_ON_INCIDENT=true

# Настройки синхронизации
FREESCOUT_SYNC_INTERVAL_SECONDS=60
FREESCOUT_WEBHOOK_SECRET=webhook_secret_key
```

### Используемые API endpoints

#### 1. Создание тикета (POST /api/conversations)

```python
{
    "type": "email",
    "mailboxId": 1,
    "subject": "SIEM Alert: Обнаружена Brute Force атака",
    "customer": {
        "email": "siem@example.com",
        "firstName": "SIEM",
        "lastName": "System"
    },
    "threads": [
        {
            "type": "customer",
            "text": "Детали алерта...",
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

**Ответ**:
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

#### 2. Получение тикета (GET /api/conversations/{id})

```python
response = requests.get(
    f"{FREESCOUT_URL}/api/conversations/{ticket_id}",
    headers={"X-FreeScout-API-Key": FREESCOUT_API_KEY}
)
```

**Ответ**:
```json
{
    "id": 789,
    "status": 2,  # 1=active, 2=pending, 3=closed
    "state": 2,   # 1=draft, 2=published, 3=deleted
    "assignee": {
        "id": 1,
        "firstName": "Иван",
        "lastName": "Петров"
    },
    "threads": [...]
}
```

#### 3. Обновление тикета (PATCH /api/conversations/{id})

```python
{
    "status": 3,  # Закрыть тикет
    "assignee": 2,
    "tags": ["resolved", "false-positive"]
}
```

#### 4. Добавление заметки (POST /api/conversations/{id}/threads)

```python
{
    "type": "note",
    "text": "SIEM: Инцидент локализован. Вредоносный процесс завершён.",
    "user": 1
}
```

---

## Интеграция Webhook

### Endpoint получения Webhook

**SIEM Backend**: `POST /api/v1/integrations/freescout/webhook`

### Настройка Webhook в FreeScout

В панели администратора FreeScout → API & Webhooks:

```
Webhook URL: https://siem.example.com/api/v1/integrations/freescout/webhook
Secret Key: [такой же как FREESCOUT_WEBHOOK_SECRET]
События:
  ✅ conversation.created
  ✅ conversation.updated
  ✅ conversation.status_changed
  ✅ conversation.assigned
  ✅ conversation.customer_replied
  ✅ conversation.note_added
```

### События Webhook

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

**Действие SIEM**: Сохранить ID тикета FreeScout в Алерте/Инциденте

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

**Действие SIEM**:
- Если тикет FreeScout закрыт → Пометить алерт SIEM как "resolved"
- Если тикет FreeScout переоткрыт → Пометить алерт SIEM как "acknowledged"

#### 3. conversation.note_added
```json
{
    "event": "conversation.note_added",
    "data": {
        "conversation_id": 789,
        "thread": {
            "type": "note",
            "text": "Заметки аналитика...",
            "created_by": 1,
            "created_at": "2025-12-05T10:15:00Z"
        }
    }
}
```

**Действие SIEM**: Добавить в журнал работы Алерта/Инцидента

---

## Изменения схемы базы данных

### Новые таблицы

#### `freescout_tickets`
```sql
CREATE TABLE freescout_tickets (
    ticket_id SERIAL PRIMARY KEY,
    freescout_id INTEGER NOT NULL,  -- ID тикета FreeScout
    freescout_number INTEGER,        -- Номер тикета FreeScout
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

### Обновления существующих таблиц

#### Таблица `alerts` - Добавить колонку
```sql
ALTER TABLE alerts ADD COLUMN freescout_ticket_id INTEGER REFERENCES freescout_tickets(ticket_id);
CREATE INDEX idx_alerts_freescout_ticket ON alerts(freescout_ticket_id);
```

#### Таблица `incidents` - Добавить колонку
```sql
ALTER TABLE incidents ADD COLUMN freescout_ticket_id INTEGER REFERENCES freescout_tickets(ticket_id);
CREATE INDEX idx_incidents_freescout_ticket ON incidents(freescout_ticket_id);
```

---

## Реализация Backend

### 1. Клиент FreeScout (`backend/app/services/freescout_client.py`)

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
        """Создать тикет FreeScout из алерта SIEM"""
        payload = {
            "type": "email",
            "mailboxId": self.mailbox_id,
            "subject": f"SIEM Алерт #{alert.AlertId}: {alert.Title}",
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
            logger.error(f"Не удалось создать тикет FreeScout: {response.text}")
            return None

    def _format_alert_body(self, alert: Alert) -> str:
        """Форматировать детали алерта в HTML для тикета"""
        return f"""
<h2>Детали алерта</h2>
<ul>
  <li><strong>ID алерта:</strong> {alert.AlertId}</li>
  <li><strong>Название:</strong> {alert.Title}</li>
  <li><strong>Критичность:</strong> {self._severity_name(alert.Severity)}</li>
  <li><strong>Компьютер:</strong> {alert.Computer}</li>
  <li><strong>Пользователь:</strong> {alert.Username}</li>
  <li><strong>IP источника:</strong> {alert.SourceIP}</li>
  <li><strong>Первое обнаружение:</strong> {alert.FirstSeenAt}</li>
  <li><strong>Кол-во событий:</strong> {alert.EventCount}</li>
</ul>

<h3>Описание</h3>
<p>{alert.Description}</p>

<h3>MITRE ATT&CK</h3>
<ul>
  <li><strong>Тактика:</strong> {alert.MitreAttackTactic}</li>
  <li><strong>Техника:</strong> {alert.MitreAttackTechnique}</li>
</ul>

<p><a href="https://siem.example.com/alerts/{alert.AlertId}">Просмотреть в SIEM</a></p>
"""

    def update_ticket_status(self, ticket_id: int, status: str) -> bool:
        """Обновить статус тикета FreeScout"""
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
        """Добавить заметку к тикету FreeScout"""
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
        """Проверить подпись webhook"""
        expected = hmac.new(
            settings.freescout_webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)
```

### 2. Обработчик Webhook (`backend/app/api/v1/integrations/freescout.py`)

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
    Получение webhooks от FreeScout
    """
    # Проверка подписи
    body = await request.body()
    signature = request.headers.get("X-FreeScout-Signature", "")

    if not FreeScoutClient.verify_webhook_signature(body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверная подпись webhook"
        )

    # Парсинг webhook
    data = await request.json()
    event_type = data.get("event")
    conversation = data.get("data", {}).get("conversation", {})

    # Обработка различных событий
    if event_type == "conversation.status_changed":
        handle_status_change(db, conversation)
    elif event_type == "conversation.note_added":
        handle_note_added(db, data)
    elif event_type == "conversation.assigned":
        handle_assignment(db, conversation)

    return {"success": True}

def handle_status_change(db: Session, conversation: Dict):
    """Синхронизировать статус тикета FreeScout с алертом SIEM"""
    freescout_id = conversation.get("id")
    new_status = conversation.get("status")

    # Найти связанный тикет
    ticket = db.query(FreeScoutTicket).filter(
        FreeScoutTicket.freescout_id == freescout_id
    ).first()

    if not ticket:
        return

    # Обновить статус алерта SIEM
    if ticket.alert_id:
        alert = db.query(Alert).filter(Alert.AlertId == ticket.alert_id).first()
        if alert and new_status == 3:  # closed
            alert.Status = "resolved"
            alert.Resolution = "resolved"
            db.commit()
```

---

## Интеграция Frontend

### Обновления страницы алертов

Добавить кнопку "Создать тикет":

```typescript
const handleCreateTicket = async (alertId: number) => {
  try {
    const result = await apiService.createFreeScoutTicket(alertId)
    message.success(`Тикет #${result.ticket_number} создан`)
    // Обновить алерт для отображения ссылки на тикет
    loadAlert(alertId)
  } catch (error) {
    message.error('Не удалось создать тикет')
  }
}
```

### Отображение ссылки на тикет

```typescript
{alert.freescout_ticket_url && (
  <Alert
    message="Тикет FreeScout"
    description={
      <a href={alert.freescout_ticket_url} target="_blank">
        Просмотреть тикет #{alert.freescout_ticket_number}
      </a>
    }
    type="info"
    showIcon
  />
)}
```

---

## План тестирования

### 1. Unit-тесты
- Вызовы API клиента FreeScout
- Проверка подписи webhook
- Создание тикета из алерта
- Логика синхронизации статусов

### 2. Интеграционные тесты
- Создание тикета FreeScout из алерта SIEM
- Обновление алерта SIEM при изменении статуса в FreeScout
- Двусторонняя синхронизация
- Обработка webhooks

### 3. E2E тестовые сценарии

**Сценарий 1: От алерта до решения**
1. SIEM обнаруживает brute force атаку → Создаёт алерт
2. Алерт вызывает создание тикета FreeScout
3. Аналитик назначает тикет себе в FreeScout
4. Аналитик добавляет заметки расследования в FreeScout
5. SIEM получает webhook с заметкой → Добавляет в журнал работы
6. Аналитик закрывает тикет в FreeScout
7. SIEM получает webhook о закрытии → Помечает алерт как resolved

**Сценарий 2: Ручное создание тикета**
1. Аналитик просматривает алерт в SIEM
2. Нажимает кнопку "Создать тикет"
3. Тикет создаётся в FreeScout с контекстом алерта
4. URL тикета отображается в алерте SIEM

**Сценарий 3: Рабочий процесс инцидента**
1. Несколько алертов коррелируются в инцидент
2. Инцидент автоматически создаёт тикет FreeScout
3. Все связанные алерты привязаны к одному тикету
4. Обновления статуса инцидента синхронизируются с FreeScout

---

## Метрики и мониторинг

### Метрики успеха
- **Процент создания тикетов**: 95%+ high/critical алертов создают тикеты
- **Задержка синхронизации**: < 5 секунд от события FreeScout до обновления SIEM
- **Успешность синхронизации**: 99%+ успешных синхронизаций
- **Ручное создание тикетов**: < 5% (большинство должны создаваться автоматически)

### Мониторинг

```python
# Метрики Prometheus
freescout_tickets_created_total = Counter('freescout_tickets_created_total')
freescout_sync_errors_total = Counter('freescout_sync_errors_total')
freescout_webhook_latency_seconds = Histogram('freescout_webhook_latency_seconds')
```

---

## Соображения безопасности

1. **Хранение API ключа**: Храните API ключ FreeScout в `.env`, никогда в коде
2. **Подпись Webhook**: Всегда проверяйте HMAC подпись
3. **Только HTTPS**: URL webhook FreeScout должен использовать HTTPS
4. **Rate Limiting**: Ограничьте вызовы API для предотвращения злоупотреблений
5. **Санитизация данных**: Санитизируйте HTML в теле тикетов

---

## Документация

### Руководство администратора
- Как настроить интеграцию FreeScout
- Как получить API ключ
- Как настроить webhooks
- Как протестировать подключение

### Руководство пользователя
- Как создавать тикеты из алертов
- Как просматривать статус тикета в SIEM
- Как работает синхронизация статусов
- Лучшие практики

---

## Чеклист развёртывания

- [ ] Модуль API & Webhooks FreeScout установлен
- [ ] API ключ FreeScout сгенерирован
- [ ] `.env` SIEM настроен с параметрами FreeScout
- [ ] Миграции базы данных выполнены
- [ ] Webhook FreeScout настроен с URL SIEM
- [ ] Секретный ключ webhook установлен в обеих системах
- [ ] HTTPS сертификат действителен для URL webhook
- [ ] Тестовое создание тикета работает
- [ ] Тестовая доставка webhook работает
- [ ] Тестовая синхронизация статусов в обе стороны
- [ ] Мониторинг логов на ошибки

---

**Приоритет реализации**: Фаза 1 - Неделя 1 (3 дня)

**Зависимости**:
- Работающий экземпляр FreeScout
- Модуль API & Webhooks приобретён/установлен
- HTTPS endpoint для webhooks

**Автор**: Команда разработки SIEM
**Последнее обновление**: 2025-12-08
