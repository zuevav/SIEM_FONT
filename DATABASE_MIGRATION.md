# Database Migration Guide

Руководство по выбору и миграции базы данных для SIEM системы.

## 📊 Сравнение баз данных

### PostgreSQL 15+ vs MS SQL Server 2019+

| Критерий | PostgreSQL + TimescaleDB | MS SQL Server |
|----------|--------------------------|---------------|
| **Лицензия** | ✅ Free, Open Source | ❌ Платная ($3,700+/core) |
| **Performance (INSERT)** | ✅ 50,000+ events/sec | ⚠️ 10,000 events/sec |
| **Performance (SELECT)** | ✅ 0.1-0.5 sec (BRIN) | ⚠️ 1-2 sec |
| **Compression** | ✅ 10-100x (TimescaleDB) | ⚠️ Columnstore (Enterprise) |
| **Partitioning** | ✅ Auto (TimescaleDB) | ⚠️ Manual |
| **Time-series** | ✅ Оптимизирован | ⚠️ Общего назначения |
| **JSONB** | ✅ Нативная поддержка | ⚠️ Limited |
| **Full-Text Search** | ✅ Встроенный | ⚠️ Отдельная настройка |
| **Replication** | ✅ Streaming (встроенная) | ⚠️ Требует настройки |
| **Linux Support** | ✅ Отличный | ⚠️ Limited features |
| **Community** | ✅ Огромное | ⚠️ Microsoft |
| **HA/Clustering** | ✅ Patroni, pgBouncer | ⚠️ Always On (Enterprise) |

### Рекомендации

**Используйте PostgreSQL если:**
- ✅ Новая установка
- ✅ Linux серверы
- ✅ Ограниченный бюджет
- ✅ >10,000 events/sec
- ✅ Нужно сжатие данных
- ✅ Open Source предпочтительнее

**Используйте MS SQL Server если:**
- ⚠️ Уже есть инфраструктура MS SQL
- ⚠️ Windows-only среда
- ⚠️ Есть Enterprise лицензии
- ⚠️ Нужна интеграция с MS ecosystem

---

## 🚀 Установка PostgreSQL + TimescaleDB

### Ubuntu 20.04/22.04

```bash
# Добавление репозитория PostgreSQL 15
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Добавление репозитория TimescaleDB
sudo sh -c "echo 'deb [signed-by=/usr/share/keyrings/timescale.keyring] https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main' > /etc/apt/sources.list.d/timescaledb.list"
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | gpg --dearmor | sudo tee /usr/share/keyrings/timescale.keyring >/dev/null

# Установка
sudo apt update
sudo apt install -y postgresql-15 postgresql-15-timescaledb-2.12

# Настройка TimescaleDB (автоматическая оптимизация)
sudo timescaledb-tune --quiet --yes

# Перезапуск PostgreSQL
sudo systemctl restart postgresql
sudo systemctl enable postgresql
```

### RHEL/CentOS 8+

```bash
# PostgreSQL 15
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm
sudo dnf -qy module disable postgresql
sudo dnf install -y postgresql15-server postgresql15-contrib

# TimescaleDB
sudo tee /etc/yum.repos.d/timescale_timescaledb.repo <<EOL
[timescale_timescaledb]
name=timescale_timescaledb
baseurl=https://packagecloud.io/timescale/timescaledb/el/8/\$basearch
repo_gpgcheck=1
gpgcheck=0
enabled=1
gpgkey=https://packagecloud.io/timescale/timescaledb/gpgkey
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOL

sudo dnf install -y timescaledb-2-postgresql-15

# Инициализация и запуск
sudo /usr/pgsql-15/bin/postgresql-15-setup initdb
sudo systemctl enable postgresql-15
sudo systemctl start postgresql-15

# Настройка TimescaleDB
sudo timescaledb-tune --quiet --yes
sudo systemctl restart postgresql-15
```

### Создание базы данных

```bash
# Вход в PostgreSQL
sudo -u postgres psql

# Создание БД и пользователя
CREATE DATABASE siem_db WITH ENCODING 'UTF8';
CREATE USER siem_app WITH PASSWORD 'YourStrongPassword123!';
GRANT ALL PRIVILEGES ON DATABASE siem_db TO siem_app;

# Подключение к БД
\c siem_db

# Включение TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

# Проверка extensions
\dx

# Выход
\q
```

### Настройка для production

```bash
# Редактирование postgresql.conf
sudo nano /etc/postgresql/15/main/postgresql.conf

# Рекомендуемые настройки:
shared_buffers = 4GB                    # 25% RAM
effective_cache_size = 12GB             # 75% RAM
maintenance_work_mem = 1GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1                  # For SSD
effective_io_concurrency = 200          # For SSD
work_mem = 64MB
min_wal_size = 1GB
max_wal_size = 4GB
max_worker_processes = 8
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
max_connections = 200

# TimescaleDB specific
timescaledb.max_background_workers = 8

# Перезапуск
sudo systemctl restart postgresql
```

### Настройка удалённого доступа

```bash
# postgresql.conf
listen_addresses = '*'

# pg_hba.conf
sudo nano /etc/postgresql/15/main/pg_hba.conf

# Добавить:
host    siem_db    siem_app    10.0.0.0/8       scram-sha-256
host    siem_db    siem_app    192.168.0.0/16   scram-sha-256

# Перезапуск
sudo systemctl restart postgresql

# Firewall
sudo ufw allow from 10.0.0.0/8 to any port 5432
```

---

## 📦 Установка схемы PostgreSQL

### Использование готовых скриптов

```bash
cd /opt/siem

# Установка schema (создаёт таблицы, hypertables)
psql -h localhost -U siem_app -d siem_db -f database_postgresql/schema.sql

# Установка functions и procedures
psql -h localhost -U siem_app -d siem_db -f database_postgresql/procedures.sql

# Установка triggers
psql -h localhost -U siem_app -d siem_db -f database_postgresql/triggers.sql

# Seed данные (default users, rules)
psql -h localhost -U siem_app -d siem_db -f database_postgresql/seed.sql

# Проверка
psql -h localhost -U siem_app -d siem_db -c "\dt security_events.*"
```

---

## 🔄 Миграция с MS SQL на PostgreSQL

### Вариант 1: Полная миграция (downtime)

#### Шаг 1: Экспорт данных из MS SQL

```sql
-- MS SQL Server
-- Экспорт Events
SELECT *
INTO OUTFILE 'events.csv'
FROM security_events.Events
ORDER BY EventId;

-- Экспорт Alerts
SELECT *
INTO OUTFILE 'alerts.csv'
FROM security_events.Alerts
ORDER BY AlertId;

-- Экспорт других таблиц...
```

#### Шаг 2: Импорт в PostgreSQL

```bash
# Events
psql -h localhost -U siem_app -d siem_db -c "
\COPY security_events.events FROM 'events.csv' WITH CSV HEADER;"

# Alerts
psql -h localhost -U siem_app -d siem_db -c "
\COPY security_events.alerts FROM 'alerts.csv' WITH CSV HEADER;"

# Обновление sequences
psql -h localhost -U siem_app -d siem_db -c "
SELECT setval('security_events.events_eventid_seq',
    (SELECT MAX(EventId) FROM security_events.events));"
```

### Вариант 2: Постепенная миграция (zero downtime)

#### Архитектура:

```
┌──────────────┐     ┌──────────────┐
│   MS SQL     │ ──▶ │  PostgreSQL  │
│  (старые     │     │  (новые      │
│   данные)    │     │   данные)    │
└──────────────┘     └──────────────┘
       ▲                     ▲
       │                     │
       └─────────┬───────────┘
                 │
         ┌───────────────┐
         │   Backend     │
         │   (пишет в    │
         │   оба БД)     │
         └───────────────┘
```

#### Шаг 1: Установить PostgreSQL и схему

```bash
# Установка PostgreSQL + TimescaleDB
# Создание схемы (см. выше)
```

#### Шаг 2: Настроить Backend для dual-write

```python
# backend/app/config.py
class Settings(BaseSettings):
    # Primary database
    DATABASE_TYPE: str = "postgresql"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_DB: str = "siem_db"

    # Legacy database (для чтения старых данных)
    LEGACY_MSSQL_ENABLED: bool = True
    MSSQL_SERVER: str = "old-server"
    MSSQL_DATABASE: str = "SIEM_DB"

# backend/app/database.py
if settings.LEGACY_MSSQL_ENABLED:
    # Создать две сессии
    pg_engine = create_engine(postgres_url)
    mssql_engine = create_engine(mssql_url)
```

#### Шаг 3: Миграция исторических данных (фоновый процесс)

```python
# scripts/migrate_historical_data.py
import asyncio
from datetime import datetime, timedelta

async def migrate_batch(start_date, end_date):
    # Читаем из MS SQL
    mssql_events = await read_mssql_events(start_date, end_date)

    # Пишем в PostgreSQL
    await write_postgres_events(mssql_events)

    print(f"Migrated {len(mssql_events)} events from {start_date} to {end_date}")

async def migrate_all():
    # Мигрировать по дням, начиная с самых старых
    start = datetime(2020, 1, 1)
    end = datetime.now()

    current = start
    while current < end:
        next_day = current + timedelta(days=1)
        await migrate_batch(current, next_day)
        current = next_day
        await asyncio.sleep(1)  # Throttle

# Запуск
asyncio.run(migrate_all())
```

#### Шаг 4: Переключение на PostgreSQL

```bash
# После миграции всех данных
# Выключить legacy mode
nano /opt/siem/.env

LEGACY_MSSQL_ENABLED=false

# Перезапустить backend
sudo systemctl restart siem-backend
```

#### Шаг 5: Удалить MS SQL (опционально)

```bash
# Бэкап MS SQL на всякий случай
# Затем можно выключить MS SQL Server
```

---

## 📈 Оптимизация PostgreSQL для SIEM

### Индексы

```sql
-- BRIN индексы для time-range queries (очень быстрые)
CREATE INDEX idx_events_time_brin ON security_events.events
    USING BRIN (EventTime) WITH (pages_per_range = 128);

-- B-tree для точных поисков
CREATE INDEX idx_events_guid ON security_events.events (EventGuid);
CREATE INDEX idx_events_computer ON security_events.events (Computer);
CREATE INDEX idx_events_eventcode ON security_events.events (EventCode);

-- Composite index
CREATE INDEX idx_events_comp_severity ON security_events.events (Computer, Severity);

-- GIN index для JSONB (если используется)
CREATE INDEX idx_events_data_gin ON security_events.events USING GIN (EventData);
```

### TimescaleDB Hypertables

```sql
-- Конвертация в hypertable (автоматическое partitioning)
SELECT create_hypertable('security_events.events', 'EventTime',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);

-- Добавление compression policy (сжатие после 7 дней)
ALTER TABLE security_events.events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'Computer, EventCode',
    timescaledb.compress_orderby = 'EventTime DESC'
);

SELECT add_compression_policy('security_events.events', INTERVAL '7 days');

-- Retention policy (удаление старше 5 лет)
SELECT add_retention_policy('security_events.events', INTERVAL '5 years');

-- Continuous Aggregates для быстрой аналитики
CREATE MATERIALIZED VIEW events_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', EventTime) AS hour,
    Computer,
    EventCode,
    COUNT(*) as event_count,
    AVG(Severity) as avg_severity
FROM security_events.events
GROUP BY hour, Computer, EventCode;

-- Refresh policy
SELECT add_continuous_aggregate_policy('events_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

### Vacuum и Maintenance

```sql
-- Автоматический vacuum (обычно включен по умолчанию)
ALTER TABLE security_events.events SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.005
);

-- Manual vacuum (при необходимости)
VACUUM ANALYZE security_events.events;

-- Reindex (если индексы "раздулись")
REINDEX INDEX CONCURRENTLY idx_events_time_brin;
```

---

## 🔄 Backup и Recovery

### Backup стратегии

#### 1. Полный бэкап (pg_dump)

```bash
# Полный бэкап БД
pg_dump -h localhost -U siem_app -d siem_db \
    -F c -f /backup/siem_db_$(date +%Y%m%d).dump

# Бэкап только схемы
pg_dump -h localhost -U siem_app -d siem_db \
    --schema-only -f /backup/siem_schema.sql

# Бэкап только данных
pg_dump -h localhost -U siem_app -d siem_db \
    --data-only -f /backup/siem_data.sql

# Автоматический бэкап (cron)
# Добавить в /etc/cron.d/siem-backup:
0 2 * * * postgres pg_dump -d siem_db -F c -f /backup/siem_$(date +\%Y\%m\%d).dump
```

#### 2. Incremental бэкап (WAL archiving)

```bash
# postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /backup/wal/%f && cp %p /backup/wal/%f'
max_wal_senders = 3

# Создать директорию
sudo mkdir -p /backup/wal
sudo chown postgres:postgres /backup/wal

# Перезапуск
sudo systemctl restart postgresql

# Base backup
sudo -u postgres pg_basebackup -D /backup/base -F tar -z -P
```

### Recovery

```bash
# Восстановление из pg_dump
pg_restore -h localhost -U siem_app -d siem_db \
    /backup/siem_db_20251203.dump

# Point-in-Time Recovery (PITR)
# 1. Остановить PostgreSQL
sudo systemctl stop postgresql

# 2. Восстановить base backup
cd /var/lib/postgresql/15/main
sudo rm -rf *
sudo tar -xzf /backup/base/base.tar.gz

# 3. Создать recovery.signal
sudo touch recovery.signal

# 4. Настроить postgresql.conf
restore_command = 'cp /backup/wal/%f %p'
recovery_target_time = '2025-12-03 12:00:00'

# 5. Запустить PostgreSQL
sudo systemctl start postgresql
```

---

## 📊 Мониторинг PostgreSQL

### Полезные запросы

```sql
-- Размер БД
SELECT pg_size_pretty(pg_database_size('siem_db'));

-- Размер таблиц
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Активные запросы
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query,
    query_start
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY query_start;

-- Cache hit ratio (должен быть > 99%)
SELECT
    sum(heap_blks_read) as heap_read,
    sum(heap_blks_hit) as heap_hit,
    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) AS cache_hit_ratio
FROM pg_statio_user_tables;

-- Index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Slow queries (pg_stat_statements)
SELECT
    query,
    calls,
    total_exec_time / 1000 as total_time_sec,
    mean_exec_time / 1000 as mean_time_sec,
    max_exec_time / 1000 as max_time_sec
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

### Prometheus + Grafana

```bash
# Установка postgres_exporter
wget https://github.com/prometheus-community/postgres_exporter/releases/download/v0.15.0/postgres_exporter-0.15.0.linux-amd64.tar.gz
tar xvf postgres_exporter-0.15.0.linux-amd64.tar.gz
cd postgres_exporter-0.15.0.linux-amd64

# Создать .pgpass
echo "localhost:5432:siem_db:siem_app:password" > ~/.pgpass
chmod 600 ~/.pgpass

# Запустить exporter
DATA_SOURCE_NAME="postgresql://siem_app@localhost:5432/siem_db?sslmode=disable" \
./postgres_exporter

# Metrics доступны на http://localhost:9187/metrics
```

---

## ⚡ Performance Tuning

### Оптимизация запросов

```sql
-- EXPLAIN ANALYZE для анализа плана запроса
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM security_events.events
WHERE EventTime > NOW() - INTERVAL '1 day'
AND Computer = 'SERVER-01';

-- Использовать prepared statements
PREPARE get_recent_events AS
SELECT * FROM security_events.events
WHERE EventTime > $1 AND Computer = $2;

EXECUTE get_recent_events('2025-12-03', 'SERVER-01');
```

### Connection Pooling (pgBouncer)

```bash
# Установка
sudo apt install -y pgbouncer

# Конфигурация /etc/pgbouncer/pgbouncer.ini
[databases]
siem_db = host=localhost port=5432 dbname=siem_db

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25

# Запуск
sudo systemctl enable pgbouncer
sudo systemctl start pgbouncer

# Backend подключается к pgBouncer вместо PostgreSQL
# Connection string: postgresql://localhost:6432/siem_db
```

---

## ✅ Checklist миграции

- [ ] Установлен PostgreSQL 15+
- [ ] Установлен TimescaleDB extension
- [ ] Создана БД и пользователь
- [ ] Настроен postgresql.conf (shared_buffers, work_mem, etc.)
- [ ] Установлена схема (schema.sql)
- [ ] Установлены procedures и triggers
- [ ] Создан seed data (default users)
- [ ] Настроены hypertables и compression
- [ ] Настроен retention policy (5 лет)
- [ ] Обновлён backend .env (DATABASE_TYPE=postgresql)
- [ ] Протестированы все API endpoints
- [ ] Настроен backup (pg_dump cron)
- [ ] Настроен мониторинг (Prometheus/Grafana)
- [ ] Документированы изменения

---

**Версия:** 1.0
**Дата:** 2025-12-03
**Поддержка:** [GitHub Issues](https://github.com/your-org/siem-system/issues)
