# WebSocket Real-Time Updates Guide

## 📡 Обзор

SIEM система поддерживает WebSocket для real-time обновлений событий, алертов, инцидентов и статистики агентов.

---

## 🔌 Доступные WebSocket endpoints

### Base URL
```
ws://localhost:8000/ws/
```

### Endpoints по каналам

| Endpoint | Описание | Сообщения |
|----------|----------|-----------|
| `/ws/events` | События безопасности | Новые события |
| `/ws/alerts` | Алерты | Создание, обновление, решение |
| `/ws/incidents` | Инциденты | Создание, эскалация, закрытие |
| `/ws/agents` | Статус агентов | Регистрация, online/offline |
| `/ws/dashboard` | Dashboard обновления | Все типы + статистика |
| `/ws/notifications` | Системные уведомления | Важные события системы |

---

## 🔐 Аутентификация

Все WebSocket соединения требуют JWT токен в query параметре:

```
ws://localhost:8000/ws/alerts?token=YOUR_JWT_TOKEN
```

### Получение токена

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "Admin123!"
  }'
```

Ответ:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 28800
}
```

---

## 📨 Формат сообщений

### Сообщение о подключении
```json
{
  "type": "connection",
  "status": "connected",
  "channel": "alerts",
  "timestamp": "2025-01-01T12:00:00"
}
```

### Новое событие
```json
{
  "type": "event",
  "action": "created",
  "data": {
    "event_id": 12345,
    "computer": "WS-001",
    "severity": 3,
    "message": "Failed login attempt",
    "source_type": "Windows Security",
    "event_code": 4625
  },
  "timestamp": "2025-01-01T12:00:00"
}
```

### Новый алерт
```json
{
  "type": "alert",
  "action": "created",
  "data": {
    "alert_id": 42,
    "title": "Multiple failed login attempts",
    "severity": 4,
    "category": "brute_force",
    "hostname": "WS-001",
    "status": "new"
  },
  "timestamp": "2025-01-01T12:00:00"
}
```

### Обновление статуса алерта
```json
{
  "type": "alert",
  "action": "acknowledged",
  "data": {
    "alert_id": 42,
    "status": "acknowledged",
    "assigned_to": "analyst",
    "acknowledged_at": "2025-01-01T12:05:00"
  },
  "timestamp": "2025-01-01T12:05:00"
}
```

### Статус агента
```json
{
  "type": "agent",
  "action": "offline",
  "data": {
    "agent_id": "uuid-here",
    "hostname": "WS-001",
    "status": "offline",
    "last_seen": "2025-01-01T11:55:00"
  },
  "timestamp": "2025-01-01T12:00:00"
}
```

### Dashboard статистика (каждые 30 секунд)
```json
{
  "type": "statistics",
  "action": "updated",
  "data": {
    "events": {
      "total_24h": 15432,
      "last_hour": 234,
      "high_severity": 12,
      "ai_attacks": 3
    },
    "alerts": {
      "new": 5,
      "critical": 2
    },
    "incidents": {
      "open": 1
    },
    "agents": {
      "online": 45,
      "offline": 3,
      "total": 48
    },
    "updated_at": "2025-01-01T12:00:00"
  },
  "timestamp": "2025-01-01T12:00:00"
}
```

### Системное уведомление
```json
{
  "type": "notification",
  "severity": "critical",
  "data": {
    "event_id": 12345,
    "computer": "DC-01",
    "ai_score": 95,
    "ai_category": "intrusion",
    "ai_description": "Обнаружена попытка атаки на контроллер домена",
    "message": "Multiple failed login attempts to DC-01"
  },
  "timestamp": "2025-01-01T12:00:00"
}
```

---

## 💻 Примеры подключения

### JavaScript / TypeScript (React)

```typescript
// WebSocket hook для React
import { useEffect, useState, useCallback } from 'react';

interface WebSocketMessage {
  type: string;
  action?: string;
  data: any;
  timestamp: string;
}

export function useWebSocket(channel: string, token: string) {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const websocket = new WebSocket(
      `ws://localhost:8000/ws/${channel}?token=${token}`
    );

    websocket.onopen = () => {
      console.log(`Connected to ${channel} channel`);
      setIsConnected(true);

      // Send ping every 30 seconds to keep connection alive
      const pingInterval = setInterval(() => {
        if (websocket.readyState === WebSocket.OPEN) {
          websocket.send('ping');
        }
      }, 30000);

      websocket.addEventListener('close', () => {
        clearInterval(pingInterval);
      });
    };

    websocket.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);
      console.log('Received:', message);

      setMessages((prev) => [...prev, message]);
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    websocket.onclose = () => {
      console.log(`Disconnected from ${channel} channel`);
      setIsConnected(false);
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, [channel, token]);

  const sendMessage = useCallback((message: string) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(message);
    }
  }, [ws]);

  return { messages, isConnected, sendMessage };
}

// Использование в компоненте
function Dashboard() {
  const token = localStorage.getItem('jwt_token');
  const { messages, isConnected } = useWebSocket('dashboard', token);

  useEffect(() => {
    const latestMessage = messages[messages.length - 1];
    if (latestMessage) {
      if (latestMessage.type === 'statistics') {
        // Обновить статистику на dashboard
        updateStatistics(latestMessage.data);
      } else if (latestMessage.type === 'alert') {
        // Показать уведомление о новом алерте
        showAlert(latestMessage.data);
      }
    }
  }, [messages]);

  return (
    <div>
      <StatusIndicator connected={isConnected} />
      {/* ... */}
    </div>
  );
}
```

### Python (для тестирования)

```python
import asyncio
import websockets
import json

async def connect_to_alerts():
    # Получить токен
    token = "your_jwt_token_here"

    uri = f"ws://localhost:8000/ws/alerts?token={token}"

    async with websockets.connect(uri) as websocket:
        print("Connected to alerts channel")

        # Ожидание сообщений
        while True:
            message = await websocket.recv()
            data = json.loads(message)

            print(f"Received: {data['type']}")
            print(json.dumps(data, indent=2))

            # Ответ на ping
            if data.get('type') == 'pong':
                continue

# Запуск
asyncio.run(connect_to_alerts())
```

---

## 🤖 Background Tasks

### AI Analyzer

Автоматически анализирует новые события каждые 60 секунд:

**Конфигурация** (.env):
```bash
# Интервал анализа (секунды)
AI_PROCESS_INTERVAL_SEC=60

# Размер батча для обработки
AI_BATCH_SIZE=10

# Количество попыток при ошибке
AI_RETRY_ATTEMPTS=3
```

**Что происходит:**
1. Выбирает неанализированные события (до 10 штук)
2. Анализирует через AI провайдер (DeepSeek/Yandex GPT)
3. Обновляет поля `AI*` в событиях
4. Для high-risk событий (score > 70):
   - Отправляет WebSocket уведомление
5. Для очень high-risk (score > 85):
   - Автоматически создаёт алерт
   - Отправляет уведомление на dashboard

### Dashboard Updater

Обновляет статистику каждые 30 секунд:

**Что происходит:**
1. Проверяет, есть ли подключённые клиенты к dashboard
2. Собирает статистику:
   - События за последние 24 часа и 1 час
   - Новые и критические алерты
   - Открытые инциденты
   - Статус агентов (online/offline)
3. Отправляет через WebSocket в канал `dashboard`

---

## 📊 Интеграция в API endpoints

Все API endpoints автоматически отправляют WebSocket уведомления:

### Events API
```python
# При создании события
await manager.broadcast_event({
    "event_id": event.EventId,
    "computer": event.Computer,
    # ...
})
```

### Alerts API
```python
# При создании алерта
await manager.broadcast_alert(alert_data, action="created")

# При обновлении
await manager.broadcast_alert(alert_data, action="acknowledged")
```

### Incidents API
```python
# При создании инцидента
await manager.broadcast_incident(incident_data, action="created")
```

### Agents API
```python
# При регистрации агента
await manager.broadcast_agent_status(agent_data, action="registered")

# При изменении статуса
await manager.broadcast_agent_status(agent_data, action="offline")
```

---

## 🔍 Мониторинг WebSocket

### Проверка активных соединений

```python
from app.websocket import get_connection_manager

manager = get_connection_manager()

# Количество соединений в канале
alerts_count = manager.get_channel_count("alerts")

# Всего соединений
total = manager.get_total_connections()
```

### Логи

WebSocket соединения логируются:
```
INFO - User admin connecting to alerts channel
INFO - Client connected to channel 'alerts' (total: 3)
INFO - User admin disconnected from alerts channel
INFO - Client disconnected from channel 'alerts' (remaining: 2)
```

---

## ⚙️ Настройка

### CORS для WebSocket

В `.env`:
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
CORS_ALLOW_CREDENTIALS=true
```

### Таймауты

По умолчанию WebSocket соединение живёт бесконечно. Используйте ping/pong для проверки:

```javascript
// Клиент отправляет ping каждые 30 секунд
setInterval(() => {
  websocket.send('ping');
}, 30000);

// Сервер отвечает pong
websocket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'pong') {
    console.log('Connection alive');
  }
};
```

---

## 🐛 Troubleshooting

### Ошибка: "Token required"
**Проблема:** Не передан JWT токен

**Решение:**
```javascript
// Правильно
ws://localhost:8000/ws/alerts?token=YOUR_JWT_TOKEN

// Неправильно
ws://localhost:8000/ws/alerts
```

### Ошибка: "Invalid token"
**Проблема:** Неверный или истёкший токен

**Решение:**
1. Получите новый токен через `/api/v1/auth/login`
2. Проверьте срок действия токена (default: 8 часов)

### WebSocket закрывается сразу после подключения
**Проблема:** Ошибка аутентификации

**Решение:**
1. Проверьте токен в базе данных (таблица `config.Sessions`)
2. Убедитесь, что пользователь активен
3. Проверьте логи backend

### Не приходят обновления
**Проблема:** Подключён не к тому каналу

**Решение:**
- Для всех обновлений → `/ws/dashboard`
- Для только алертов → `/ws/alerts`
- Для только событий → `/ws/events`

---

## 🎯 Best Practices

1. **Переподключение при разрыве**
   ```javascript
   function connectWithRetry() {
     const ws = new WebSocket(url);

     ws.onclose = () => {
       setTimeout(connectWithRetry, 5000); // Retry after 5 seconds
     };
   }
   ```

2. **Ping/Pong для keep-alive**
   ```javascript
   setInterval(() => ws.send('ping'), 30000);
   ```

3. **Обработка больших объёмов сообщений**
   ```javascript
   const messageQueue = [];
   const BATCH_SIZE = 10;

   ws.onmessage = (event) => {
     messageQueue.push(JSON.parse(event.data));

     if (messageQueue.length >= BATCH_SIZE) {
       processBatch(messageQueue.splice(0, BATCH_SIZE));
     }
   };
   ```

4. **Использование каналов по назначению**
   - Dashboard → Для главной страницы
   - Alerts → Для страницы алертов
   - Events → Для страницы событий
   - Agents → Для страницы агентов

---

## 📚 Дополнительные ресурсы

- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [WebSocket API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [React WebSocket Tutorial](https://blog.logrocket.com/websockets-tutorial-how-to-go-real-time-with-node-and-react-8e4693fbf843/)

---

**Готово!** 🎉 Ваша SIEM система теперь поддерживает real-time обновления через WebSocket!
