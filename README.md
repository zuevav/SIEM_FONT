# SIEM System для Windows-инфраструктуры

Полнофункциональная SIEM-система (Security Information and Event Management) для мониторинга безопасности Windows-инфраструктуры с соответствием требованиям ЦБ РФ.

## 🎯 Назначение

Система предназначена для:
- Сбора и анализа событий безопасности из Windows-инфраструктуры
- Детекции угроз и инцидентов информационной безопасности
- AI-анализа событий через Yandex GPT
- Инвентаризации активов и программного обеспечения
- Соответствия требованиям ЦБ РФ (683-П, 716-П, 747-П, ГОСТ Р 57580)
- Оперативного предоставления информации регулятору

## 🏗️ Архитектура

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Windows Agent  │────▶│                  │────▶│   MS SQL /      │
│  (Go)           │     │                  │     │   PostgreSQL    │
└─────────────────┘     │   Backend API    │     │   (Database)    │
                        │   (FastAPI)      │     └─────────────────┘
┌─────────────────┐     │                  │              ▲
│ Network Monitor │────▶│                  │              │
│ (Python)        │     └──────────────────┘              │
│ - SNMP          │            │                          │
│ - Syslog        │            ▼                          │
│ - NetFlow       │     ┌──────────────────┐              │
│ - SNMP Traps    │     │  DeepSeek /      │              │
└─────────────────┘     │  Yandex GPT      │              │
                        │  (AI Analysis)   │              │
                        └──────────────────┘              │
                               │                          │
                               ▼                          │
┌─────────────────┐     ┌──────────────────┐             │
│  Web Frontend   │────▶│   WebSocket      │─────────────┘
│  (React + TS)   │     │   (Real-time)    │
└─────────────────┘     └──────────────────┘
```

### Компоненты

| Компонент | Технологии | Назначение |
|-----------|-----------|-----------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy | REST API, обработка событий, AI-анализ |
| **Database** | PostgreSQL 15+ / MS SQL Server 2019+ | Хранение событий, алертов, инцидентов |
| **Frontend** | React 18, TypeScript, Ant Design | Веб-интерфейс, дашборды, отчёты |
| **Windows Agent** | Go 1.21+ | Сбор событий Windows, инвентаризация |
| **Network Monitor** | Python 3.11+, asyncio | SNMP, Syslog, NetFlow, Device Discovery |
| **AI** | DeepSeek / Yandex GPT API | Классификация угроз, корреляция |

## ✨ Основные возможности

### 🔍 Сбор событий
- Windows Event Log (Security, System, Application)
- Sysmon события (процессы, сеть, файлы, реестр)
- PowerShell логи
- Windows Defender события
- IPBan события (блокировки IP, brute-force атаки)
- Сетевые подключения
- Запущенные процессы

### 📊 Инвентаризация
- Список установленного ПО на всех хостах
- Информация о системе (ОС, железо, домен)
- Службы Windows
- Запланированные задачи
- Локальные пользователи и группы
- Автоматическая классификация ПО

### 🌐 Мониторинг сетевого оборудования
- **SNMP мониторинг** (принтеры, коммутаторы, роутеры, МСЭ, UPS)
  - Статус устройств, CPU/Memory usage
  - Тонер принтеров, заряд батареи UPS
  - Состояние портов и интерфейсов
- **Syslog receiver** (UDP/TCP порт 514)
  - RFC 3164/5424 парсинг
  - Vendor-specific форматы (Cisco, Fortinet, Juniper)
- **NetFlow/IPFIX collector**
  - NetFlow v5, v9, IPFIX (v10)
  - Анализ сетевых потоков
  - Детекция подозрительного трафика и port scanning
- **SNMP Traps receiver** (порт 162)
  - Асинхронные уведомления от устройств
  - coldStart, linkDown/Up, authenticationFailure
- **Device Discovery**
  - Автоматическое обнаружение устройств в сети
  - ICMP ping sweep + SNMP probing
  - Определение типа устройства

### 🤖 AI-анализ (DeepSeek / Yandex GPT)
- Классификация событий по уровню угрозы
- Маппинг на MITRE ATT&CK
- Корреляция событий в инциденты
- Генерация человекочитаемых описаний
- Рекомендации по реагированию

### 🚨 Детекция угроз
- **19 правил детекции** (базовые + IPBan + FIM)
  - Brute-force атаки и Pass-the-Hash
  - Подозрительные PowerShell команды
  - Mimikatz и credential theft
  - Ransomware поведение
  - IPBan: массовые блокировки IP
  - FIM: изменения файлов и реестра
- Поддержка Sigma rules
- Threshold rules (N событий за M минут)
- Correlation rules (цепочки событий)
- Whitelist/исключения

### 🔒 File Integrity Monitoring (FIM)
- **Мониторинг файловой системы** через Sysmon
  - Создание/удаление файлов в системных папках
  - Хеширование файлов (SHA256, MD5)
  - Отслеживание исполняемых файлов в Temp
  - Мониторинг hosts файла (DNS hijacking)
- **Мониторинг реестра Windows**
  - Изменения ключей автозапуска (Run, RunOnce)
  - Модификация критичных ключей системы
  - Отслеживание создания задач планировщика
- **UI для просмотра FIM событий**
  - Фильтрация по типу, пути, процессу
  - Просмотр хешей и деталей изменений
  - Статистика по файлам и процессам

### 🛡️ IPBan Integration
- **Мониторинг IPBan событий** (C:\IPBan\)
  - Event ID 1: IP заблокирован
  - Event ID 2: IP разблокирован
  - Event ID 3: Неудачные попытки входа
  - Event ID 4-5: Изменения конфигурации и статус сервиса
- **Автоматическая детекция атак**
  - Массовые блокировки IP (>10 за 5 минут)
  - Повторные попытки входа с одного IP
  - Корреляция с threat intelligence
- **SOAR автоматизация**
  - Проверка IP через threat intelligence feeds
  - Автоматические уведомления и тикеты
  - Email alerts на критичные события

### 🤖 SOAR (Security Orchestration, Automation and Response)
- **8 автоматических Playbooks**
  - Auto-Block Malicious IP
  - Isolate Infected Host
  - Kill Suspicious Process
  - Quarantine Malware
  - Disable Compromised Account
  - IPBan Mass Attack Response
  - FIM Critical File Change Response
- **9 типов Actions**
  - Block IP, Isolate Host, Kill Process
  - Send Email, Create Ticket, Slack Notification
  - Quarantine File, Disable User Account
  - Check Threat Intelligence
- **Автозапуск на основе severity и MITRE ATT&CK**
- **Approval workflow** для критичных действий
- **UI для управления** playbooks и executions

### 📈 Дашборды и отчёты
- Главный дашборд с KPI безопасности
- Timeline событий с фильтрацией
- Топ хостов и пользователей по алертам
- Карта угроз (MITRE ATT&CK heatmap)
- Drill-down в события и инциденты
- **FreeScout интеграция** - автоматические тикеты на алерты
- **In-system документация** - просмотр руководств из UI

### 📋 Соответствие ЦБ РФ
- Хранение событий минимум 5 лет (683-П)
- Защита от изменения/удаления (ГОСТ Р 57580)
- Классификация по операционным рискам (716-П)
- Экспорт в форматах ФинЦЕРТ и 0403203 (747-П)
- Audit log всех действий

## 🚀 Быстрый старт

### ⚡ Click-to-Run Установка (Рекомендуется)

**Автоматическая установка за 5 минут!**

#### Linux/Unix (Ubuntu, Debian, CentOS, RHEL, Fedora)

```bash
# Одна команда для полной установки
curl -sSL https://raw.githubusercontent.com/zuevav/SIEM_FONT/main/install.sh | sudo bash
```

Или с wget:
```bash
wget -qO- https://raw.githubusercontent.com/zuevav/SIEM_FONT/main/install.sh | sudo bash
```

#### Windows (PowerShell as Administrator)

```powershell
# Скачать установщик
Invoke-WebRequest -Uri https://raw.githubusercontent.com/zuevav/SIEM_FONT/main/install.ps1 -OutFile install.ps1

# Запустить установку
PowerShell -ExecutionPolicy Bypass -File install.ps1
```

**Что делает установщик:**
- ✅ Проверяет зависимости (Docker, Git)
- ✅ Скачивает последнюю версию с GitHub
- ✅ Интерактивная настройка (admin, порты, AI)
- ✅ Генерирует безопасные пароли
- ✅ Запускает все сервисы
- ✅ Создаёт systemd service (Linux) или scheduled task (Windows)
- ✅ Проверяет работоспособность

**После установки:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Логин: `admin` / `admin123` (измените после входа!)

📖 **Подробная документация**: [docs/QUICK_INSTALL.md](docs/QUICK_INSTALL.md)

---

### 📦 Ручная установка (Docker Compose)

#### Предварительные требования

- **MS SQL Server 2019+** (Standard или Enterprise)
- **Docker + Docker Compose** (для backend и frontend)
- **Python 3.11+** (для разработки backend)
- **Node.js 18+** (для разработки frontend)
- **Go 1.21+** (для сборки агента)

### Шаг 1: Установка базы данных

```powershell
# 1. Отредактируйте database/schema.sql - укажите пути к файлам
# 2. Выполните скрипты по порядку:

sqlcmd -S localhost -i database/schema.sql
sqlcmd -S localhost -i database/procedures.sql
sqlcmd -S localhost -i database/triggers.sql
sqlcmd -S localhost -i database/seed.sql
sqlcmd -S localhost -i database/jobs.sql

# 3. Создайте пользователя для приложения
sqlcmd -S localhost -Q "CREATE LOGIN siem_app WITH PASSWORD = 'YourStrongPassword'"
sqlcmd -S localhost -d SIEM_DB -Q "CREATE USER siem_app FOR LOGIN siem_app; GRANT EXECUTE TO siem_app;"
```

Подробнее: [database/README.md](database/README.md)

### Шаг 2: Настройка Backend

```bash
cd backend

# Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установите зависимости
pip install -r requirements.txt

# Создайте .env файл
cp ../.env.example .env

# Отредактируйте .env - укажите:
# - Параметры подключения к MS SQL
# - Yandex GPT API ключи
# - SMTP настройки

# Запустите сервер
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API будет доступно: `http://localhost:8000`
Документация: `http://localhost:8000/docs`

### Шаг 3: Запуск Frontend

```bash
cd frontend

# Установите зависимости
npm install

# Создайте .env.local
cp .env.example .env.local

# Укажите URL backend API
echo "VITE_API_URL=http://localhost:8000" > .env.local

# Запустите dev сервер
npm run dev
```

Интерфейс будет доступен: `http://localhost:5173`

### Шаг 4: Установка агента на Windows

```powershell
# Скачайте собранный агент или соберите из исходников:
cd agent
go build -o siem-agent.exe cmd/agent/main.go

# Создайте конфигурацию
cp configs/agent.yaml.example C:\ProgramData\SIEM\agent.yaml

# Отредактируйте agent.yaml:
# - server_url: http://your-siem-server:8000
# - agent_id: уникальный GUID

# Установите как службу
.\siem-agent.exe install

# Запустите службу
Start-Service SIEM-Agent
```

### Шаг 5: Установка Network Monitor (Linux)

```bash
cd network_monitor

# Создайте виртуальное окружение
python3.11 -m venv venv
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt

# Создайте конфигурацию
cp config.yaml.example config.yaml

# Отредактируйте config.yaml:
# - SIEM server URL и API key
# - Список SNMP устройств
# - Настройки syslog и NetFlow

# Установите как systemd service
sudo ./install.sh

# Запустите службу
sudo systemctl start siem-network-monitor
```

Подробнее: [network_monitor/README.md](network_monitor/README.md)

### Шаг 6: Первый вход

1. Откройте `http://localhost:5173`
2. Войдите с учётными данными:
   - **Username:** `admin`
   - **Password:** `Admin123!`
3. **ВАЖНО:** Смените пароль при первом входе!

## 📁 Структура проекта

```
siem-system/
├── database/              # MS SQL схема и скрипты
│   ├── schema.sql        # Основная схема БД
│   ├── procedures.sql    # Хранимые процедуры
│   ├── triggers.sql      # Триггеры защиты
│   ├── seed.sql          # Начальные данные
│   ├── jobs.sql          # SQL Agent Jobs
│   └── README.md         # Документация БД
│
├── backend/              # FastAPI приложение
│   ├── app/
│   │   ├── main.py           # Entry point
│   │   ├── config.py         # Конфигурация
│   │   ├── database.py       # Подключение к MS SQL
│   │   ├── api/              # API endpoints
│   │   │   └── v1/           # API v1
│   │   ├── core/             # Безопасность, RBAC
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   └── services/         # Бизнес-логика
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/             # React приложение
│   ├── src/
│   │   ├── api/              # API клиент
│   │   ├── components/       # React компоненты
│   │   ├── pages/            # Страницы
│   │   ├── hooks/            # Custom hooks
│   │   ├── store/            # State management
│   │   └── types/            # TypeScript типы
│   ├── package.json
│   └── Dockerfile
│
├── agent/                # Windows агент (Go)
│   ├── cmd/agent/        # Entry point
│   ├── internal/
│   │   ├── collector/        # Сборщики событий
│   │   ├── sender/           # Отправка на сервер
│   │   ├── service/          # Windows Service
│   │   └── config/           # Конфигурация
│   ├── go.mod
│   └── build/                # Установщики
│
├── network_monitor/      # Network Device Monitor (Python)
│   ├── main.py               # Entry point
│   ├── config.py             # Configuration
│   ├── snmp_collector.py     # SNMP polling
│   ├── syslog_receiver.py    # Syslog receiver
│   ├── netflow_collector.py  # NetFlow/IPFIX
│   ├── snmp_traps.py         # SNMP Traps
│   ├── device_discovery.py   # Device discovery
│   ├── device_profiles.py    # Device profiles
│   ├── api_client.py         # SIEM API client
│   ├── requirements.txt      # Dependencies
│   ├── install.sh            # Installer
│   └── README.md             # Documentation
│
├── deploy/               # Деплой скрипты
│   ├── ansible/              # Ansible playbooks
│   └── scripts/              # Скрипты установки
│
├── docs/                 # Документация
│   ├── architecture.md       # Архитектура системы
│   ├── api-reference.md      # API документация
│   ├── cbr-compliance.md     # Соответствие ЦБ РФ
│   └── user-guide.md         # Руководство пользователя
│
├── rules/                # Правила детекции
│   ├── sigma/                # Sigma rules
│   └── custom/               # Собственные правила
│
├── docker-compose.yml    # Docker Compose конфиг
├── .env.example          # Пример переменных окружения
└── README.md             # Этот файл
```

## 🔒 Безопасность

### Аутентификация и авторизация
- JWT токены с настраиваемым временем жизни
- Интеграция с Active Directory (LDAP)
- RBAC: admin, analyst, viewer

### Защита данных
- События защищены от изменения триггерами (требование ЦБ)
- Контрольные суммы SHA256 для верификации
- Audit log всех действий пользователей
- Шифрование паролей (bcrypt)

### Сетевая безопасность
- HTTPS для всех соединений
- Rate limiting на API
- CORS настройка

## 📊 Производительность

### Метрики
- **Обработка:** 10,000+ событий/сек
- **Хранение:** Миллионы событий в день
- **Поиск:** <1 сек для запросов за 24ч
- **Дашборд:** Real-time обновления через WebSocket

### Оптимизации
- Columnstore индексы для аналитики
- Партиционирование по месяцам
- Batch-вставка событий
- Сжатие данных (PAGE/COLUMNSTORE)
- Кэширование в Redis (опционально)

## 📝 Соответствие требованиям ЦБ РФ

| Требование | Реализация |
|------------|-----------|
| **683-П** | Хранение событий 5 лет, защита от изменения, контроль доступа |
| **716-П** | Классификация по операционным рискам, оценка ущерба |
| **747-П** | Экспорт в формате ФинЦЕРТ, форма 0403203 |
| **ГОСТ Р 57580** | Audit log, RBAC, контроль целостности |

Подробнее: [docs/cbr-compliance.md](docs/cbr-compliance.md)

## 🔧 Настройка

### Основные параметры (.env)

```bash
# База данных
MSSQL_SERVER=localhost
MSSQL_DATABASE=SIEM_DB
MSSQL_USER=siem_app
MSSQL_PASSWORD=YourStrongPassword

# Yandex GPT
YANDEX_GPT_API_KEY=your_api_key
YANDEX_GPT_FOLDER_ID=your_folder_id
YANDEX_GPT_MODEL=yandexgpt-lite

# Email уведомления
SMTP_SERVER=smtp.company.local
SMTP_PORT=587
SMTP_USER=siem@company.local
SMTP_PASSWORD=smtp_password

# Безопасность
JWT_SECRET=your_very_secret_key_change_me
JWT_EXPIRATION_MINUTES=480

# Данные организации (для отчётов ЦБ)
ORG_NAME=ООО "Название"
ORG_INN=1234567890
ORG_OGRN=1234567890123
```

### Yandex GPT API

Для получения API ключа:
1. Создайте аккаунт в [Yandex Cloud](https://cloud.yandex.ru/)
2. Создайте Folder
3. Получите API ключ: https://cloud.yandex.ru/docs/iam/operations/api-key/create
4. Укажите в `.env`: `YANDEX_GPT_API_KEY` и `YANDEX_GPT_FOLDER_ID`

Стоимость: ~1₽ за 1000 токенов (yandexgpt-lite)

## 🐳 Docker Compose

Для запуска всего стека (кроме MS SQL):

```bash
# Создайте .env из примера
cp .env.example .env

# Отредактируйте .env

# Запустите контейнеры
docker-compose up -d

# Проверьте статус
docker-compose ps

# Логи
docker-compose logs -f backend
```

Сервисы:
- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- Redis (кэш): `localhost:6379`

## 📚 Документация

### Руководства по установке и настройке
- [📦 Быстрая установка (QUICK_INSTALL.md)](docs/QUICK_INSTALL.md) - Click-to-run установка за 5 минут
- [⚙️ Настройка Phase 1 (PHASE1_SETUP.md)](docs/PHASE1_SETUP.md) - Детальная настройка всех компонентов
- [🔧 Docker Guide (DOCKER_GUIDE.md)](DOCKER_GUIDE.md) - Развёртывание через Docker Compose
- [💿 Installation Guide (INSTALLATION_GUIDE.md)](INSTALLATION_GUIDE.md) - Ручная установка компонентов

### Интеграции и специализированная настройка
- [📧 FreeScout Integration (FREESCOUT_INTEGRATION.md)](docs/FREESCOUT_INTEGRATION.md) - Интеграция с helpdesk системой
- [🤖 AI Provider Setup (AI_PROVIDER_SETUP.md)](AI_PROVIDER_SETUP.md) - Настройка Yandex GPT / DeepSeek
- [🔄 Database Migration (DATABASE_MIGRATION.md)](DATABASE_MIGRATION.md) - Миграция с MS SQL на PostgreSQL
- [💾 База данных (database/README.md)](database/README.md) - Схема и структура БД
- [🌐 Network Monitor (network_monitor/README.md)](network_monitor/README.md) - SNMP, Syslog, NetFlow

### API и разработка
- [🔌 WebSocket Guide (WEBSOCKET_GUIDE.md)](WEBSOCKET_GUIDE.md) - Real-time обновления
- [📊 API Docs](http://localhost:8000/docs) - Swagger/OpenAPI документация (после запуска)

### Статус проекта
- [📈 Project Status (PROJECT_STATUS.md)](PROJECT_STATUS.md) - Детальный статус всех компонентов
- [🎯 Market Analysis (MARKET_ANALYSIS.md)](docs/MARKET_ANALYSIS.md) - Анализ рынка и feature comparison

## 🧪 Тестирование

```bash
# Backend тесты
cd backend
pytest tests/ -v

# Frontend тесты
cd frontend
npm run test

# E2E тесты
npm run test:e2e
```

## 🤝 Разработка

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Инструменты разработки

# Запуск с hot-reload
uvicorn app.main:app --reload

# Форматирование кода
black app/
isort app/

# Линтинг
pylint app/
mypy app/
```

### Frontend

```bash
cd frontend
npm install
npm run dev  # Dev сервер с hot-reload

# Линтинг и форматирование
npm run lint
npm run format

# Сборка production
npm run build
```

### Агент

```bash
cd agent
go mod download

# Сборка
go build -o siem-agent.exe cmd/agent/main.go

# Тесты
go test ./...

# Cross-compile для Windows (из Linux)
GOOS=windows GOARCH=amd64 go build -o siem-agent.exe cmd/agent/main.go
```

## 📦 Установка в production

Для production установки рекомендуется:
1. Использовать [Docker Compose](DOCKER_GUIDE.md) для контейнеризации
2. Настроить PostgreSQL + TimescaleDB (см. [DATABASE_MIGRATION.md](DATABASE_MIGRATION.md))
3. Настроить HTTPS через nginx reverse proxy
4. Использовать systemd для автозапуска сервисов
5. Настроить регулярные бэкапы БД

См. также:
- [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) - детальное руководство
- [QUICK_INSTALL.md](docs/QUICK_INSTALL.md) - автоматическая установка
- [PHASE1_SETUP.md](docs/PHASE1_SETUP.md) - настройка всех компонентов

## 💾 Выбор базы данных

Система поддерживает две СУБД:

### PostgreSQL 15+ (Рекомендуется)
**Преимущества:**
- ✅ Бесплатный и Open Source
- ✅ Отличная производительность для time-series данных
- ✅ TimescaleDB extension для автоматического partitioning
- ✅ JSONB для гибкого хранения событий
- ✅ Full-Text Search встроенный
- ✅ Простая установка и интеграция с Linux
- ✅ Высокое сжатие данных (10-100x)

**Рекомендуется для:**
- Новых установок
- Linux серверов
- Бюджетных проектов
- Высоконагруженных SIEM (>10,000 events/sec)

### MS SQL Server 2019+
**Преимущества:**
- ✅ Знакомая технология для Windows-окружений
- ✅ Columnstore indexes для аналитики
- ✅ SQL Agent Jobs для автоматизации
- ✅ Enterprise features

**Ограничения:**
- ❌ Дорогая лицензия (Standard/Enterprise)
- ❌ Express edition: лимит 10 GB БД
- ❌ Больший footprint на Linux

Подробнее: [DATABASE_MIGRATION.md](DATABASE_MIGRATION.md)

## ⚠️ Известные ограничения

- **Database:** PostgreSQL или MS SQL Server требуется отдельная установка
- **AI Provider:** DeepSeek (бесплатный) или Yandex GPT (платный)
- **Windows Agent:** Поддержка только Windows (Server 2016+, Windows 10+)
- **Network Monitor:** Поддержка только Linux
- **Performance:** Для >1000 хостов рекомендуется кластер БД

## 🔮 Roadmap

### ✅ Реализовано (Phase 1 & 2)
- [x] Windows Agent для сбора событий
- [x] Network Monitor (SNMP, Syslog, NetFlow)
- [x] SOAR Playbooks (8 playbooks, 9 actions)
- [x] File Integrity Monitoring (Sysmon FIM)
- [x] IPBan Integration
- [x] FreeScout Helpdesk Integration
- [x] AI Analysis (Yandex GPT / DeepSeek)
- [x] Docker Compose для быстрого развёртывания
- [x] PostgreSQL + TimescaleDB support
- [x] In-system documentation viewer

### 🚧 В разработке (Phase 3)
- [ ] Threat Intelligence feeds integration (MISP, AlienVault OTX, AbuseIPDB)
- [ ] Advanced Search & Saved Searches UI
- [ ] Scheduled Reports (ежедневные/еженедельные)
- [ ] User Behavior Analytics (UEBA)
- [ ] Graph visualization для корреляции событий

### 🔮 Планируется (Phase 4+)
- [ ] Поддержка Linux-агентов для сбора событий
- [ ] Интеграция с внешними SIEM (Splunk, ELK) через syslog/API
- [ ] Мобильное приложение для мониторинга
- [ ] Кластеризация backend для High Availability
- [ ] Kubernetes Helm charts
- [ ] Compliance reporting automation (ЦБ РФ forms)

## 📄 Лицензия

Проприетарное ПО. Все права защищены.

## 👥 Поддержка

При возникновении проблем:
1. Проверьте документацию
2. Проверьте логи: `docker-compose logs` или SQL Server Error Log
3. Создайте issue в репозитории

---

**Версия:** 1.0.0-beta (Phase 2.2 Complete)
**Дата:** 2025-12-07
**Статус:** ~95% готовности

**Компоненты:**
- ✅ **Database schema** - MS SQL + PostgreSQL 15 + TimescaleDB
- ✅ **Backend API** - 70+ endpoints, WebSocket, AI analysis, SOAR, FIM
- ✅ **Windows Agent** - Event collection, inventory, Sysmon, IPBan
- ✅ **Network Monitor** - SNMP, Syslog, NetFlow, SNMP Traps, Device Discovery
- ✅ **Frontend** - React 18 + TypeScript + Ant Design
  - Dashboard, Events, Alerts, Incidents, Agents
  - Settings, Documentation viewer
  - **SOAR Playbooks UI** - управление playbooks и executions
  - **FIM UI** - File Integrity Monitoring
  - FreeScout integration UI

**Phase 1 Complete:**
- ✅ Event collection & storage
- ✅ Detection rules (19 правил)
- ✅ Incident management
- ✅ AI analysis integration
- ✅ Email notifications
- ✅ FreeScout helpdesk integration
- ✅ Threat Intelligence enrichment

**Phase 2 Complete:**
- ✅ SOAR Playbooks (8 playbooks, 9 actions)
- ✅ Auto-trigger на основе severity/MITRE
- ✅ Approval workflow
- ✅ IPBan integration (3 detection rules)
- ✅ File Integrity Monitoring via Sysmon (6 FIM rules)
- ✅ FIM UI with statistics

**Next:** Phase 3 - Advanced Search, Scheduled Reports, UEBA
