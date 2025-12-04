# SIEM System - Installation Guide

Полная пошаговая инструкция по установке SIEM системы.

## 📋 Содержание

- [Требования](#требования)
- [Вариант 1: Standalone (всё на одной машине)](#вариант-1-standalone)
- [Вариант 2: Distributed (распределённая установка)](#вариант-2-distributed)
- [Настройка компонентов](#настройка-компонентов)
- [Проверка работы](#проверка-работы)
- [Troubleshooting](#troubleshooting)

---

## 🔧 Требования

### Минимальные требования (Standalone)

| Компонент | Требование |
|-----------|-----------|
| **CPU** | 4 ядра |
| **RAM** | 8 GB |
| **Disk** | 100 GB SSD |
| **OS** | Ubuntu 20.04+ / Debian 11+ / Windows Server 2019+ |
| **Network** | 1 Gbps |

### Рекомендуемые требования (Production)

| Компонент | Требование |
|-----------|-----------|
| **CPU** | 8+ ядер |
| **RAM** | 16+ GB |
| **Disk** | 500 GB+ SSD (RAID 10) |
| **OS** | Ubuntu 22.04 LTS / RHEL 8+ |
| **Network** | 10 Gbps |

### Программные требования

**Backend Server (Linux):**
- Python 3.11+
- PostgreSQL 15+ (рекомендуется) или MS SQL Server 2019+
- Node.js 18+ (для Frontend)
- Git

**Windows Agents:**
- Windows Server 2016+ / Windows 10+
- .NET Framework 4.7.2+ (обычно уже установлен)
- Go 1.21+ (для сборки агента из исходников)

**Network Monitor (Linux):**
- Python 3.11+
- SNMP tools
- Root права (для портов 162, 514, 2055)

---

## 🚀 Вариант 1: Standalone

Установка всех компонентов на одном сервере.

### Шаг 1: Подготовка системы

#### Ubuntu/Debian:
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка базовых пакетов
sudo apt install -y \
    build-essential \
    git \
    curl \
    wget \
    vim \
    htop \
    net-tools

# Установка Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# Установка Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Проверка версий
python3.11 --version
node --version
npm --version
```

### Шаг 2: Установка PostgreSQL + TimescaleDB

```bash
# Добавление репозитория PostgreSQL
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Добавление репозитория TimescaleDB
sudo sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main' > /etc/apt/sources.list.d/timescaledb.list"
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -

# Установка
sudo apt update
sudo apt install -y postgresql-15 postgresql-15-timescaledb-2.12

# Настройка TimescaleDB
sudo timescaledb-tune --quiet --yes

# Перезапуск PostgreSQL
sudo systemctl restart postgresql

# Проверка статуса
sudo systemctl status postgresql
```

### Шаг 3: Создание базы данных

```bash
# Вход в PostgreSQL
sudo -u postgres psql

# В psql консоли:
CREATE DATABASE siem_db;
CREATE USER siem_app WITH PASSWORD 'YourStrongPassword123!';
GRANT ALL PRIVILEGES ON DATABASE siem_db TO siem_app;

# Включение TimescaleDB extension
\c siem_db
CREATE EXTENSION IF NOT EXISTS timescaledb;

# Проверка
\dx

# Выход
\q
```

### Шаг 4: Клонирование репозитория

```bash
# Создание директории
cd /opt
sudo git clone https://github.com/your-org/siem-system.git siem
cd /opt/siem

# Установка прав
sudo chown -R $USER:$USER /opt/siem
```

### Шаг 5: Автоматическая установка

```bash
cd /opt/siem

# Запуск инсталлятора (с правами root)
sudo ./install.sh

# Следуйте инструкциям:
# 1. Укажите параметры PostgreSQL
# 2. Установите Backend
# 3. Установите Frontend
# 4. Установите Network Monitor (опционально)
```

Инсталлятор автоматически:
- ✅ Проверит все зависимости
- ✅ Создаст .env файл
- ✅ Установит схему БД PostgreSQL
- ✅ Установит Python зависимости (venv)
- ✅ Установит npm зависимости
- ✅ Создаст helper скрипты

### Шаг 6: Настройка .env

```bash
cd /opt/siem
nano .env
```

Минимальная конфигурация:
```bash
# Database
DATABASE_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=siem_db
POSTGRES_USER=siem_app
POSTGRES_PASSWORD=YourStrongPassword123!

# AI Provider (выберите один)
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_api_key
# Или
# AI_PROVIDER=yandex
# YANDEX_GPT_API_KEY=your_yandex_key
# YANDEX_GPT_FOLDER_ID=your_folder_id

# Security
JWT_SECRET_KEY=generate_random_32_char_string_here
JWT_EXPIRATION_MINUTES=480

# Organization (для CBR отчётов)
ORG_NAME=ООО "Ваша Компания"
ORG_INN=1234567890
ORG_OGRN=1234567890123
```

Генерация JWT_SECRET_KEY:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Шаг 7: Запуск сервисов

#### Backend:
```bash
cd /opt/siem
./start_backend.sh
```

Или как systemd service:
```bash
sudo systemctl enable siem-backend
sudo systemctl start siem-backend
sudo systemctl status siem-backend
```

#### Frontend:
```bash
cd /opt/siem
./start_frontend.sh
```

#### Network Monitor (опционально):
```bash
cd /opt/siem/network_monitor

# Настроить config.yaml
cp config.yaml.example config.yaml
nano config.yaml

# Запустить
sudo ./install.sh  # Установит как systemd service
sudo systemctl start siem-network-monitor
```

### Шаг 8: Проверка установки

```bash
# Проверка портов
sudo netstat -tulpn | grep -E '8000|5173|514|162|2055'

# Backend API
curl http://localhost:8000/health
# Должен вернуть: {"status":"ok"}

# Frontend
curl http://localhost:5173
# Должен вернуть HTML страницу

# Логи
sudo journalctl -u siem-backend -f
sudo journalctl -u siem-network-monitor -f
```

### Шаг 9: Первый вход

1. Откройте браузер: `http://your-server-ip:5173`
2. Войдите:
   - Username: `admin`
   - Password: `Admin123!`
3. **ОБЯЗАТЕЛЬНО смените пароль!**

---

## 🌐 Вариант 2: Distributed

Распределённая установка для production.

### Архитектура

```
┌─────────────────┐
│   Database      │  PostgreSQL 15 + TimescaleDB
│   Server        │  IP: 10.0.1.10
└─────────────────┘
         ▲
         │
┌─────────────────┐
│   Backend       │  FastAPI + WebSocket
│   Server        │  IP: 10.0.1.20
└─────────────────┘
         ▲
         │
┌─────────────────┐
│   Frontend      │  Nginx + React
│   Server        │  IP: 10.0.1.30
└─────────────────┘

┌─────────────────┐
│   Network       │  SNMP, Syslog, NetFlow
│   Monitor       │  IP: 10.0.1.40
└─────────────────┘

┌─────────────────┐
│   Windows       │  Event collection
│   Agents        │  IP: 10.0.2.x
└─────────────────┘
```

### Сервер 1: Database (10.0.1.10)

```bash
# Установка PostgreSQL + TimescaleDB (как выше)

# Настройка для удалённых подключений
sudo nano /etc/postgresql/15/main/postgresql.conf
# Изменить:
listen_addresses = '*'

sudo nano /etc/postgresql/15/main/pg_hba.conf
# Добавить:
host    siem_db    siem_app    10.0.1.0/24    scram-sha-256

# Перезапуск
sudo systemctl restart postgresql

# Firewall
sudo ufw allow from 10.0.1.0/24 to any port 5432
```

### Сервер 2: Backend (10.0.1.20)

```bash
# Клонирование и установка
cd /opt
sudo git clone https://github.com/your-org/siem-system.git siem
cd /opt/siem

# Установка только backend
sudo ./install.sh --skip-db --skip-frontend

# Настройка .env
nano .env
# Изменить:
POSTGRES_HOST=10.0.1.10
POSTGRES_PORT=5432
```

### Сервер 3: Frontend (10.0.1.30)

```bash
# Установка Nginx
sudo apt install -y nginx

# Сборка frontend
cd /opt/siem/frontend
npm run build

# Nginx конфигурация
sudo nano /etc/nginx/sites-available/siem

# Содержимое:
server {
    listen 80;
    server_name your-domain.com;

    root /opt/siem/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://10.0.1.20:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /ws {
        proxy_pass http://10.0.1.20:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}

# Активация
sudo ln -s /etc/nginx/sites-available/siem /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Сервер 4: Network Monitor (10.0.1.40)

```bash
# Установка
cd /opt/siem/network_monitor
sudo ./install.sh

# Настройка
sudo nano config.yaml
# Изменить:
siem:
  url: "http://10.0.1.20:8000"
  api_key: "your_api_key"
```

### Windows Agents

На каждом Windows хосте:

```powershell
# Скачать агент
Invoke-WebRequest -Uri "http://10.0.1.20:8000/download/agent" -OutFile "siem-agent.exe"

# Создать конфигурацию
mkdir C:\ProgramData\SIEM
notepad C:\ProgramData\SIEM\agent.yaml

# agent.yaml:
server:
  url: "http://10.0.1.20:8000"
  api_key: "your_api_key"
  timeout: 30
  verify_ssl: true

# Установить как службу
.\siem-agent.exe install
Start-Service SIEM-Agent
```

---

## ⚙️ Настройка компонентов

### Backend настройки (.env)

```bash
# Performance
WORKER_COUNT=4
DB_POOL_SIZE=20
DB_POOL_MAX_OVERFLOW=10

# WebSocket
WEBSOCKET_PING_INTERVAL=30
WEBSOCKET_TIMEOUT=300

# AI Analysis
AI_BATCH_SIZE=10
AI_ANALYSIS_INTERVAL=60
AI_SCORE_THRESHOLD=70
AI_AUTO_ALERT_THRESHOLD=85

# Event Retention (days)
EVENT_RETENTION_DAYS=1825  # 5 years for CBR compliance

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/siem/backend.log
```

### Network Monitor (config.yaml)

```yaml
siem:
  url: "http://localhost:8000"
  api_key: "your_api_key"
  timeout: 30
  batch_size: 100
  retry_attempts: 3

snmp:
  enabled: true
  community: "public"
  version: "2c"
  timeout: 5
  retries: 2
  interval: 300  # 5 minutes

syslog:
  enabled: true
  udp_port: 514
  tcp_port: 514
  listen_address: "0.0.0.0"

netflow:
  enabled: true
  port: 2055
  listen_address: "0.0.0.0"

snmp_traps:
  enabled: true
  port: 162
  listen_address: "0.0.0.0"

device_discovery:
  enabled: true
  interval: 3600  # 1 hour
  networks:
    - "192.168.1.0/24"
    - "10.0.0.0/16"

devices:
  - name: "Switch-Core-01"
    ip: "192.168.1.1"
    type: "switch"
    profile: "cisco"

  - name: "Printer-Office-01"
    ip: "192.168.1.10"
    type: "printer"
    profile: "hp"
```

---

## ✅ Проверка работы

### 1. Проверка Backend API

```bash
# Health check
curl http://localhost:8000/health

# API Documentation
curl http://localhost:8000/docs

# Login test
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!"}'
```

### 2. Проверка Database

```bash
sudo -u postgres psql -d siem_db

SELECT count(*) FROM security_events.events;
SELECT count(*) FROM security_events.alerts;
SELECT count(*) FROM assets.agents;

\q
```

### 3. Проверка WebSocket

```javascript
// В браузере console (F12)
const ws = new WebSocket('ws://localhost:8000/ws/dashboard?token=YOUR_JWT_TOKEN');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

### 4. Проверка Network Monitor

```bash
# Логи
sudo journalctl -u siem-network-monitor -f

# Статистика
sudo systemctl status siem-network-monitor

# Тест SNMP
snmpwalk -v2c -c public 192.168.1.1 system
```

### 5. Проверка Windows Agent

```powershell
# Статус службы
Get-Service SIEM-Agent

# Логи в Event Viewer
Get-EventLog -LogName Application -Source "SIEM Agent" -Newest 10

# Проверка на сервере
curl http://localhost:8000/api/v1/agents
```

---

## 🔧 Troubleshooting

### Backend не запускается

**Проблема:** `Connection refused` к БД

**Решение:**
```bash
# Проверить PostgreSQL
sudo systemctl status postgresql

# Проверить подключение
psql -h localhost -U siem_app -d siem_db

# Проверить .env
cat .env | grep POSTGRES
```

**Проблема:** `ImportError: No module named 'fastapi'`

**Решение:**
```bash
cd /opt/siem/backend
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend не открывается

**Проблема:** `Cannot GET /`

**Решение:**
```bash
# Проверить процесс
ps aux | grep "npm run dev"

# Перезапустить
cd /opt/siem
./stop_all.sh
./start_frontend.sh
```

### Network Monitor не получает SNMP

**Проблема:** Timeout при SNMP запросах

**Решение:**
```bash
# Проверить firewall
sudo ufw status

# Разрешить SNMP
sudo ufw allow from 192.168.1.0/24 to any port 161

# Проверить community string
snmpwalk -v2c -c public 192.168.1.1 sysDescr
```

**Проблема:** `Permission denied` для портов 162, 514

**Решение:**
```bash
# Network Monitor нужен root для привилегированных портов
sudo systemctl start siem-network-monitor

# Или использовать setcap (не рекомендуется)
sudo setcap 'cap_net_bind_service=+ep' /opt/siem/network_monitor/venv/bin/python3
```

### Windows Agent не отправляет события

**Проблема:** Служба запущена, но события не приходят

**Решение:**
```powershell
# Проверить конфигурацию
type C:\ProgramData\SIEM\agent.yaml

# Проверить логи
Get-EventLog -LogName Application -Source "SIEM Agent" -Newest 50

# Проверить сетевое подключение
Test-NetConnection -ComputerName backend-server -Port 8000

# Перезапустить службу
Restart-Service SIEM-Agent
```

### High CPU/Memory usage

**Проблема:** Backend потребляет много ресурсов

**Решение:**
```bash
# Оптимизировать .env
nano /opt/siem/.env

# Уменьшить worker count
WORKER_COUNT=2

# Уменьшить pool size
DB_POOL_SIZE=10

# Увеличить AI interval
AI_ANALYSIS_INTERVAL=300

# Перезапустить
sudo systemctl restart siem-backend
```

---

## 📊 Monitoring

### System Monitoring

```bash
# CPU/RAM/Disk
htop
df -h

# Network
sudo iftop
sudo netstat -tulpn

# PostgreSQL
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"

# Logs
sudo journalctl -u siem-backend --since "1 hour ago"
```

### Application Metrics

```bash
# Backend metrics (если настроен Prometheus)
curl http://localhost:8000/metrics

# Events per second
sudo -u postgres psql -d siem_db -c "
SELECT
    COUNT(*) / 60 as events_per_second
FROM security_events.events
WHERE EventTime > NOW() - INTERVAL '1 minute';"
```

---

## 🔒 Security Checklist

После установки:

- [ ] Сменить все default пароли (admin, analyst, viewer)
- [ ] Сгенерировать уникальный JWT_SECRET_KEY
- [ ] Настроить SSL/TLS (Let's Encrypt)
- [ ] Настроить firewall (ufw/iptables)
- [ ] Включить audit logging в PostgreSQL
- [ ] Настроить резервное копирование БД
- [ ] Ограничить доступ к API (API keys, rate limiting)
- [ ] Настроить мониторинг (Prometheus + Grafana)
- [ ] Документировать изменения в конфигурации

---

**Версия:** 1.0
**Дата:** 2025-12-03
**Поддержка:** [GitHub Issues](https://github.com/your-org/siem-system/issues)
