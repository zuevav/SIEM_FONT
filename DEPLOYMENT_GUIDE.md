# 🚀 SIEM System - Deployment Guide

## 📊 Статус проекта: 100% ЗАВЕРШЁН! ✅

Все компоненты системы полностью реализованы и готовы к production deployment.

---

## 🎯 Что готово к деплою

### ✅ Backend (Python/FastAPI)
- **70+ REST API endpoints**
- **6 WebSocket каналов** для real-time updates
- **AI Integration** (DeepSeek + Yandex GPT)
- **RBAC** с JWT authentication
- **Background tasks** (AI analyzer, dashboard updater)
- **CBR Compliance** (683-П, 716-П, 747-П, ГОСТ Р 57580)

### ✅ Frontend (React + TypeScript)
- **15 полнофункциональных страниц**
- **70+ API методов** в клиенте
- **Real-time WebSocket** интеграция
- **Dark/Light theme**
- **Russian localization**
- **Responsive design**

### ✅ Database
- **18 таблиц** в 5 схемах
- **11 хранимых процедур** для performance
- **9 триггеров** для защиты данных
- **Партиционирование** по месяцам
- **Поддержка:** PostgreSQL 15+ / MS SQL Server 2019+

### ✅ Agents & Monitoring
- **Windows Agent (Go)** - сбор событий и инвентаря
- **Network Monitor (Python)** - SNMP/Syslog/NetFlow/SNMP Traps
- **IPBan Integration** - защита от brute-force
- **File Integrity Monitoring** - через Sysmon

---

## 🔧 Quick Start Deployment

### Вариант 1: Docker Compose (Рекомендуется для быстрого старта)

```bash
# 1. Клонировать репозиторий
git clone <repository-url>
cd SIEM_FONT

# 2. Создать .env файл
cp .env.example .env
# Отредактировать .env (DB credentials, AI API keys, etc.)

# 3. Запустить все сервисы
docker-compose up -d

# 4. Проверить статус
docker-compose ps
docker-compose logs -f backend
```

Доступ:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### Вариант 2: Manual Installation (Production)

#### 1. Database Setup

**PostgreSQL (Рекомендуется):**
```bash
# Установка PostgreSQL 15
sudo apt install postgresql-15 postgresql-15-contrib

# Создание БД
sudo -u postgres psql
CREATE DATABASE siem_db;
CREATE USER siem_app WITH PASSWORD 'YourStrongPassword';
GRANT ALL PRIVILEGES ON DATABASE siem_db TO siem_app;
\q

# Миграция схемы
cd database
psql -U siem_app -d siem_db -f postgresql_schema.sql
```

**MS SQL Server:**
```powershell
# Выполнить скрипты по порядку
sqlcmd -S localhost -i database/schema.sql
sqlcmd -S localhost -i database/procedures.sql
sqlcmd -S localhost -i database/triggers.sql
sqlcmd -S localhost -i database/seed.sql
```

#### 2. Backend Setup

```bash
cd backend

# Создать venv
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Настроить .env
cp ../.env.example .env
# Отредактировать параметры

# Запустить
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 3. Frontend Setup

```bash
cd frontend

# Установить зависимости
npm install

# Создать .env.local
echo "VITE_API_URL=http://localhost:8000" > .env.local

# Development
npm run dev

# Production build
npm run build
npm run preview
```

#### 4. Windows Agent Setup

```powershell
cd agent

# Сборка
go build -o siem-agent.exe cmd/agent/main.go

# Конфигурация
cp config.yaml.example C:\ProgramData\SIEM\agent.yaml
# Отредактировать agent.yaml

# Установка как служба
.\siem-agent.exe install
Start-Service SIEM-Agent
```

#### 5. Network Monitor Setup (Linux)

```bash
cd network_monitor

# Создать venv
python3.11 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Конфигурация
cp config.yaml.example config.yaml
# Отредактировать config.yaml

# Установить как systemd service
sudo ./install.sh
sudo systemctl start siem-network-monitor
```

---

## 🔐 Безопасность

### Первый вход

**Default credentials:**
- Username: `admin`
- Password: `Admin123!`

⚠️ **ОБЯЗАТЕЛЬНО:** Смените пароль после первого входа!

### Рекомендации по безопасности

1. **Измените пароли** всех дефолтных пользователей
2. **Настройте HTTPS** (nginx reverse proxy)
3. **Включите firewall** правила
4. **Настройте JWT** secret key (уникальный для каждой установки)
5. **Регулярные backup** базы данных
6. **Мониторинг логов** системы
7. **Обновление** dependencies

---

## 📝 Configuration

### Критичные параметры в .env

```bash
# Database
MSSQL_SERVER=localhost
MSSQL_DATABASE=SIEM_DB
MSSQL_USER=siem_app
MSSQL_PASSWORD=YourStrongPassword

# или PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_DB=siem_db
POSTGRES_USER=siem_app
POSTGRES_PASSWORD=YourStrongPassword

# JWT Secret (ОБЯЗАТЕЛЬНО ИЗМЕНИТЬ!)
JWT_SECRET=your-very-secret-key-change-this-immediately

# AI Provider (выбрать один)
AI_PROVIDER=deepseek  # или yandex_gpt
DEEPSEEK_API_KEY=your-deepseek-api-key
# или
YANDEX_GPT_API_KEY=your-yandex-api-key
YANDEX_GPT_FOLDER_ID=your-folder-id

# Email notifications (опционально)
SMTP_SERVER=smtp.company.local
SMTP_PORT=587
SMTP_USER=siem@company.local
SMTP_PASSWORD=smtp_password

# Organization info (для CBR отчетов)
ORG_NAME=ООО "Название"
ORG_INN=1234567890
ORG_OGRN=1234567890123
```

---

## 🧪 Проверка работоспособности

### 1. Health Check

```bash
# Backend
curl http://localhost:8000/health

# Frontend
curl http://localhost:3000
```

### 2. API Test

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!"}'

# Get events (with token)
curl http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. WebSocket Test

```javascript
// В браузере console
const ws = new WebSocket('ws://localhost:8000/ws/events');
ws.onmessage = (event) => console.log(JSON.parse(event.data));
```

### 4. Agent Registration Test

```powershell
# Windows Agent
Get-Service SIEM-Agent
# Status должен быть Running

# Проверить логи
Get-EventLog -LogName Application -Source "SIEM Agent" -Newest 10
```

---

## 📊 Мониторинг

### Logs

**Backend:**
```bash
# Docker
docker-compose logs -f backend

# Manual
tail -f logs/siem_backend.log
```

**Frontend:**
```bash
# Development
# Логи в консоли браузера

# Production
# Логи nginx или web server
```

**Windows Agent:**
```powershell
# Event Viewer
Get-EventLog -LogName Application -Source "SIEM Agent" -Newest 50

# Или файл
type C:\ProgramData\SIEM\agent.log
```

**Network Monitor:**
```bash
# Journalctl
sudo journalctl -u siem-network-monitor -f

# Или файл
tail -f /var/log/siem/network_monitor.log
```

### Метрики

- **Events per second:** мониторить через Dashboard
- **Database size:** регулярно проверять рост
- **API response time:** через /metrics endpoint (если включено)
- **Agent status:** Dashboard -> Agents page

---

## 🔄 Backup & Restore

### Database Backup

**PostgreSQL:**
```bash
# Backup
pg_dump -U siem_app siem_db > backup_$(date +%Y%m%d).sql

# Restore
psql -U siem_app siem_db < backup_20251208.sql
```

**MS SQL Server:**
```sql
-- Backup
BACKUP DATABASE SIEM_DB
TO DISK = 'C:\Backups\SIEM_DB_20251208.bak'
WITH FORMAT;

-- Restore
RESTORE DATABASE SIEM_DB
FROM DISK = 'C:\Backups\SIEM_DB_20251208.bak'
WITH REPLACE;
```

### Configuration Backup

```bash
# Backup всех конфигураций
tar -czf siem_config_backup_$(date +%Y%m%d).tar.gz \
  backend/.env \
  frontend/.env.local \
  agent/config.yaml \
  network_monitor/config.yaml
```

---

## 🚨 Troubleshooting

### Backend не запускается

1. Проверить .env файл
2. Проверить подключение к БД
3. Проверить логи: `docker-compose logs backend`
4. Проверить порты: `netstat -an | grep 8000`

### Frontend не подключается к API

1. Проверить VITE_API_URL в .env.local
2. Проверить CORS настройки в backend
3. Проверить network tab в браузере
4. Проверить JWT token в localStorage

### Agent не отправляет события

1. Проверить config.yaml (server_url, agent_id)
2. Проверить network connectivity
3. Проверить логи агента
4. Проверить firewall rules
5. Проверить API key authentication

### Network Monitor не собирает данные

1. Проверить config.yaml (устройства, credentials)
2. Проверить SNMP connectivity: `snmpwalk -v2c -c public device_ip`
3. Проверить syslog port: `netstat -an | grep 514`
4. Проверить firewall rules
5. Проверить логи: `journalctl -u siem-network-monitor -f`

---

## 📈 Performance Tuning

### Database

**PostgreSQL:**
```sql
-- Создать индексы для частых запросов
CREATE INDEX idx_events_time ON security_events.events(event_time DESC);
CREATE INDEX idx_events_severity ON security_events.events(severity);

-- Настроить shared_buffers, work_mem в postgresql.conf
-- Рекомендуется: 25% RAM для shared_buffers
```

**MS SQL:**
```sql
-- Обновить статистику
UPDATE STATISTICS security_events.Events WITH FULLSCAN;

-- Rebuild индексов
ALTER INDEX ALL ON security_events.Events REBUILD;
```

### Backend

```bash
# Увеличить количество workers (в production)
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000

# Или использовать gunicorn
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend

```bash
# Production build с оптимизациями
npm run build

# Настроить nginx caching для static assets
# Включить gzip compression
# Использовать CDN для assets
```

---

## 📞 Support

При возникновении проблем:

1. Проверьте **логи** всех компонентов
2. Проверьте **документацию** в docs/
3. Проверьте **PROJECT_STATUS.md** для текущего статуса
4. Проверьте **Issues** в репозитории
5. Создайте **новый Issue** с деталями проблемы

---

## ✅ Checklist перед Production

- [ ] Сменены все дефолтные пароли
- [ ] Настроен уникальный JWT_SECRET
- [ ] Настроен HTTPS (SSL/TLS)
- [ ] Настроен firewall
- [ ] Настроены регулярные backups
- [ ] Проверена работоспособность всех компонентов
- [ ] Настроен мониторинг и алерты
- [ ] Документирована инфраструктура
- [ ] Обучены пользователи (admin, analyst, viewer)
- [ ] Настроены AI provider credentials
- [ ] Проверена интеграция с IPBan (если используется)
- [ ] Настроен Sysmon для FIM (если используется)
- [ ] Проверена отчетность для ЦБ РФ

---

**Версия:** 1.0.0 (Release)
**Дата:** 2025-12-08
**Статус:** Production Ready ✅

Успешного деплоя! 🚀
