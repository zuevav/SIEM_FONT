# Руководство по быстрой установке

## Установка в один клик

SIEM система поддерживает полностью автоматизированную установку без ручной настройки!

---

## Установка на Linux/Unix (Рекомендуется)

### Установка одной командой (требуется интернет)

```bash
curl -sSL https://raw.githubusercontent.com/zuevav/SIEM_FONT/main/install.sh | sudo bash
```

Или с wget:

```bash
wget -qO- https://raw.githubusercontent.com/zuevav/SIEM_FONT/main/install.sh | sudo bash
```

### Ручная загрузка и установка

```bash
# Скачать установщик
wget https://raw.githubusercontent.com/zuevav/SIEM_FONT/main/install.sh

# Сделать исполняемым
chmod +x install.sh

# Запустить установщик
sudo ./install.sh
```

### Что делает установщик

1. Проверяет вашу ОС (Ubuntu, Debian, CentOS, RHEL, Fedora)
2. Устанавливает зависимости (Docker, Docker Compose, Git, curl)
3. Загружает последнюю версию SIEM с GitHub
4. Запускает интерактивный мастер настройки
5. Генерирует безопасные пароли
6. Собирает и запускает Docker контейнеры
7. Выполняет проверку работоспособности
8. Создаёт systemd сервис для автозапуска
9. Выводит URL доступа и учётные данные

### Время установки

- **Чистая установка**: 5-10 минут (зависит от скорости интернета)
- **Обновление существующей**: 1-2 минуты

---

## Установка на Windows

### Требования

- Windows 10/11 или Windows Server 2019/2022
- Права администратора
- Docker Desktop для Windows (установщик поможет с установкой)

### Шаги

1. **Скачайте PowerShell установщик**

   Откройте PowerShell от имени администратора и выполните:

   ```powershell
   Invoke-WebRequest -Uri https://raw.githubusercontent.com/zuevav/SIEM_FONT/main/install.ps1 -OutFile install.ps1
   ```

2. **Запустите установщик**

   ```powershell
   PowerShell -ExecutionPolicy Bypass -File install.ps1
   ```

3. **Следуйте мастеру**

   Установщик выполнит:
   - Проверку/установку Docker Desktop
   - Загрузку SIEM с GitHub
   - Интерактивную настройку системы
   - Запуск всех сервисов
   - Создание задачи планировщика для автозапуска

### Время установки

- **С уже установленным Docker Desktop**: 10-15 минут
- **Первичная установка (нужен Docker Desktop)**: 20-30 минут

---

## Мастер настройки

Во время установки вам будут заданы вопросы:

### 1. Администратор
- **Имя пользователя** (по умолчанию: `admin`)
- **Пароль** (по умолчанию: `admin123`)

> **Безопасность**: Смените пароль по умолчанию после первого входа!

### 2. Сетевые порты
- **Порт API** (по умолчанию: `8000`)
- **Порт Frontend** (по умолчанию: `3000`)

### 3. AI провайдер
Выберите один из вариантов:
- **DeepSeek** (бесплатный, рекомендуется) - API ключ опционален
- **Yandex GPT** - Требуется API ключ + Folder ID
- **Нет** - Пропустить AI функции

---

## После установки

### URL доступа

После завершения установки:

| Сервис | URL | Описание |
|--------|-----|----------|
| **Frontend** | http://localhost:3000 | Веб-интерфейс |
| **API** | http://localhost:8000 | REST API |
| **API Документация** | http://localhost:8000/docs | Swagger UI |
| **Redoc** | http://localhost:8000/redoc | Альтернативная документация |

### Учётные данные по умолчанию

- **Имя пользователя**: `admin` (или пользовательское, если изменено)
- **Пароль**: `admin123` (или пользовательский, если изменён)

> **Первый вход**: Перейдите в Настройки → Смена пароля

### Расположение установки

- **Linux**: `/opt/siem/`
- **Windows**: `C:\SIEM\`

### Файл конфигурации

- **Linux**: `/opt/siem/.env`
- **Windows**: `C:\SIEM\.env`

---

## Команды управления

### Linux (systemd)

```bash
# Проверить статус
sudo systemctl status siem

# Запустить SIEM
sudo systemctl start siem

# Остановить SIEM
sudo systemctl stop siem

# Перезапустить SIEM
sudo systemctl restart siem

# Просмотр логов
cd /opt/siem && docker-compose logs -f

# Обновить SIEM
cd /opt/siem && git pull && docker-compose up -d --build
```

### Windows (Docker Compose)

```powershell
# Перейти в каталог установки
cd C:\SIEM

# Проверить статус
docker-compose ps

# Запустить SIEM
docker-compose start

# Остановить SIEM
docker-compose stop

# Перезапустить SIEM
docker-compose restart

# Просмотр логов
docker-compose logs -f

# Обновить SIEM
git pull
docker-compose up -d --build
```

---

## Устранение неполадок

### Ошибка установки

**Linux:**
```bash
# Просмотр логов установщика
cat /var/log/siem-install.log

# Проверка сервиса Docker
sudo systemctl status docker

# Ручная очистка
cd /opt/siem && sudo docker-compose down
sudo rm -rf /opt/siem
```

**Windows:**
```powershell
# Проверка Docker Desktop
docker version

# Просмотр логов compose
cd C:\SIEM
docker-compose logs

# Ручная очистка
docker-compose down
Remove-Item -Recurse -Force C:\SIEM
```

### Сервисы не запускаются

```bash
# Проверка статуса контейнеров
docker-compose ps

# Просмотр логов конкретного сервиса
docker-compose logs backend
docker-compose logs db
docker-compose logs frontend

# Перезапуск проблемного сервиса
docker-compose restart backend
```

### Нет доступа к Frontend

1. Проверьте, работает ли контейнер:
   ```bash
   docker-compose ps frontend
   ```

2. Проверьте привязку порта:
   ```bash
   netstat -tuln | grep 3000  # Linux
   netstat -ano | findstr 3000  # Windows
   ```

3. Проверьте firewall:
   ```bash
   # Linux (Ubuntu)
   sudo ufw allow 3000

   # Windows
   New-NetFirewallRule -DisplayName "SIEM Frontend" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
   ```

### Проблемы с подключением к БД

```bash
# Проверка логов базы данных
docker-compose logs db

# Проверка готовности БД
docker-compose exec db psql -U siem -d siem_db -c "SELECT 1;"

# Переинициализация БД
docker-compose down -v
docker-compose up -d
```

### AI анализ не работает

1. Проверьте конфигурацию AI провайдера в `.env`:
   ```bash
   cat .env | grep AI_PROVIDER
   ```

2. Убедитесь, что API ключ установлен:
   ```bash
   cat .env | grep DEEPSEEK_API_KEY
   # или
   cat .env | grep YANDEX_GPT_API_KEY
   ```

3. Тест AI сервиса:
   ```bash
   curl http://localhost:8000/api/v1/ai/health
   ```

---

## Обновление SIEM

### Автоматическое обновление

**Linux:**
```bash
cd /opt/siem
git pull origin main
docker-compose pull
docker-compose up -d --build
```

**Windows:**
```powershell
cd C:\SIEM
git pull origin main
docker-compose pull
docker-compose up -d --build
```

### Периодичность обновлений

- **Стабильные релизы**: Ежемесячно
- **Патчи безопасности**: По мере необходимости
- **Обновления функций**: Каждые две недели

### Резервное копирование перед обновлением

```bash
# Резервная копия БД
docker-compose exec db pg_dump -U siem siem_db > backup_$(date +%Y%m%d).sql

# Резервная копия конфигурации
cp .env .env.backup

# Резервная копия правил детекции
docker-compose exec db psql -U siem -d siem_db -c "COPY detection_rules TO STDOUT CSV HEADER" > rules_backup.csv
```

---

## Удаление

### Linux

```bash
# Остановка сервисов
cd /opt/siem
sudo docker-compose down -v

# Удаление systemd сервиса
sudo systemctl stop siem
sudo systemctl disable siem
sudo rm /etc/systemd/system/siem.service
sudo systemctl daemon-reload

# Удаление файлов
sudo rm -rf /opt/siem
```

### Windows

```powershell
# Остановка сервисов
cd C:\SIEM
docker-compose down -v

# Удаление задачи планировщика
Unregister-ScheduledTask -TaskName "SIEM System" -Confirm:$false

# Удаление файлов
Remove-Item -Recurse -Force C:\SIEM
```

---

## Расширенные опции установки

### Пользовательский каталог установки

**Linux:**
```bash
# Скачать установщик
wget https://raw.githubusercontent.com/zuevav/SIEM_FONT/main/install.sh
chmod +x install.sh

# Изменить переменную INSTALL_DIR
nano install.sh
# Измените: INSTALL_DIR="/your/custom/path"

# Запуск
sudo ./install.sh
```

**Windows:**
```powershell
.\install.ps1 -InstallPath "D:\MyCustomPath\SIEM"
```

### Тихая установка (без запросов)

Создайте файл `.env` перед запуском установщика:

```bash
# Создание предварительно настроенного .env
cat > /opt/siem/.env << EOF
POSTGRES_PASSWORD=your_secure_password
JWT_SECRET=your_jwt_secret
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=secure_password
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_api_key
API_PORT=8000
FRONTEND_PORT=3000
EOF

# Запуск установщика (обнаружит существующий .env)
sudo ./install.sh
```

### Установка в изолированной сети (Air-Gapped)

Для сред без интернета:

1. **Загрузите все файлы на машине с интернетом:**
   ```bash
   git clone https://github.com/zuevav/SIEM_FONT.git
   cd SIEM_FONT

   # Загрузка Docker образов
   docker-compose pull
   docker save -o siem-images.tar \
     postgres:15-alpine \
     $(docker-compose config | grep 'image:' | awk '{print $2}')
   ```

2. **Перенесите на изолированную машину:**
   - Каталог SIEM_FONT
   - siem-images.tar

3. **Загрузите на изолированной машине:**
   ```bash
   docker load -i siem-images.tar
   cd SIEM_FONT
   docker-compose up -d
   ```

---

## Усиление безопасности

### После установки

1. **Смените пароль по умолчанию** (через UI или API)

2. **Настройте firewall:**
   ```bash
   # Linux (ufw)
   sudo ufw allow from YOUR_ADMIN_IP to any port 3000
   sudo ufw allow from YOUR_ADMIN_IP to any port 8000

   # Windows
   # Используйте GUI Windows Defender Firewall или PowerShell
   ```

3. **Включите HTTPS** (см. docs/HTTPS_SETUP.md)

4. **Проверьте права доступа к .env:**
   ```bash
   # Linux
   chmod 600 /opt/siem/.env

   # Windows
   icacls C:\SIEM\.env /inheritance:r /grant:r Administrators:F
   ```

5. **Включите журналирование аудита:**
   Отредактируйте `.env`:
   ```
   LOG_LEVEL=INFO
   AUDIT_ENABLED=true
   ```

---

## Получение помощи

### Документация

- [Руководство по настройке Phase 1](PHASE1_SETUP.md) - Настройка Email, FreeScout, Threat Intelligence
- [Интеграция с FreeScout](FREESCOUT_INTEGRATION.md) - Подробное руководство по интеграции с helpdesk
- [Анализ рынка](MARKET_ANALYSIS.md) - Сравнение функций с коммерческими SIEM решениями

### Каналы поддержки

- **GitHub Issues**: https://github.com/zuevav/SIEM_FONT/issues
- **Документация**: `/opt/siem/docs/` или `C:\SIEM\docs\`
- **Сообщество**: [Скоро]

### Расположение логов

- **Linux**: `/opt/siem/logs/` (внутри контейнеров)
- **Windows**: `C:\SIEM\logs\` (внутри контейнеров)

Просмотр:
```bash
docker-compose logs -f --tail=100 backend
```

---

## Следующие шаги

После успешной установки:

1. **Войдите в веб-интерфейс** - http://localhost:3000
2. **Смените пароль по умолчанию** - Настройки → Безопасность
3. **Настройте функции Phase 1** - См. [Руководство по настройке Phase 1](PHASE1_SETUP.md)
4. **Установите Windows агент** - См. `agent/README.md`
5. **Проверьте правила детекции** - 10 предустановленных правил
6. **Настройте AI провайдер** - Настройки → Конфигурация AI
7. **Мониторьте Dashboard** - Визуализация событий в реальном времени
8. **Настройте интеграции** - Email, FreeScout, Threat Intelligence (см. [Настройка Phase 1](PHASE1_SETUP.md))

---

**Установка успешно завершена!**

По вопросам или проблемам создайте GitHub issue: https://github.com/zuevav/SIEM_FONT/issues
