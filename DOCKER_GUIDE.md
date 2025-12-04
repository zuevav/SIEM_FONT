# 🐳 Docker Compose Deployment Guide

**Руководство по развертыванию SIEM системы с помощью Docker Compose**

---

## 📋 Содержание

1. [Преимущества Docker Compose](#преимущества-docker-compose)
2. [Архитектура](#архитектура)
3. [Требования](#требования)
4. [Быстрый старт](#быстрый-старт)
5. [Конфигурация](#конфигурация)
6. [Управление сервисами](#управление-сервисами)
7. [Мониторинг и логи](#мониторинг-и-логи)
8. [Backup и восстановление](#backup-и-восстановление)
9. [Production deployment](#production-deployment)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Преимущества Docker Compose

### Почему Docker Compose?

| Преимущество | Описание |
|--------------|----------|
| ⚡ **Быстрое развертывание** | 2 минуты вместо часов ручной установки |
| 🔒 **Изоляция** | Каждый сервис в своем контейнере |
| 📦 **Воспроизводимость** | Одинаковая среда на Dev/Test/Prod |
| 🔄 **Простое обновление** | `docker-compose pull && docker-compose up -d` |
| 📈 **Масштабируемость** | `docker-compose up --scale backend=3` |
| 🚀 **Откат** | Быстрый возврат к предыдущей версии |
| 🌍 **Портативность** | Работает на любой ОС с Docker |

### Что работает в Docker?

✅ **В контейнерах:**
- PostgreSQL 15 + TimescaleDB
- Backend (FastAPI)
- Frontend (Nginx + React)
- Redis (кэширование)
- PgAdmin (опционально - веб-интерфейс для БД)

❌ **Вне контейнеров (нативная установка):**
- Windows Agents (требуют доступ к Windows Event Log)
- Network Monitor (требует привилегированные порты 161/UDP, 162/UDP, 514/UDP)

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                         Docker Host                         │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Frontend   │    │   Backend    │    │  PostgreSQL  │  │
│  │  (Nginx +    │───▶│  (FastAPI)   │───▶│  TimescaleDB │  │
│  │   React)     │    │              │    │              │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│       :3000               :8000              :5432          │
│                              │                              │
│                              ▼                              │
│                       ┌──────────────┐                      │
│                       │    Redis     │                      │
│                       │  (Cache)     │                      │
│                       └──────────────┘                      │
│                            :6379                            │
│                                                             │
│  ┌──────────────┐                                          │
│  │   PgAdmin    │ (опционально)                            │
│  │  (Web UI)    │                                          │
│  └──────────────┘                                          │
│       :5050                                                 │
└─────────────────────────────────────────────────────────────┘
         ▲                                  ▲
         │                                  │
    ┌────┴─────┐                      ┌────┴──────┐
    │  Browser │                      │  Windows  │
    │  (Users) │                      │  Agents   │
    └──────────┘                      └───────────┘
```

---

## 💻 Требования

### Системные требования

**Минимальные (для тестирования):**
- CPU: 4 ядра
- RAM: 8 GB
- Disk: 50 GB
- OS: Linux / macOS / Windows + WSL2

**Рекомендуемые (для production):**
- CPU: 8+ ядер
- RAM: 16+ GB
- Disk: 200+ GB SSD
- OS: Ubuntu 22.04 LTS / Debian 11+

### Программное обеспечение

```bash
# Docker Engine 20.10+
docker --version

# Docker Compose V2
docker compose version

# Git
git --version
```

### Установка Docker

**Ubuntu/Debian:**
```bash
# Удалить старые версии
sudo apt remove docker docker-engine docker.io containerd runc

# Установить зависимости
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release

# Добавить GPG ключ Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Добавить репозиторий
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установить Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Добавить текущего пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker

# Проверить установку
docker run hello-world
```

**Windows:**
- Установите [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- Включите WSL2 backend

**macOS:**
- Установите [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)

---

## 🚀 Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/your-org/SIEM_FONT.git
cd SIEM_FONT
```

### 2. Настроить переменные окружения

```bash
# Скопировать шаблон
cp .env.example .env

# Отредактировать настройки
nano .env
```

**Минимальные обязательные изменения в .env:**

```bash
# 1. Пароли БД (ОБЯЗАТЕЛЬНО ИЗМЕНИТЬ!)
POSTGRES_PASSWORD=YourSecurePassword123!
POSTGRES_SUPERUSER_PASSWORD=PostgresAdminPassword456!

# 2. JWT Secret (ОБЯЗАТЕЛЬНО ИЗМЕНИТЬ!)
JWT_SECRET_KEY=$(openssl rand -hex 32)

# 3. AI Provider (выбрать и настроить один из)
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_actual_deepseek_key_here

# Или
# AI_PROVIDER=yandex_gpt
# YANDEX_GPT_API_KEY=your_actual_yandex_key
# YANDEX_GPT_FOLDER_ID=your_folder_id
```

### 3. Создать директории для volumes

```bash
mkdir -p volumes/{postgres,logs,uploads,archive,backups}
```

### 4. Запустить сервисы

```bash
# Запустить все сервисы
docker compose up -d

# Проверить статус
docker compose ps

# Посмотреть логи
docker compose logs -f
```

### 5. Инициализировать базу данных

```bash
# Подождать пока PostgreSQL запустится (30-60 секунд)
docker compose logs -f postgres

# Когда увидите "database system is ready to accept connections"
# выполнить инициализацию схемы

docker compose exec postgres psql -U siem_app -d siem_db -f /docker-entrypoint-initdb.d/schema.sql
docker compose exec postgres psql -U siem_app -d siem_db -f /docker-entrypoint-initdb.d/seed.sql
```

### 6. Проверить доступность

```bash
# Backend API
curl http://localhost:8000/health

# Frontend
curl http://localhost:3000

# PostgreSQL
docker compose exec postgres psql -U siem_app -d siem_db -c "SELECT version();"
```

### 7. Войти в систему

Откройте браузер: **http://localhost:3000**

**Учетные данные по умолчанию:**
- **Username:** `admin`
- **Password:** `Admin123!`

⚠️ **ВАЖНО:** Измените пароль сразу после первого входа!

---

## ⚙️ Конфигурация

### Переменные окружения

Полный список переменных см. в [.env.example](.env.example)

**Ключевые настройки:**

#### Database
```env
DATABASE_TYPE=postgresql          # postgresql или mssql
POSTGRES_HOST=postgres             # Имя сервиса в docker-compose
POSTGRES_DB=siem_db
POSTGRES_USER=siem_app
POSTGRES_PASSWORD=SecurePass123!
```

#### Backend
```env
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_WORKERS=4                  # Количество worker процессов
LOG_LEVEL=INFO                     # DEBUG, INFO, WARNING, ERROR
```

#### AI Provider
```env
AI_ENABLED=true
AI_PROVIDER=deepseek               # deepseek, yandex_gpt, openai
DEEPSEEK_API_KEY=sk-...
AI_TEMPERATURE=0.3
AI_MAX_TOKENS=2000
```

#### Security
```env
JWT_SECRET_KEY=random_secret_key_32_chars_minimum
JWT_EXPIRATION_MINUTES=480
PASSWORD_MIN_LENGTH=12
FAILED_LOGIN_ATTEMPTS=5
```

### Настройка портов

По умолчанию используются порты:
- `3000` - Frontend
- `8000` - Backend API
- `5432` - PostgreSQL
- `5050` - PgAdmin (если включен)
- `6379` - Redis

Изменить порты можно в `docker-compose.yml`:

```yaml
services:
  frontend:
    ports:
      - "8080:80"  # Изменить с 3000 на 8080
```

### Настройка ресурсов

Ограничить потребление ресурсов контейнерами:

```yaml
services:
  postgres:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

---

## 🎛️ Управление сервисами

### Базовые команды

```bash
# Запустить все сервисы
docker compose up -d

# Остановить все сервисы
docker compose stop

# Остановить и удалить контейнеры
docker compose down

# Остановить и удалить контейнеры + volumes
docker compose down -v

# Перезапустить сервис
docker compose restart backend

# Пересобрать и запустить
docker compose up -d --build

# Обновить только один сервис
docker compose up -d --no-deps --build backend
```

### Масштабирование

```bash
# Запустить 3 инстанса backend
docker compose up -d --scale backend=3

# Для production используйте load balancer (nginx, traefik)
```

### Обновление системы

```bash
# 1. Сделать backup БД
docker compose exec postgres pg_dump -U siem_app siem_db > backup_$(date +%Y%m%d).sql

# 2. Получить обновления
git pull

# 3. Остановить сервисы
docker compose down

# 4. Пересобрать образы
docker compose build --no-cache

# 5. Запустить обновленные сервисы
docker compose up -d

# 6. Проверить логи
docker compose logs -f
```

### Откат к предыдущей версии

```bash
# 1. Остановить текущую версию
docker compose down

# 2. Откатить git
git checkout <previous-commit-hash>

# 3. Пересобрать и запустить
docker compose up -d --build

# 4. Восстановить БД из backup (если нужно)
docker compose exec -T postgres psql -U siem_app -d siem_db < backup_20241204.sql
```

---

## 📊 Мониторинг и логи

### Просмотр логов

```bash
# Логи всех сервисов
docker compose logs

# Логи конкретного сервиса
docker compose logs backend

# Follow логи (real-time)
docker compose logs -f backend

# Последние 100 строк
docker compose logs --tail=100 backend

# Логи с timestamp
docker compose logs -t backend

# Логи с фильтром
docker compose logs backend | grep ERROR
```

### Статистика контейнеров

```bash
# Использование ресурсов
docker stats

# Информация о контейнере
docker compose ps
docker inspect siem-backend-1
```

### Подключение к контейнеру

```bash
# Bash в backend
docker compose exec backend bash

# Bash в postgres
docker compose exec postgres bash

# psql в postgres
docker compose exec postgres psql -U siem_app -d siem_db

# Python REPL в backend
docker compose exec backend python
```

### Health checks

```bash
# Проверить health status
docker compose ps

# Вручную проверить endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/stats
```

---

## 💾 Backup и восстановление

### Backup PostgreSQL

**Полный backup:**

```bash
# Backup базы данных
docker compose exec postgres pg_dump -U siem_app -Fc siem_db > backup_$(date +%Y%m%d_%H%M%S).dump

# Backup с gzip
docker compose exec postgres pg_dump -U siem_app siem_db | gzip > backup_$(date +%Y%m%d).sql.gz
```

**Backup только схемы:**

```bash
docker compose exec postgres pg_dump -U siem_app -s siem_db > schema_backup.sql
```

**Backup только данных:**

```bash
docker compose exec postgres pg_dump -U siem_app -a siem_db > data_backup.sql
```

**Автоматический backup (cron):**

```bash
# Создать скрипт backup
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
cd /path/to/SIEM_FONT
docker compose exec -T postgres pg_dump -U siem_app -Fc siem_db > $BACKUP_DIR/siem_backup_$DATE.dump
# Удалить backups старше 30 дней
find $BACKUP_DIR -name "siem_backup_*.dump" -mtime +30 -delete
EOF

chmod +x backup.sh

# Добавить в crontab (каждый день в 2:00 AM)
crontab -e
0 2 * * * /path/to/backup.sh >> /var/log/siem_backup.log 2>&1
```

### Восстановление PostgreSQL

```bash
# Остановить backend (чтобы не было подключений)
docker compose stop backend

# Восстановить из dump
docker compose exec -T postgres pg_restore -U siem_app -d siem_db -c < backup_20241204.dump

# Или из SQL
docker compose exec -T postgres psql -U siem_app -d siem_db < backup_20241204.sql

# Запустить backend
docker compose start backend
```

### Backup volumes

```bash
# Backup всех volumes
docker run --rm \
  -v siem_postgres_data:/source \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres_data_$(date +%Y%m%d).tar.gz -C /source .
```

---

## 🏭 Production Deployment

### Рекомендации для Production

#### 1. Используйте внешний PostgreSQL

Для production рекомендуется использовать отдельный сервер БД:

```yaml
# docker-compose.prod.yml
services:
  backend:
    environment:
      POSTGRES_HOST: db.company.local  # Внешний сервер
      POSTGRES_PORT: 5432
```

#### 2. Настройте SSL/TLS

```yaml
services:
  frontend:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.siem.rule=Host(`siem.company.com`)"
      - "traefik.http.routers.siem.entrypoints=websecure"
      - "traefik.http.routers.siem.tls=true"
      - "traefik.http.routers.siem.tls.certresolver=letsencrypt"
```

#### 3. Настройте логирование

```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"
```

#### 4. Настройте health checks

```yaml
services:
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

#### 5. Используйте secrets для паролей

```yaml
services:
  postgres:
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    secrets:
      - postgres_password

secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
```

#### 6. Настройте мониторинг

Используйте Prometheus + Grafana для мониторинга:

```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
```

---

## 🔧 Troubleshooting

### Проблемы с запуском

**Ошибка: "port is already allocated"**

```bash
# Найти процесс, занимающий порт
sudo lsof -i :8000
sudo netstat -tulpn | grep :8000

# Убить процесс или изменить порт в docker-compose.yml
```

**Ошибка: "network not found"**

```bash
# Удалить и пересоздать сеть
docker network prune
docker compose up -d
```

**Ошибка: "permission denied"**

```bash
# Дать права на volumes
sudo chown -R $USER:$USER volumes/
chmod -R 755 volumes/
```

### Проблемы с PostgreSQL

**Контейнер постоянно перезапускается:**

```bash
# Проверить логи
docker compose logs postgres

# Удалить volume и пересоздать
docker compose down -v
docker compose up -d
```

**Не могу подключиться к БД:**

```bash
# Проверить что БД запущена
docker compose ps postgres

# Проверить порт
docker compose port postgres 5432

# Подключиться напрямую
docker compose exec postgres psql -U siem_app -d siem_db

# Проверить переменные окружения
docker compose exec postgres env | grep POSTGRES
```

### Проблемы с Backend

**Backend не запускается:**

```bash
# Проверить логи
docker compose logs -f backend

# Проверить подключение к БД
docker compose exec backend python -c "import asyncpg; print('OK')"

# Пересобрать образ
docker compose up -d --build --no-deps backend
```

**Ошибки импорта модулей:**

```bash
# Пересобрать с --no-cache
docker compose build --no-cache backend
docker compose up -d backend
```

### Проблемы с Frontend

**Белый экран / 404:**

```bash
# Проверить что frontend собрался
docker compose logs frontend

# Проверить переменные окружения
docker compose exec frontend env | grep VITE

# Пересобрать
docker compose up -d --build frontend
```

**API недоступен:**

```bash
# Проверить CORS settings
docker compose exec backend cat .env | grep CORS

# Проверить nginx config
docker compose exec frontend cat /etc/nginx/conf.d/default.conf
```

### Проблемы с производительностью

**Медленные запросы:**

```bash
# Проверить индексы в БД
docker compose exec postgres psql -U siem_app -d siem_db -c "SELECT * FROM pg_stat_user_indexes WHERE idx_scan = 0;"

# Проверить slow queries
docker compose exec postgres psql -U siem_app -d siem_db -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

**Высокое потребление памяти:**

```bash
# Проверить статистику
docker stats

# Ограничить память для контейнера (в docker-compose.yml)
deploy:
  resources:
    limits:
      memory: 2G
```

### Очистка системы

```bash
# Удалить неиспользуемые контейнеры
docker container prune

# Удалить неиспользуемые образы
docker image prune -a

# Удалить неиспользуемые volumes
docker volume prune

# Удалить всё неиспользуемое
docker system prune -a --volumes
```

---

## 📚 Дополнительные ресурсы

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [TimescaleDB Docker Image](https://hub.docker.com/r/timescale/timescaledb)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/deployment/docker/)

---

## 📞 Поддержка

Если возникли проблемы:

1. Проверьте [Troubleshooting](#troubleshooting)
2. Посмотрите логи: `docker compose logs`
3. Создайте issue в GitHub
4. Обратитесь к документации: [README.md](README.md)

---

## ✅ Checklist для Production

- [ ] Изменены все пароли по умолчанию
- [ ] Настроен JWT_SECRET_KEY (случайная строка 32+ символов)
- [ ] Настроен AI provider (DeepSeek/Yandex GPT)
- [ ] Настроены email уведомления
- [ ] Настроен backup базы данных (cron)
- [ ] Настроен SSL/TLS (https)
- [ ] Настроен firewall (только нужные порты)
- [ ] Настроен мониторинг (Prometheus/Grafana)
- [ ] Протестирован процесс восстановления из backup
- [ ] Настроены retention policies (5 лет по требованию ЦБ)
- [ ] Документированы учетные данные (в защищенном хранилище)
- [ ] Настроена интеграция с Active Directory (если нужно)
- [ ] Проверена производительность под нагрузкой
- [ ] Настроены алерты для критичных событий
- [ ] Подготовлена документация для операторов

---

**Версия документа:** 1.0
**Дата обновления:** 2025-12-04
