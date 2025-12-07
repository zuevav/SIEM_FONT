-- =====================================================================
-- SIEM DATABASE INITIAL DATA (SEED) FOR POSTGRESQL
-- Начальные данные для быстрого старта системы
-- =====================================================================

\echo 'Загрузка начальных данных...'

-- =====================================================================
-- КАТЕГОРИИ ПРОГРАММНОГО ОБЕСПЕЧЕНИЯ
-- =====================================================================

INSERT INTO assets.software_categories (category_id, category_name, description, default_risk_level, requires_license, requires_approval) VALUES
(1, 'system', 'Компоненты операционной системы и драйверы', 'low', FALSE, FALSE),
(2, 'security', 'Антивирусы, EDR, фаерволы, средства защиты', 'low', TRUE, FALSE),
(3, 'office', 'Офисные приложения и инструменты продуктивности', 'low', TRUE, FALSE),
(4, 'browser', 'Веб-браузеры', 'low', FALSE, FALSE),
(5, 'development', 'Среды разработки, SDK, компиляторы', 'medium', FALSE, TRUE),
(6, 'database', 'СУБД и клиенты баз данных', 'medium', TRUE, TRUE),
(7, 'network', 'Сетевые утилиты, анализаторы трафика', 'medium', FALSE, TRUE),
(8, 'remote_access', 'Средства удалённого доступа (RDP, TeamViewer, AnyDesk)', 'high', TRUE, TRUE),
(9, 'crypto', 'Криптопровайдеры, средства электронной подписи', 'medium', TRUE, FALSE),
(10, 'financial', 'Банковское ПО, АБС, бухгалтерские системы', 'high', TRUE, TRUE),
(11, 'monitoring', 'Агенты мониторинга и управления', 'low', FALSE, FALSE),
(12, 'backup', 'Программное обеспечение резервного копирования', 'low', TRUE, FALSE),
(13, 'virtualization', 'Средства виртуализации (VMware, Hyper-V)', 'medium', TRUE, TRUE),
(14, 'media', 'Медиа-проигрыватели, графические редакторы', 'low', FALSE, FALSE),
(15, 'archive', 'Архиваторы и упаковщики', 'low', FALSE, FALSE),
(16, 'communication', 'Мессенджеры, почтовые клиенты, VoIP', 'medium', FALSE, FALSE),
(17, 'unknown', 'Неклассифицированное ПО', 'medium', FALSE, TRUE)
ON CONFLICT (category_name) DO NOTHING;

-- Обновляем sequence
SELECT setval('assets.software_categories_category_id_seq', 17, true);

\echo '  ✓ Категории ПО загружены (17 категорий)'

-- =====================================================================
-- НАСТРОЙКИ СИСТЕМЫ
-- =====================================================================

INSERT INTO config.settings (setting_key, setting_value, description, is_encrypted) VALUES
-- Хранение данных
('retention_days', '1825', 'Срок хранения событий безопасности в днях (5 лет по требованию ЦБ)', FALSE),
('retention_alerts_days', '1825', 'Срок хранения алертов (5 лет)', FALSE),
('retention_audit_days', '1825', 'Срок хранения audit log (5 лет)', FALSE),
('archive_enabled', 'true', 'Включена ли автоматическая архивация старых данных', FALSE),

-- AI анализ
('ai_enabled', 'true', 'Включён ли AI-анализ событий', FALSE),
('ai_provider', 'deepseek', 'Провайдер AI (deepseek, yandex_gpt)', FALSE),
('ai_api_url', 'https://api.deepseek.com/v1/chat/completions', 'URL API для AI', FALSE),
('ai_api_key', '', 'API ключ для AI (требуется настроить)', TRUE),
('ai_model', 'deepseek-chat', 'Модель AI (deepseek-chat, yandexgpt-lite)', FALSE),
('ai_temperature', '0.3', 'Temperature для AI (0.0-1.0, меньше = более консервативно)', FALSE),
('ai_max_tokens', '2000', 'Максимальное количество токенов в ответе', FALSE),
('ai_batch_size', '10', 'Количество событий для анализа в одном запросе', FALSE),
('ai_fallback_enabled', 'true', 'Использовать локальные правила при недоступности AI', FALSE),

-- Уведомления
('notifications_enabled', 'true', 'Включены ли уведомления', FALSE),
('alert_email_enabled', 'true', 'Отправка алертов на email', FALSE),
('alert_email_smtp_server', '', 'SMTP сервер для email', FALSE),
('alert_email_smtp_port', '587', 'SMTP порт', FALSE),
('alert_email_from', 'siem@company.local', 'Email отправителя', FALSE),
('alert_email_username', '', 'SMTP username', FALSE),
('alert_email_password', '', 'SMTP password', TRUE),
('alert_email_use_tls', 'true', 'Использовать TLS для SMTP', FALSE),
('alert_telegram_enabled', 'false', 'Отправка алертов в Telegram', FALSE),
('alert_telegram_bot_token', '', 'Telegram Bot Token', TRUE),
('alert_telegram_chat_id', '', 'Telegram Chat ID для алертов', FALSE),

-- Интеграция с Active Directory
('ad_integration_enabled', 'false', 'Интеграция с Active Directory для аутентификации', FALSE),
('ad_server', '', 'LDAP сервер (ldap://dc.company.local:389)', FALSE),
('ad_base_dn', '', 'Base DN (DC=company,DC=local)', FALSE),
('ad_bind_user', '', 'Пользователь для bind', FALSE),
('ad_bind_password', '', 'Пароль для bind', TRUE),
('ad_user_search_filter', '(&(objectClass=user)(sAMAccountName={username}))', 'Фильтр поиска пользователей', FALSE),

-- Безопасность
('session_timeout_minutes', '480', 'Время жизни сессии в минутах (8 часов)', FALSE),
('jwt_secret', 'CHANGE_ME_IN_PRODUCTION', 'Секретный ключ для JWT (ТРЕБУЕТСЯ ИЗМЕНИТЬ!)', TRUE),
('jwt_algorithm', 'HS256', 'Алгоритм JWT', FALSE),
('jwt_expiration_minutes', '480', 'Срок действия JWT токена', FALSE),
('password_min_length', '12', 'Минимальная длина пароля', FALSE),
('password_require_uppercase', 'true', 'Требовать заглавные буквы в пароле', FALSE),
('password_require_lowercase', 'true', 'Требовать строчные буквы в пароле', FALSE),
('password_require_digits', 'true', 'Требовать цифры в пароле', FALSE),
('password_require_special', 'true', 'Требовать спецсимволы в пароле', FALSE),
('failed_login_attempts', '5', 'Количество неудачных попыток входа до блокировки', FALSE),
('account_lockout_minutes', '30', 'Время блокировки после неудачных попыток входа', FALSE),

-- Производительность
('event_batch_size', '1000', 'Размер батча для вставки событий', FALSE),
('event_processing_threads', '4', 'Количество потоков для обработки событий', FALSE),
('max_events_per_query', '10000', 'Максимальное количество событий в одном запросе', FALSE),

-- Агенты
('agent_heartbeat_interval_seconds', '60', 'Интервал heartbeat от агентов в секундах', FALSE),
('agent_offline_threshold_minutes', '5', 'Время до маркировки агента как offline', FALSE),
('agent_config_update_enabled', 'true', 'Разрешить обновление конфигурации агентов с сервера', FALSE),
('agent_auto_update_enabled', 'false', 'Автообновление агентов (осторожно в production!)', FALSE),

-- Отчётность для ЦБ РФ
('cbr_reporting_enabled', 'true', 'Включена ли функция отчётности для ЦБ', FALSE),
('cbr_organization_name', '', 'Название организации для отчётов', FALSE),
('cbr_organization_inn', '', 'ИНН организации', FALSE),
('cbr_organization_ogrn', '', 'ОГРН организации', FALSE),
('cbr_contact_person', '', 'Контактное лицо', FALSE),
('cbr_contact_email', '', 'Email для связи с регулятором', FALSE),
('cbr_contact_phone', '', 'Телефон для связи', FALSE),
('cbr_fincert_enabled', 'false', 'Автоматическая отправка в ФинЦЕРТ', FALSE),
('cbr_incident_threshold_severity', '3', 'Минимальный severity для автоматического создания отчёта в ЦБ', FALSE),

-- Прочие настройки
('system_timezone', 'Europe/Moscow', 'Часовой пояс системы', FALSE),
('ui_theme', 'dark', 'Тема интерфейса по умолчанию', FALSE),
('ui_language', 'ru', 'Язык интерфейса', FALSE),
('maintenance_mode', 'false', 'Режим обслуживания', FALSE)
ON CONFLICT (setting_key) DO NOTHING;

\echo '  ✓ Настройки системы загружены (56 параметров)'

-- =====================================================================
-- ПОЛЬЗОВАТЕЛИ ПО УМОЛЧАНИЮ
-- =====================================================================

-- Создаём администратора по умолчанию
-- Username: admin
-- Password: Admin123! (ОБЯЗАТЕЛЬНО ИЗМЕНИТЬ ПОСЛЕ ПЕРВОГО ВХОДА!)
-- Bcrypt hash: $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VzNQPAB7thK.lK

INSERT INTO config.users (user_id, username, email, password_hash, role, is_ad_user, is_active) VALUES
(1, 'admin', 'admin@company.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VzNQPAB7thK.lK', 'admin', FALSE, TRUE),
(2, 'analyst', 'analyst@company.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VzNQPAB7thK.lK', 'analyst', FALSE, TRUE),
(3, 'viewer', 'viewer@company.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VzNQPAB7thK.lK', 'viewer', FALSE, TRUE)
ON CONFLICT (username) DO NOTHING;

-- Обновляем sequence
SELECT setval('config.users_user_id_seq', 3, true);

\echo '  ✓ Пользователи по умолчанию созданы:'
\echo '    - admin / Admin123!  (роль: admin)'
\echo '    - analyst / Admin123!  (роль: analyst)'
\echo '    - viewer / Admin123!  (роль: viewer)'
\echo '    ⚠ ВАЖНО: Измените пароли при первом входе!'

-- =====================================================================
-- БАЗОВЫЕ ПРАВИЛА ДЕТЕКЦИИ (CRITICAL)
-- =====================================================================

INSERT INTO config.detection_rules (
    rule_id, rule_name, description, is_enabled, severity, priority,
    rule_type, rule_logic,
    mitre_attack_tactic, mitre_attack_technique,
    created_by, tags
) VALUES
-- 1. Множественные неудачные попытки входа
(1, 'Множественные неудачные попытки входа',
 'Обнаружено более 5 неудачных попыток входа за 10 минут с одного хоста',
 TRUE, 3, 10,
 'threshold',
 '{"event_code": 4625, "count": 5, "field": "subject_user", "distinct": true}'::jsonb,
 'Credential Access', 'T1110',
 1, '["authentication", "brute_force", "critical"]'::jsonb),

-- 2. Запуск PowerShell с подозрительными параметрами
(2, 'PowerShell с подозрительными параметрами',
 'Обнаружен запуск PowerShell с параметрами obfuscation, bypass, encoded command',
 TRUE, 4, 5,
 'simple',
 '{"process_name": "powershell.exe", "command_line_contains": ["-enc", "-w hidden", "-nop", "-exec bypass", "IEX", "Invoke-Expression"]}'::jsonb,
 'Execution', 'T1059.001',
 1, '["powershell", "execution", "critical"]'::jsonb),

-- 3. Создание службы с SYSTEM привилегиями
(3, 'Создание новой службы Windows',
 'Создана новая служба Windows (возможна установка malware)',
 TRUE, 3, 15,
 'simple',
 '{"event_code": 7045}'::jsonb,
 'Persistence', 'T1543.003',
 1, '["persistence", "service", "high"]'::jsonb),

-- 4. Изменение критичных ключей реестра
(4, 'Изменение автозапуска в реестре',
 'Изменены ключи реестра автозапуска (Run, RunOnce)',
 TRUE, 3, 20,
 'simple',
 '{"event_code": 13, "registry_path_contains": ["\\\\CurrentVersion\\\\Run", "\\\\CurrentVersion\\\\RunOnce"]}'::jsonb,
 'Persistence', 'T1547.001',
 1, '["persistence", "registry", "high"]'::jsonb),

-- 5. Pass-the-Hash атака
(5, 'Подозрение на Pass-the-Hash',
 'Обнаружена аутентификация NTLM с подозрительными характеристиками',
 TRUE, 4, 3,
 'simple',
 '{"event_code": 4776, "status": "0xC0000234"}'::jsonb,
 'Lateral Movement', 'T1550.002',
 1, '["lateral_movement", "pth", "critical"]'::jsonb),

-- 6. Mimikatz в памяти
(6, 'Обнаружение Mimikatz',
 'Подозрительный доступ к памяти процесса lsass.exe (типично для Mimikatz)',
 TRUE, 4, 1,
 'simple',
 '{"event_code": 10, "target_process": "lsass.exe", "granted_access": ["0x1010", "0x1410", "0x147a"]}'::jsonb,
 'Credential Access', 'T1003.001',
 1, '["credential_theft", "mimikatz", "critical"]'::jsonb),

-- 7. Подозрительное сетевое подключение
(7, 'Исходящее подключение на нестандартный порт',
 'Процесс установил исходящее соединение на подозрительный порт',
 TRUE, 2, 50,
 'simple',
 '{"event_code": 3, "destination_port_in": [4444, 5555, 6666, 7777, 8888, 9999, 31337]}'::jsonb,
 'Command and Control', 'T1071',
 1, '["network", "c2", "medium"]'::jsonb),

-- 8. Удалённый доступ вне рабочего времени
(8, 'RDP подключение вне рабочих часов',
 'Успешное RDP подключение в нерабочее время (22:00-07:00)',
 TRUE, 2, 30,
 'simple',
 '{"event_code": 4624, "logon_type": 10}'::jsonb,
 'Initial Access', 'T1078',
 1, '["remote_access", "rdp", "after_hours"]'::jsonb),

-- 9. Запрещённое ПО
(9, 'Установка запрещённого программного обеспечения',
 'Обнаружена установка ПО из чёрного списка',
 TRUE, 3, 25,
 'simple',
 '{"software_forbidden": true}'::jsonb,
 'Execution', 'T1204',
 1, '["software", "policy", "high"]'::jsonb),

-- 10. Массовое чтение файлов (ransomware)
(10, 'Подозрение на Ransomware',
 'Процесс прочитал более 100 файлов за 1 минуту',
 TRUE, 4, 2,
 'threshold',
 '{"event_code": 11, "count": 100, "field": "process_id", "file_extension_in": [".doc", ".docx", ".xls", ".xlsx", ".pdf"]}'::jsonb,
 'Impact', 'T1486',
 1, '["ransomware", "data_destruction", "critical"]'::jsonb)
ON CONFLICT (rule_name) DO NOTHING;

-- Обновляем sequence
SELECT setval('config.detection_rules_rule_id_seq', 10, true);

\echo '  ✓ Базовые правила детекции созданы (10 правил)'

-- =====================================================================
-- ПРИМЕРЫ КЛАССИФИКАЦИИ ПО В СПРАВОЧНИКЕ
-- =====================================================================

INSERT INTO assets.software_registry (software_id, name, normalized_name, publisher, category_id, is_allowed, is_forbidden, requires_license, risk_level, notes) VALUES
-- Безопасное ПО
(1, 'Microsoft Windows', 'windows', 'Microsoft Corporation', 1, TRUE, FALSE, TRUE, 'low', 'Операционная система'),
(2, 'Google Chrome', 'chrome', 'Google LLC', 4, TRUE, FALSE, FALSE, 'low', 'Веб-браузер'),
(3, 'Mozilla Firefox', 'firefox', 'Mozilla Foundation', 4, TRUE, FALSE, FALSE, 'low', 'Веб-браузер'),
(4, 'Microsoft Office', 'office', 'Microsoft Corporation', 3, TRUE, FALSE, TRUE, 'low', 'Офисный пакет'),
(5, 'Kaspersky Endpoint Security', 'kaspersky', 'Kaspersky Lab', 2, TRUE, FALSE, TRUE, 'low', 'Антивирус'),
(6, '7-Zip', '7zip', '7-Zip', 15, TRUE, FALSE, FALSE, 'low', 'Архиватор'),
(7, 'KeePass', 'keepass', 'KeePass', 9, TRUE, FALSE, FALSE, 'low', 'Менеджер паролей'),

-- Потенциально опасное ПО (требует одобрения)
(100, 'TeamViewer', 'teamviewer', 'TeamViewer GmbH', 8, TRUE, FALSE, TRUE, 'high', 'Удалённый доступ - требует контроля'),
(101, 'AnyDesk', 'anydesk', 'AnyDesk Software GmbH', 8, TRUE, FALSE, TRUE, 'high', 'Удалённый доступ - требует контроля'),
(102, 'Wireshark', 'wireshark', 'Wireshark Foundation', 7, TRUE, FALSE, FALSE, 'medium', 'Анализатор трафика - только для ИТ'),
(103, 'Nmap', 'nmap', 'Nmap Project', 7, TRUE, FALSE, FALSE, 'medium', 'Сканер сети - только для ИБ'),

-- Запрещённое ПО
(200, 'µTorrent', 'utorrent', 'BitTorrent Inc.', 17, FALSE, TRUE, FALSE, 'critical', 'Torrent-клиент - ЗАПРЕЩЁН'),
(201, 'BitTorrent', 'bittorrent', 'BitTorrent Inc.', 17, FALSE, TRUE, FALSE, 'critical', 'Torrent-клиент - ЗАПРЕЩЁН'),
(202, 'Ammyy Admin', 'ammyy', 'Ammyy', 8, FALSE, TRUE, FALSE, 'critical', 'Часто используется в мошенничестве - ЗАПРЕЩЁН'),
(203, 'Radmin', 'radmin', 'Famatech', 8, FALSE, TRUE, TRUE, 'critical', 'Несанкционированный удалённый доступ - ЗАПРЕЩЁН'),
(204, 'Remote Utilities', 'remote-utilities', 'Remote Utilities LLC', 8, FALSE, TRUE, FALSE, 'critical', 'Потенциально опасно - ЗАПРЕЩЁН')
ON CONFLICT DO NOTHING;

-- Обновляем sequence
SELECT setval('assets.software_registry_software_id_seq', 204, true);

\echo '  ✓ Справочник ПО наполнен примерами (17 записей)'

-- =====================================================================
-- PHASE 1: DEFAULT SETTINGS
-- =====================================================================

INSERT INTO config.system_settings (setting_key, setting_value, setting_type, category, description) VALUES
-- FreeScout Integration
('freescout_enabled', 'false', 'boolean', 'freescout', 'Enable FreeScout integration'),
('freescout_url', '', 'string', 'freescout', 'FreeScout base URL'),
('freescout_api_key', '', 'string', 'freescout', 'FreeScout API key'),
('freescout_mailbox_id', '1', 'integer', 'freescout', 'FreeScout mailbox ID for ticket creation'),
('freescout_auto_create_on_alert', 'false', 'boolean', 'freescout', 'Automatically create tickets for alerts'),
('freescout_auto_create_severity_min', '3', 'integer', 'freescout', 'Minimum severity for auto-ticket creation (0-4)'),
('freescout_sync_interval_seconds', '300', 'integer', 'freescout', 'Ticket sync interval in seconds'),

-- Email Notifications
('smtp_enabled', 'false', 'boolean', 'email', 'Enable email notifications'),
('smtp_host', '', 'string', 'email', 'SMTP server host'),
('smtp_port', '587', 'integer', 'email', 'SMTP server port'),
('smtp_username', '', 'string', 'email', 'SMTP username'),
('smtp_password', '', 'string', 'email', 'SMTP password'),
('smtp_from_email', 'siem@company.local', 'string', 'email', 'From email address'),
('smtp_from_name', 'SIEM System', 'string', 'email', 'From name'),
('smtp_use_tls', 'true', 'boolean', 'email', 'Use TLS for SMTP connection'),
('email_alert_recipients', '', 'string', 'email', 'Comma-separated list of alert recipients'),
('email_alert_min_severity', '3', 'integer', 'email', 'Minimum severity for email alerts (0-4)'),

-- AI Provider
('ai_provider', 'deepseek', 'string', 'ai', 'AI provider (deepseek, yandex_gpt, none)'),
('deepseek_api_key', '', 'string', 'ai', 'DeepSeek API key'),
('yandex_gpt_api_key', '', 'string', 'ai', 'Yandex GPT API key'),
('yandex_gpt_folder_id', '', 'string', 'ai', 'Yandex Cloud folder ID'),

-- Threat Intelligence
('threat_intel_enabled', 'false', 'boolean', 'threat_intel', 'Enable threat intelligence enrichment'),
('virustotal_api_key', '', 'string', 'threat_intel', 'VirusTotal API key'),
('abuseipdb_api_key', '', 'string', 'threat_intel', 'AbuseIPDB API key'),

-- System Updates
('auto_update_enabled', 'false', 'boolean', 'system', 'Enable automatic system updates'),
('update_check_interval_hours', '24', 'integer', 'system', 'Update check interval in hours'),
('last_update_check', '', 'string', 'system', 'Timestamp of last update check')

ON CONFLICT (setting_key) DO NOTHING;

\echo '  ✓ Phase 1 настройки добавлены (30 settings)'

-- =====================================================================
-- ФИНАЛИЗАЦИЯ
-- =====================================================================

\echo ''
\echo '============================================================='
\echo 'Начальные данные успешно загружены!'
\echo '============================================================='
\echo ''
\echo 'База данных готова к работе.'
\echo ''
\echo 'Следующие шаги:'
\echo '  1. Измените пароль администратора (admin / Admin123!)'
\echo '  2. Настройте AI provider в таблице config.settings'
\echo '  3. Настройте SMTP для email уведомлений'
\echo '  4. Запустите backend сервер'
\echo '  5. Запустите frontend'
\echo '  6. Установите Windows агенты на хосты'
\echo ''
