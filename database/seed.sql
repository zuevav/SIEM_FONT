-- =====================================================================
-- SIEM DATABASE INITIAL DATA (SEED)
-- Начальные данные для быстрого старта системы
-- =====================================================================

USE SIEM_DB;
GO

PRINT 'Загрузка начальных данных...';
GO

-- =====================================================================
-- КАТЕГОРИИ ПРОГРАММНОГО ОБЕСПЕЧЕНИЯ
-- =====================================================================

SET IDENTITY_INSERT assets.SoftwareCategories ON;

INSERT INTO assets.SoftwareCategories (CategoryId, CategoryName, Description, DefaultRiskLevel, RequiresLicense, RequiresApproval) VALUES
(1, 'system', 'Компоненты операционной системы и драйверы', 'low', 0, 0),
(2, 'security', 'Антивирусы, EDR, фаерволы, средства защиты', 'low', 1, 0),
(3, 'office', 'Офисные приложения и инструменты продуктивности', 'low', 1, 0),
(4, 'browser', 'Веб-браузеры', 'low', 0, 0),
(5, 'development', 'Среды разработки, SDK, компиляторы', 'medium', 0, 1),
(6, 'database', 'СУБД и клиенты баз данных', 'medium', 1, 1),
(7, 'network', 'Сетевые утилиты, анализаторы трафика', 'medium', 0, 1),
(8, 'remote_access', 'Средства удалённого доступа (RDP, TeamViewer, AnyDesk)', 'high', 1, 1),
(9, 'crypto', 'Криптопровайдеры, средства электронной подписи', 'medium', 1, 0),
(10, 'financial', 'Банковское ПО, АБС, бухгалтерские системы', 'high', 1, 1),
(11, 'monitoring', 'Агенты мониторинга и управления', 'low', 0, 0),
(12, 'backup', 'Программное обеспечение резервного копирования', 'low', 1, 0),
(13, 'virtualization', 'Средства виртуализации (VMware, Hyper-V)', 'medium', 1, 1),
(14, 'media', 'Медиа-проигрыватели, графические редакторы', 'low', 0, 0),
(15, 'archive', 'Архиваторы и упаковщики', 'low', 0, 0),
(16, 'communication', 'Мессенджеры, почтовые клиенты, VoIP', 'medium', 0, 0),
(17, 'unknown', 'Неклассифицированное ПО', 'medium', 0, 1);

SET IDENTITY_INSERT assets.SoftwareCategories OFF;

PRINT '  ✓ Категории ПО загружены (17 категорий)';
GO

-- =====================================================================
-- НАСТРОЙКИ СИСТЕМЫ
-- =====================================================================

INSERT INTO config.Settings (SettingKey, SettingValue, Description, IsEncrypted) VALUES
-- Хранение данных
('retention_days', '1825', 'Срок хранения событий безопасности в днях (5 лет по требованию ЦБ)', 0),
('retention_alerts_days', '1825', 'Срок хранения алертов (5 лет)', 0),
('retention_audit_days', '1825', 'Срок хранения audit log (5 лет)', 0),
('archive_enabled', 'true', 'Включена ли автоматическая архивация старых данных', 0),

-- AI анализ
('ai_enabled', 'true', 'Включён ли AI-анализ событий', 0),
('ai_provider', 'yandex_gpt', 'Провайдер AI (yandex_gpt)', 0),
('ai_api_url', 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion', 'URL API Yandex GPT', 0),
('ai_api_key', '', 'API ключ Yandex Cloud (требуется настроить)', 1),
('ai_folder_id', '', 'Folder ID в Yandex Cloud', 0),
('ai_model', 'yandexgpt-lite', 'Модель AI (yandexgpt-lite или yandexgpt)', 0),
('ai_temperature', '0.3', 'Temperature для AI (0.0-1.0, меньше = более консервативно)', 0),
('ai_max_tokens', '2000', 'Максимальное количество токенов в ответе', 0),
('ai_batch_size', '10', 'Количество событий для анализа в одном запросе', 0),
('ai_fallback_enabled', 'true', 'Использовать локальные правила при недоступности AI', 0),

-- Уведомления
('notifications_enabled', 'true', 'Включены ли уведомления', 0),
('alert_email_enabled', 'true', 'Отправка алертов на email', 0),
('alert_email_smtp_server', '', 'SMTP сервер для email', 0),
('alert_email_smtp_port', '587', 'SMTP порт', 0),
('alert_email_from', 'siem@company.local', 'Email отправителя', 0),
('alert_email_username', '', 'SMTP username', 0),
('alert_email_password', '', 'SMTP password', 1),
('alert_email_use_tls', 'true', 'Использовать TLS для SMTP', 0),
('alert_telegram_enabled', 'false', 'Отправка алертов в Telegram', 0),
('alert_telegram_bot_token', '', 'Telegram Bot Token', 1),
('alert_telegram_chat_id', '', 'Telegram Chat ID для алертов', 0),

-- Интеграция с Active Directory
('ad_integration_enabled', 'false', 'Интеграция с Active Directory для аутентификации', 0),
('ad_server', '', 'LDAP сервер (ldap://dc.company.local:389)', 0),
('ad_base_dn', '', 'Base DN (DC=company,DC=local)', 0),
('ad_bind_user', '', 'Пользователь для bind', 0),
('ad_bind_password', '', 'Пароль для bind', 1),
('ad_user_search_filter', '(&(objectClass=user)(sAMAccountName={username}))', 'Фильтр поиска пользователей', 0),

-- Безопасность
('session_timeout_minutes', '480', 'Время жизни сессии в минутах (8 часов)', 0),
('jwt_secret', 'CHANGE_ME_IN_PRODUCTION', 'Секретный ключ для JWT (ТРЕБУЕТСЯ ИЗМЕНИТЬ!)', 1),
('jwt_algorithm', 'HS256', 'Алгоритм JWT', 0),
('jwt_expiration_minutes', '480', 'Срок действия JWT токена', 0),
('password_min_length', '12', 'Минимальная длина пароля', 0),
('password_require_uppercase', 'true', 'Требовать заглавные буквы в пароле', 0),
('password_require_lowercase', 'true', 'Требовать строчные буквы в пароле', 0),
('password_require_digits', 'true', 'Требовать цифры в пароле', 0),
('password_require_special', 'true', 'Требовать спецсимволы в пароле', 0),
('failed_login_attempts', '5', 'Количество неудачных попыток входа до блокировки', 0),
('account_lockout_minutes', '30', 'Время блокировки после неудачных попыток входа', 0),

-- Производительность
('event_batch_size', '1000', 'Размер батча для вставки событий', 0),
('event_processing_threads', '4', 'Количество потоков для обработки событий', 0),
('max_events_per_query', '10000', 'Максимальное количество событий в одном запросе', 0),

-- Агенты
('agent_heartbeat_interval_seconds', '60', 'Интервал heartbeat от агентов в секундах', 0),
('agent_offline_threshold_minutes', '5', 'Время до маркировки агента как offline', 0),
('agent_config_update_enabled', 'true', 'Разрешить обновление конфигурации агентов с сервера', 0),
('agent_auto_update_enabled', 'false', 'Автообновление агентов (осторожно в production!)', 0),

-- Отчётность для ЦБ РФ
('cbr_reporting_enabled', 'true', 'Включена ли функция отчётности для ЦБ', 0),
('cbr_organization_name', '', 'Название организации для отчётов', 0),
('cbr_organization_inn', '', 'ИНН организации', 0),
('cbr_organization_ogrn', '', 'ОГРН организации', 0),
('cbr_contact_person', '', 'Контактное лицо', 0),
('cbr_contact_email', '', 'Email для связи с регулятором', 0),
('cbr_contact_phone', '', 'Телефон для связи', 0),
('cbr_fincert_enabled', 'false', 'Автоматическая отправка в ФинЦЕРТ', 0),
('cbr_incident_threshold_severity', '3', 'Минимальный severity для автоматического создания отчёта в ЦБ', 0),

-- Прочие настройки
('system_timezone', 'Europe/Moscow', 'Часовой пояс системы', 0),
('ui_theme', 'dark', 'Тема интерфейса по умолчанию', 0),
('ui_language', 'ru', 'Язык интерфейса', 0),
('maintenance_mode', 'false', 'Режим обслуживания', 0);

PRINT '  ✓ Настройки системы загружены (56 параметров)';
GO

-- =====================================================================
-- ПОЛЬЗОВАТЕЛЬ ПО УМОЛЧАНИЮ
-- =====================================================================

-- Создаём администратора по умолчанию
-- Username: admin
-- Password: Admin123! (ОБЯЗАТЕЛЬНО ИЗМЕНИТЬ ПОСЛЕ ПЕРВОГО ВХОДА!)
-- Bcrypt hash: $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VzNQPAB7thK.lK

SET IDENTITY_INSERT config.Users ON;

INSERT INTO config.Users (UserId, Username, Email, PasswordHash, Role, IsADUser, IsActive) VALUES
(1, 'admin', 'admin@company.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VzNQPAB7thK.lK', 'admin', 0, 1),
(2, 'analyst', 'analyst@company.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VzNQPAB7thK.lK', 'analyst', 0, 1),
(3, 'viewer', 'viewer@company.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VzNQPAB7thK.lK', 'viewer', 0, 1);

SET IDENTITY_INSERT config.Users OFF;

PRINT '  ✓ Пользователи по умолчанию созданы:';
PRINT '    - admin / Admin123!  (роль: admin)';
PRINT '    - analyst / Admin123!  (роль: analyst)';
PRINT '    - viewer / Admin123!  (роль: viewer)';
PRINT '    ⚠ ВАЖНО: Измените пароли при первом входе!';
GO

-- =====================================================================
-- БАЗОВЫЕ ПРАВИЛА ДЕТЕКЦИИ (CRITICAL)
-- =====================================================================

SET IDENTITY_INSERT config.DetectionRules ON;

INSERT INTO config.DetectionRules (
    RuleId, RuleName, Description, IsEnabled, Severity, Priority,
    RuleType, RuleLogic,
    MitreAttackTactic, MitreAttackTechnique,
    CreatedBy, Tags
) VALUES
-- 1. Множественные неудачные попытки входа
(1, 'Множественные неудачные попытки входа',
 'Обнаружено более 5 неудачных попыток входа за 10 минут с одного хоста',
 1, 3, 10,
 'threshold',
 '{"event_code": 4625, "count": 5, "field": "SubjectUser", "distinct": true}',
 'Credential Access', 'T1110',
 1, '["authentication", "brute_force", "critical"]'),

-- 2. Запуск PowerShell с подозрительными параметрами
(2, 'PowerShell с подозрительными параметрами',
 'Обнаружен запуск PowerShell с параметрами obfuscation, bypass, encoded command',
 1, 4, 5,
 'simple',
 '{"process_name": "powershell.exe", "command_line_contains": ["-enc", "-w hidden", "-nop", "-exec bypass", "IEX", "Invoke-Expression"]}',
 'Execution', 'T1059.001',
 1, '["powershell", "execution", "critical"]'),

-- 3. Создание службы с SYSTEM привилегиями
(3, 'Создание новой службы Windows',
 'Создана новая служба Windows (возможна установка malware)',
 1, 3, 15,
 'simple',
 '{"event_code": 7045}',
 'Persistence', 'T1543.003',
 1, '["persistence", "service", "high"]'),

-- 4. Изменение критичных ключей реестра
(4, 'Изменение автозапуска в реестре',
 'Изменены ключи реестра автозапуска (Run, RunOnce)',
 1, 3, 20,
 'simple',
 '{"event_code": 13, "registry_path_contains": ["\\\\CurrentVersion\\\\Run", "\\\\CurrentVersion\\\\RunOnce"]}',
 'Persistence', 'T1547.001',
 1, '["persistence", "registry", "high"]'),

-- 5. Pass-the-Hash атака
(5, 'Подозрение на Pass-the-Hash',
 'Обнаружена аутентификация NTLM с подозрительными характеристиками',
 1, 4, 3,
 'simple',
 '{"event_code": 4776, "status": "0xC0000234"}',
 'Lateral Movement', 'T1550.002',
 1, '["lateral_movement", "pth", "critical"]'),

-- 6. Mimikatz в памяти
(6, 'Обнаружение Mimikatz',
 'Подозрительный доступ к памяти процесса lsass.exe (типично для Mimikatz)',
 1, 4, 1,
 'simple',
 '{"event_code": 10, "target_process": "lsass.exe", "granted_access": ["0x1010", "0x1410", "0x147a"]}',
 'Credential Access', 'T1003.001',
 1, '["credential_theft", "mimikatz", "critical"]'),

-- 7. Подозрительное сетевое подключение
(7, 'Исходящее подключение на нестандартный порт',
 'Процесс установил исходящее соединение на подозрительный порт',
 1, 2, 50,
 'simple',
 '{"event_code": 3, "destination_port_in": [4444, 5555, 6666, 7777, 8888, 9999, 31337]}',
 'Command and Control', 'T1071',
 1, '["network", "c2", "medium"]'),

-- 8. Удалённый доступ вне рабочего времени
(8, 'RDP подключение вне рабочих часов',
 'Успешное RDP подключение в нерабочее время (22:00-07:00)',
 1, 2, 30,
 'simple',
 '{"event_code": 4624, "logon_type": 10}',
 'Initial Access', 'T1078',
 1, '["remote_access", "rdp", "after_hours"]'),

-- 9. Запрещённое ПО
(9, 'Установка запрещённого программного обеспечения',
 'Обнаружена установка ПО из чёрного списка',
 1, 3, 25,
 'simple',
 '{"software_forbidden": true}',
 'Execution', 'T1204',
 1, '["software", "policy", "high"]'),

-- 10. Массовое чтение файлов (ransomware)
(10, 'Подозрение на Ransomware',
 'Процесс прочитал более 100 файлов за 1 минуту',
 1, 4, 2,
 'threshold',
 '{"event_code": 11, "count": 100, "field": "ProcessId", "file_extension_in": [".doc", ".docx", ".xls", ".xlsx", ".pdf"]}',
 'Impact', 'T1486',
 1, '["ransomware", "data_destruction", "critical"]');

SET IDENTITY_INSERT config.DetectionRules OFF;

PRINT '  ✓ Базовые правила детекции созданы (10 правил)';
GO

-- =====================================================================
-- ПРИМЕРЫ КЛАССИФИКАЦИИ ПО В СПРАВОЧНИКЕ
-- =====================================================================

SET IDENTITY_INSERT assets.SoftwareRegistry ON;

INSERT INTO assets.SoftwareRegistry (SoftwareId, Name, NormalizedName, Publisher, CategoryId, IsAllowed, IsForbidden, RequiresLicense, RiskLevel, Notes) VALUES
-- Безопасное ПО
(1, 'Microsoft Windows', 'windows', 'Microsoft Corporation', 1, 1, 0, 1, 'low', 'Операционная система'),
(2, 'Google Chrome', 'chrome', 'Google LLC', 4, 1, 0, 0, 'low', 'Веб-браузер'),
(3, 'Mozilla Firefox', 'firefox', 'Mozilla Foundation', 4, 1, 0, 0, 'low', 'Веб-браузер'),
(4, 'Microsoft Office', 'office', 'Microsoft Corporation', 3, 1, 0, 1, 'low', 'Офисный пакет'),
(5, 'Kaspersky Endpoint Security', 'kaspersky', 'Kaspersky Lab', 2, 1, 0, 1, 'low', 'Антивирус'),
(6, '7-Zip', '7zip', '7-Zip', 15, 1, 0, 0, 'low', 'Архиватор'),
(7, 'KeePass', 'keepass', 'KeePass', 9, 1, 0, 0, 'low', 'Менеджер паролей'),

-- Потенциально опасное ПО (требует одобрения)
(100, 'TeamViewer', 'teamviewer', 'TeamViewer GmbH', 8, 1, 0, 1, 'high', 'Удалённый доступ - требует контроля'),
(101, 'AnyDesk', 'anydesk', 'AnyDesk Software GmbH', 8, 1, 0, 1, 'high', 'Удалённый доступ - требует контроля'),
(102, 'Wireshark', 'wireshark', 'Wireshark Foundation', 7, 1, 0, 0, 'medium', 'Анализатор трафика - только для ИТ'),
(103, 'Nmap', 'nmap', 'Nmap Project', 7, 1, 0, 0, 'medium', 'Сканер сети - только для ИБ'),

-- Запрещённое ПО
(200, 'µTorrent', 'utorrent', 'BitTorrent Inc.', 17, 0, 1, 0, 'critical', 'Torrent-клиент - ЗАПРЕЩЁН'),
(201, 'BitTorrent', 'bittorrent', 'BitTorrent Inc.', 17, 0, 1, 0, 'critical', 'Torrent-клиент - ЗАПРЕЩЁН'),
(202, 'Ammyy Admin', 'ammyy', 'Ammyy', 8, 0, 1, 0, 'critical', 'Часто используется в мошенничестве - ЗАПРЕЩЁН'),
(203, 'Radmin', 'radmin', 'Famatech', 8, 0, 1, 1, 'critical', 'Несанкционированный удалённый доступ - ЗАПРЕЩЁН'),
(204, 'Remote Utilities', 'remote-utilities', 'Remote Utilities LLC', 8, 0, 1, 0, 'critical', 'Потенциально опасно - ЗАПРЕЩЁН');

SET IDENTITY_INSERT assets.SoftwareRegistry OFF;

PRINT '  ✓ Справочник ПО наполнен примерами (17 записей)';
GO

-- =====================================================================
-- ФИНАЛИЗАЦИЯ
-- =====================================================================

-- Логируем инициализацию системы
INSERT INTO compliance.AuditLog (Action, ObjectType, Details, Outcome)
VALUES (
    'system_initialized',
    'system',
    JSON_QUERY((
        SELECT
            GETUTCDATE() AS initialized_at,
            @@VERSION AS sql_version,
            DB_NAME() AS database_name
        FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
    )),
    'success'
);

PRINT '';
PRINT '═══════════════════════════════════════════════════════════════';
PRINT 'Начальные данные успешно загружены!';
PRINT '═══════════════════════════════════════════════════════════════';
PRINT '';
PRINT 'Что загружено:';
PRINT '  ✓ 17 категорий программного обеспечения';
PRINT '  ✓ 56 настроек системы';
PRINT '  ✓ 3 пользователя (admin, analyst, viewer)';
PRINT '  ✓ 10 базовых правил детекции угроз';
PRINT '  ✓ 17 записей в справочнике ПО';
PRINT '';
PRINT '⚠  ВАЖНЫЕ ДЕЙСТВИЯ ПОСЛЕ УСТАНОВКИ:';
PRINT '  1. Измените пароли пользователей по умолчанию';
PRINT '  2. Настройте Yandex GPT API (ai_api_key, ai_folder_id)';
PRINT '  3. Настройте SMTP для email уведомлений';
PRINT '  4. Заполните данные организации для отчётов в ЦБ';
PRINT '  5. Измените jwt_secret в production';
PRINT '  6. Настройте интеграцию с AD (опционально)';
PRINT '';
PRINT 'Следующий шаг: Создайте SQL Agent Jobs для обслуживания';
PRINT '  - Запустите database/jobs.sql';
PRINT '';
GO
