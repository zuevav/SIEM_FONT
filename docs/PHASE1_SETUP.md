# Руководство по настройке Phase 1

Полное руководство по настройке функций Phase 1: Настройки, Email уведомления, интеграция с FreeScout и Threat Intelligence.

> **Предварительные требования:** Завершите [Быструю установку](QUICK_INSTALL.md) перед настройкой Phase 1.

> **Связанная документация:**
> - [Руководство по быстрой установке](QUICK_INSTALL.md) - Инструкции по установке
> - [Спецификация интеграции с FreeScout](FREESCOUT_INTEGRATION.md) - Подробное руководство по интеграции с FreeScout
> - [Анализ рынка](MARKET_ANALYSIS.md) - Сравнение функций

## Содержание

1. [Миграция базы данных](#1-миграция-базы-данных)
2. [Email уведомления](#2-email-уведомления)
3. [Интеграция с FreeScout](#3-интеграция-с-freescout)
4. [Threat Intelligence](#4-threat-intelligence)
5. [GeoIP обогащение](#5-geoip-обогащение)
6. [Обновления системы](#6-обновления-системы)
7. [Тестирование](#7-тестирование)

---

## 1. Миграция базы данных

Выполните SQL-миграцию для создания необходимых таблиц:

```bash
# Используя sqlcmd (Linux/macOS)
sqlcmd -S localhost -U sa -P YourPassword -d SIEMDatabase \
  -i backend/migrations/001_create_system_settings.sql

# Используя SQL Server Management Studio (Windows)
# Откройте backend/migrations/001_create_system_settings.sql и выполните
```

**Созданные таблицы:**
- `config.SystemSettings` - Все системные настройки с шифрованием
- `incidents.FreeScoutTickets` - Отслеживание тикетов FreeScout
- `config.EmailNotifications` - Журнал аудита email
- `enrichment.ThreatIntelligence` - Кэш threat intelligence

**Проверка миграции:**
```sql
SELECT COUNT(*) FROM config.SystemSettings;
-- Должно вернуть ~15 строк с настройками по умолчанию
```

---

## 2. Email уведомления

### 2.1 Настройка SMTP

Перейдите в **Настройки → Email уведомления**:

**Пример Gmail:**
```
SMTP Host: smtp.gmail.com
SMTP Port: 587
Имя пользователя: your-email@gmail.com
Пароль: your-app-password  # НЕ ваш пароль Gmail!
Email отправителя: siem@yourcompany.com
Использовать TLS: ✓ Включено
```

> **Пароль приложения Gmail:** Google требует пароли приложений для SMTP. Сгенерируйте на https://myaccount.google.com/apppasswords

**Пример Яндекс Почта:**
```
SMTP Host: smtp.yandex.ru
SMTP Port: 587
Имя пользователя: your-email@yandex.ru
Пароль: your-password
Email отправителя: siem@yourcompany.com
Использовать TLS: ✓ Включено
```

**Пример Mail.ru:**
```
SMTP Host: smtp.mail.ru
SMTP Port: 465 или 587
Имя пользователя: your-email@mail.ru
Пароль: your-password
Email отправителя: siem@yourcompany.com
Использовать TLS: ✓ Включено
```

### 2.2 Настройка получателей

**Добавьте получателей (через запятую):**
```
admin@company.com, security@company.com, soc@company.com
```

**Мин. критичность:** `3` (только High и Critical)

### 2.3 Тестовое письмо

1. Нажмите кнопку **"Отправить тестовое письмо"**
2. Введите email получателя
3. Проверьте почтовый ящик на наличие тестового письма
4. При ошибке проверьте сообщение об ошибке

**Типичные проблемы:**
- ❌ "Ошибка аутентификации" → Неверное имя пользователя/пароль
- ❌ "Соединение отклонено" → Неверный хост/порт
- ❌ "Ошибка TLS" → Отключите TLS или используйте порт 465

### 2.4 Шаблоны писем

Письма включают:
- ✅ Значок критичности (цветовая кодировка)
- ✅ Название и описание алерта
- ✅ Контекст (hostname, пользователь, IP, процесс)
- ✅ Тактики/техники MITRE ATT&CK
- ✅ Рекомендации AI
- ✅ Результаты threat intelligence (если доступны)
- ✅ GeoIP локация (если доступна)
- ✅ Прямая ссылка на алерт в UI SIEM

**Автоматическая отправка:**
Письма отправляются автоматически когда:
- Критичность алерта ≥ настроенного порога (по умолчанию: 3 = High)
- SMTP включен
- Настроены получатели

---

## 3. Интеграция с FreeScout

> **Подробное руководство:** Для полной документации по интеграции с FreeScout см. [Спецификацию интеграции с FreeScout](FREESCOUT_INTEGRATION.md)

### 3.1 Предварительные требования

1. Работающий экземпляр **FreeScout** (https://freescout.net)
2. Установлен модуль **API & Webhooks**
3. Сгенерирован **API ключ**

### 3.2 Генерация API ключа

1. Войдите в FreeScout как администратор
2. Перейдите в **Управление → Настройки → API**
3. Нажмите **"Сгенерировать новый API ключ"**
4. Скопируйте ключ (начинается с `fs_`)

### 3.3 Конфигурация

Перейдите в **Настройки → Интеграция с FreeScout**:

```
URL FreeScout: https://helpdesk.yourcompany.com
API ключ: fs_xxxxxxxxxxxxxxxxxxxxxxxx
ID почтового ящика: 1
Авто-создание тикетов: ✓ Включено
Мин. критичность: 3 (только High и Critical)
```

**Найти ID почтового ящика:**
```bash
curl -X GET "https://helpdesk.yourcompany.com/api/mailboxes" \
  -H "X-FreeScout-API-Key: fs_xxxxxxxxxxxxxxxxxxxxxxxx"
```

### 3.4 Проверка подключения

1. Нажмите кнопку **"Проверить подключение"**
2. Должно показать: `✓ Подключение успешно. Найдено X почтовых ящиков`
3. Отображается название и ID почтового ящика

### 3.5 Настройка Webhook (Опционально)

Для двусторонней синхронизации (FreeScout → SIEM):

1. Перейдите в FreeScout **Управление → Настройки → Webhooks**
2. Добавьте новый webhook:
   ```
   URL: https://your-siem.com/api/v1/integrations/freescout/webhook
   События: conversation.status_changed, conversation.note_added
   Секрет: (сгенерируйте случайную строку)
   ```
3. Обновите настройки SIEM с секретом webhook

### 3.6 Создание тикетов

**Автоматически:**
Когда критичность алерта ≥ порога, тикет создаётся автоматически с:
- Темой: `[SIEM Алерт #123] Название алерта`
- Детали алерта, контекст, MITRE ATT&CK, рекомендации AI
- Теги: `siem`, `severity-high`, `category-name`
- Пользовательские поля: `alert_id`, `severity`

**Вручную:**
На странице деталей алерта нажмите кнопку **"Создать тикет FreeScout"**

---

## 4. Threat Intelligence

### 4.1 Получение API ключей

#### VirusTotal (Рекомендуется)
1. Зарегистрируйтесь на https://www.virustotal.com/gui/join-us
2. Бесплатный тариф: 4 запроса/минуту (500/день)
3. Перейдите в **Профиль → API ключ**
4. Скопируйте API ключ

#### AbuseIPDB (Рекомендуется)
1. Зарегистрируйтесь на https://www.abuseipdb.com/register
2. Бесплатный тариф: 1,000 запросов/день
3. Перейдите в **Аккаунт → API**
4. Скопируйте API ключ

### 4.2 Конфигурация

Перейдите в **Настройки → Threat Intelligence**:

```
Включить Threat Intelligence: ✓
API ключ VirusTotal: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
API ключ AbuseIPDB: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 4.3 Автоматическое обогащение

Когда включено, каждый новый алерт автоматически обогащается:

**Для SourceIP и TargetIP:**
1. ✅ Проверка репутации IP в VirusTotal
2. ✅ Оценка злоупотреблений в AbuseIPDB
3. ✅ Поиск GeoIP локации
4. ✅ Результаты сохраняются в JSON поле `alert.AIAnalysis`
5. ✅ Кэшируются на 24 часа

**Пример данных обогащения:**
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

### 4.4 Ручной поиск

**API Endpoints:**
```bash
# Поиск IP
curl -X POST "http://localhost:8000/api/v1/enrichment/lookup/ip" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ip_address": "1.2.3.4"}'

# Поиск хеша файла
curl -X POST "http://localhost:8000/api/v1/enrichment/lookup/hash" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"file_hash": "44d88612fea8a8f36de82e1278abb02f"}'

# Только GeoIP
curl "http://localhost:8000/api/v1/enrichment/geoip/8.8.8.8" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4.5 Управление кэшем

**Таблица кэша:** `enrichment.ThreatIntelligence`

**Просмотр кэша:**
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

**Очистка истёкшего кэша:**
```sql
DELETE FROM enrichment.ThreatIntelligence
WHERE CacheExpiresAt < GETUTCDATE();
```

---

## 5. GeoIP обогащение

### 5.1 Загрузка базы данных GeoLite2

**Вариант 1: Аккаунт MaxMind (Рекомендуется)**
1. Зарегистрируйтесь на https://www.maxmind.com/en/geolite2/signup
2. Войдите → **Загрузить базы данных**
3. Скачайте **GeoLite2 City** (формат MMDB)
4. Распакуйте `GeoLite2-City.mmdb`

**Вариант 2: Прямая загрузка (может требовать аккаунт)**
```bash
# Загрузка последней GeoLite2-City
wget https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb

# Или используя curl
curl -L -o GeoLite2-City.mmdb \
  https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb
```

### 5.2 Установка базы данных

**Docker (рекомендуется):**
```bash
# Копировать в docker volume
docker cp GeoLite2-City.mmdb siem-backend:/app/data/GeoLite2-City.mmdb

# Или примонтировать volume в docker-compose.yml
volumes:
  - ./data/GeoLite2-City.mmdb:/app/data/GeoLite2-City.mmdb
```

**Пути в системе Linux:**
```bash
# Вариант 1: /usr/share/GeoIP/
sudo mkdir -p /usr/share/GeoIP
sudo cp GeoLite2-City.mmdb /usr/share/GeoIP/

# Вариант 2: /var/lib/GeoIP/
sudo mkdir -p /var/lib/GeoIP
sudo cp GeoLite2-City.mmdb /var/lib/GeoIP/
```

### 5.3 Проверка установки

```bash
# Проверка статуса сервиса
curl "http://localhost:8000/api/v1/enrichment/status" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Ожидаемый ответ:
{
  "threat_intelligence": {...},
  "geoip": {
    "available": true,
    "db_path": "/app/data/GeoLite2-City.mmdb"
  }
}
```

### 5.4 Обновление базы данных (Рекомендуется ежемесячно)

MaxMind обновляет GeoLite2 ежемесячно. Настройте cron задачу:

```bash
# /etc/cron.monthly/update-geoip.sh
#!/bin/bash
curl -L -o /tmp/GeoLite2-City.mmdb \
  https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb

mv /tmp/GeoLite2-City.mmdb /usr/share/GeoIP/GeoLite2-City.mmdb

# Перезапустить backend для перезагрузки базы
docker restart siem-backend
```

---

## 6. Обновления системы

### 6.1 Проверка обновлений

Перейдите в **Настройки → Обновления системы**:

1. Нажмите **"Проверить обновления"**
2. Показывает текущую версию, git ветку, количество коммитов отставания
3. Отображает changelog если доступны обновления

### 6.2 Автоматическое обновление

**⚠️ ВНИМАНИЕ:** Это перезапустит сервис backend!

1. Нажмите кнопку **"Обновить сейчас"**
2. Подтвердите действие
3. Модальное окно прогресса показывает:
   - Git pull
   - Пересборка Docker образа
   - Перезапуск контейнера
4. Страница перезагрузится после завершения

**Ручное обновление (если автоматическое не работает):**
```bash
cd /path/to/SIEM_FONT
git pull origin main
docker-compose up -d --build
```

---

## 7. Тестирование

### 7.1 Тест Email уведомлений

Создайте тестовый алерт с высокой критичностью:

```bash
curl -X POST "http://localhost:8000/api/v1/alerts" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "severity": 4,
    "title": "Тестовый алерт высокой критичности",
    "description": "Тестирование email уведомлений",
    "category": "Test",
    "source_ip": "1.2.3.4"
  }'
```

**Ожидается:**
- ✅ Email отправлен настроенным получателям
- ✅ Email содержит детали алерта
- ✅ Запись в таблице `config.EmailNotifications`

### 7.2 Тест интеграции с FreeScout

Создайте тестовый алерт с высокой критичностью (аналогично выше).

**Ожидается:**
- ✅ Тикет создан в FreeScout
- ✅ Запись в таблице `incidents.FreeScoutTickets`
- ✅ Тикет содержит детали алерта

### 7.3 Тест Threat Intelligence

Создайте алерт с известным вредоносным IP:

```bash
curl -X POST "http://localhost:8000/api/v1/alerts" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "severity": 3,
    "title": "Тест Threat Intel",
    "description": "Тестирование обогащения threat intelligence",
    "category": "Test",
    "source_ip": "185.220.101.1"
  }'
```

**Ожидается:**
- ✅ Алерт обогащён данными threat intel
- ✅ `alert.AIAnalysis` содержит данные threat intel
- ✅ Запись в кэше `enrichment.ThreatIntelligence`
- ✅ Email/тикет включает результаты threat intel

### 7.4 Тест GeoIP

Ручной поиск:

```bash
curl "http://localhost:8000/api/v1/enrichment/geoip/8.8.8.8" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Ожидаемый ответ:**
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

## Устранение неполадок

### Email не отправляется

1. Проверьте настройки SMTP в интерфейсе настроек
2. Нажмите кнопку "Тестовое письмо"
3. Проверьте логи: `docker logs siem-backend | grep -i smtp`
4. Убедитесь что firewall разрешает исходящий SMTP (порт 587/465)

### Тикеты FreeScout не создаются

1. Проверьте правильность API ключа
2. Проверьте URL FreeScout (без завершающего слеша)
3. Протестируйте подключение в интерфейсе настроек
4. Проверьте логи: `docker logs siem-backend | grep -i freescout`

### Threat intel не работает

1. Проверьте валидность API ключей
2. Проверьте лимиты (VT: 4/мин, AbuseIPDB: 1000/день)
3. Включите threat intel в настройках
4. Проверьте логи: `docker logs siem-backend | grep -i "threat intel"`

### GeoIP недоступен

1. Скачайте GeoLite2-City.mmdb
2. Скопируйте в `/usr/share/GeoIP/` или `/app/data/`
3. Перезапустите backend: `docker restart siem-backend`
4. Проверьте статус: `/api/v1/enrichment/status`

---

## Следующие шаги

✅ Phase 1 завершён! Теперь у вас есть:
- Email уведомления для критических алертов
- Автоматическое создание тикетов FreeScout
- Обогащение threat intelligence
- Отслеживание GeoIP локации
- Механизм обновления системы

**Phase 2 (Опционально):**
- Продвинутый threat hunting
- Пользовательские правила детекции
- SOAR playbooks
- Продвинутая отчётность
