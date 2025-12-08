# Миграции базы данных

Эта папка содержит SQL-миграции для базы данных SIEM системы.

## Выполнение миграций

### Вариант 1: Ручное выполнение (рекомендуется для первоначальной установки)

Подключитесь к базе данных SQL Server и выполните миграции по порядку:

```bash
# Используя sqlcmd
sqlcmd -S localhost -U sa -P YourPassword -d SIEMDatabase -i migrations/001_create_system_settings.sql

# Или используя SQL Server Management Studio (SSMS)
# Откройте файл и выполните его
```

### Вариант 2: Используя Python-скрипт

```bash
cd backend
python scripts/run_migrations.py
```

## Файлы миграций

- `001_create_system_settings.sql` - Создаёт таблицы SystemSettings, FreeScoutTickets, EmailNotifications и ThreatIntelligence

## Создаваемые таблицы

### config.SystemSettings
Хранит все системные настройки (FreeScout, Email, AI и др.) с поддержкой шифрования конфиденциальных данных.

### incidents.FreeScoutTickets
Отслеживает связь между алертами/инцидентами SIEM и тикетами FreeScout для синхронизации.

### config.EmailNotifications
Логирует все отправленные email-уведомления для аудита.

### enrichment.ThreatIntelligence
Кэширует результаты запросов к источникам Threat Intelligence (VirusTotal, AbuseIPDB и др.) для избежания превышения лимитов API.

## Действия после миграции

После выполнения миграций настройте параметры через страницу "Настройки" в веб-интерфейсе:

1. **Настройка Email**
   - SMTP сервер, порт, учётные данные
   - Тестовая отправка email

2. **Интеграция с FreeScout**
   - URL FreeScout, API ключ, ID почтового ящика
   - Проверка подключения

3. **Настройка AI**
   - Выбор провайдера (DeepSeek/YandexGPT)
   - Добавление API ключей

4. **Threat Intelligence**
   - Добавление API ключа VirusTotal
   - Добавление API ключа AbuseIPDB
