-- =====================================================================
-- SIEM DATABASE SCHEMA FOR POSTGRESQL 15 + TIMESCALEDB
-- Соответствие требованиям ЦБ РФ: 683-П, 716-П, 747-П, ГОСТ Р 57580
-- =====================================================================
-- Версия: 1.0
-- Дата создания: 2025-12-04
-- Описание: Полная схема базы данных SIEM-системы с поддержкой
--           инвентаризации активов, событий безопасности, инцидентов
--           и экспорта для регулятора.
--           Использует TimescaleDB для time-series оптимизации.
-- =====================================================================

-- =====================================================================
-- УСТАНОВКА РАСШИРЕНИЙ
-- =====================================================================

-- TimescaleDB для time-series данных
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Full-Text Search (уже включен в PostgreSQL)
-- CREATE EXTENSION IF NOT EXISTS pg_trgm; -- для Like %pattern%

-- Статистика запросов (опционально)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- =====================================================================
-- СОЗДАНИЕ СХЕМ ДЛЯ ОРГАНИЗАЦИИ ОБЪЕКТОВ
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS security_events;
CREATE SCHEMA IF NOT EXISTS config;
CREATE SCHEMA IF NOT EXISTS incidents;
CREATE SCHEMA IF NOT EXISTS assets;
CREATE SCHEMA IF NOT EXISTS compliance;

-- =====================================================================
-- ТАБЛИЦЫ КОНФИГУРАЦИИ И ПОЛЬЗОВАТЕЛЕЙ
-- =====================================================================

-- Таблица пользователей системы
CREATE TABLE config.users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255),
    password_hash VARCHAR(255), -- NULL если AD-аутентификация
    role VARCHAR(20) NOT NULL DEFAULT 'viewer', -- admin, analyst, viewer
    is_ad_user BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    settings JSONB, -- JSON с пользовательскими настройками
    CONSTRAINT ck_users_role CHECK (role IN ('admin', 'analyst', 'viewer'))
);

-- Индексы для пользователей
CREATE INDEX idx_users_username ON config.users(username) WHERE is_active = TRUE;
CREATE INDEX idx_users_role ON config.users(role);

COMMENT ON TABLE config.users IS 'Пользователи SIEM-системы с RBAC';

-- =====================================================================
-- ТАБЛИЦЫ АКТИВОВ И ИНВЕНТАРИЗАЦИИ
-- =====================================================================

-- Таблица агентов (хостов)
CREATE TABLE assets.agents (
    agent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hostname VARCHAR(255) NOT NULL,
    fqdn VARCHAR(500),
    ip_address VARCHAR(45),
    mac_address VARCHAR(17),

    -- Информация о системе
    os_version VARCHAR(100),
    os_build VARCHAR(50),
    os_architecture VARCHAR(10), -- x64, x86

    -- Домен Active Directory
    domain VARCHAR(255),
    organizational_unit VARCHAR(500),

    -- Оборудование
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    serial_number VARCHAR(100),
    cpu_model VARCHAR(200),
    cpu_cores INTEGER,
    total_ram_mb BIGINT,
    total_disk_gb BIGINT,

    -- Статус агента
    agent_version VARCHAR(20),
    status VARCHAR(20) DEFAULT 'offline', -- online, offline, error, installing
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_inventory TIMESTAMP,
    last_reboot TIMESTAMP,

    -- Метаданные
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    configuration JSONB, -- JSON конфиг
    tags JSONB, -- JSON array тегов
    location VARCHAR(200), -- Физическое расположение
    owner VARCHAR(200), -- Ответственный
    criticality_level VARCHAR(20) DEFAULT 'medium', -- critical, high, medium, low

    CONSTRAINT ck_agents_status CHECK (status IN ('online', 'offline', 'error', 'installing')),
    CONSTRAINT ck_agents_criticality CHECK (criticality_level IN ('critical', 'high', 'medium', 'low'))
);

-- Индексы для агентов
CREATE UNIQUE INDEX idx_agents_hostname ON assets.agents(hostname);
CREATE INDEX idx_agents_status ON assets.agents(status, last_seen DESC);
CREATE INDEX idx_agents_last_seen ON assets.agents(last_seen DESC);
CREATE INDEX idx_agents_domain ON assets.agents(domain) WHERE domain IS NOT NULL;

COMMENT ON TABLE assets.agents IS 'Windows агенты и хосты под мониторингом';

-- =====================================================================
-- ТАБЛИЦА СЕССИЙ API
-- =====================================================================

CREATE TABLE config.sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES config.users(user_id),
    token VARCHAR(500) NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT ck_sessions_expires CHECK (expires_at > created_at)
);

CREATE UNIQUE INDEX idx_sessions_token ON config.sessions(token) WHERE is_active = TRUE;
CREATE INDEX idx_sessions_user_id ON config.sessions(user_id, created_at DESC);
CREATE INDEX idx_sessions_expires ON config.sessions(expires_at) WHERE is_active = TRUE;

-- =====================================================================
-- ТАБЛИЦА НАСТРОЕК СИСТЕМЫ
-- =====================================================================

CREATE TABLE config.settings (
    setting_key VARCHAR(100) PRIMARY KEY,
    setting_value JSONB,
    description VARCHAR(500),
    is_encrypted BOOLEAN DEFAULT FALSE,
    updated_by INTEGER REFERENCES config.users(user_id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================================
-- ПРОГРАММНОЕ ОБЕСПЕЧЕНИЕ
-- =====================================================================

-- Таблица категорий программного обеспечения
CREATE TABLE assets.software_categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(500),
    default_risk_level VARCHAR(20) DEFAULT 'low', -- critical, high, medium, low
    requires_license BOOLEAN DEFAULT FALSE,
    requires_approval BOOLEAN DEFAULT FALSE,
    CONSTRAINT ck_software_categories_risk CHECK (default_risk_level IN ('critical', 'high', 'medium', 'low'))
);

-- Справочник установленного ПО (уникальные продукты)
CREATE TABLE assets.software_registry (
    software_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255), -- Очищенное название для группировки
    publisher VARCHAR(255),
    category_id INTEGER REFERENCES assets.software_categories(category_id),

    -- Классификация
    is_allowed BOOLEAN DEFAULT TRUE, -- Разрешено ли использование
    is_forbidden BOOLEAN DEFAULT FALSE, -- Запрещено политикой безопасности
    requires_license BOOLEAN DEFAULT FALSE,
    risk_level VARCHAR(20) DEFAULT 'low',

    -- MITRE ATT&CK (если ПО может использоваться в атаках)
    mitre_relevant BOOLEAN DEFAULT FALSE,
    mitre_techniques JSONB, -- JSON array

    -- Метаданные
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,

    CONSTRAINT ck_software_registry_risk CHECK (risk_level IN ('critical', 'high', 'medium', 'low'))
);

CREATE INDEX idx_software_registry_name ON assets.software_registry(name);
CREATE INDEX idx_software_registry_normalized ON assets.software_registry(normalized_name);
CREATE INDEX idx_software_registry_category ON assets.software_registry(category_id);
CREATE INDEX idx_software_registry_forbidden ON assets.software_registry(is_forbidden) WHERE is_forbidden = TRUE;

-- Таблица установленного ПО на хостах
CREATE TABLE assets.installed_software (
    install_id BIGSERIAL PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES assets.agents(agent_id),
    software_id INTEGER REFERENCES assets.software_registry(software_id),

    -- Информация об установке
    name VARCHAR(255) NOT NULL, -- Оригинальное название из реестра
    version VARCHAR(100),
    publisher VARCHAR(255),
    install_date DATE,
    install_location VARCHAR(1000),
    uninstall_string VARCHAR(1000),
    estimated_size_kb BIGINT,

    -- Статус
    is_active BOOLEAN DEFAULT TRUE, -- false если ПО было удалено
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    removed_at TIMESTAMP,

    -- Для отслеживания изменений
    CONSTRAINT uq_installed_software_agent_name_version UNIQUE (agent_id, name, version)
);

CREATE INDEX idx_installed_software_agent ON assets.installed_software(agent_id, is_active);
CREATE INDEX idx_installed_software_software ON assets.installed_software(software_id);
CREATE INDEX idx_installed_software_active ON assets.installed_software(is_active, last_seen_at DESC);

-- =====================================================================
-- СЛУЖБЫ WINDOWS
-- =====================================================================

CREATE TABLE assets.windows_services (
    service_id BIGSERIAL PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES assets.agents(agent_id),

    service_name VARCHAR(255) NOT NULL,
    display_name VARCHAR(500),
    status VARCHAR(20), -- running, stopped
    start_type VARCHAR(20), -- auto, manual, disabled
    service_account VARCHAR(255),
    executable_path VARCHAR(1000),

    is_active BOOLEAN DEFAULT TRUE,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_windows_services_status CHECK (status IN ('running', 'stopped', 'paused')),
    CONSTRAINT ck_windows_services_start_type CHECK (start_type IN ('auto', 'manual', 'disabled', 'automatic_delayed'))
);

CREATE INDEX idx_windows_services_agent ON assets.windows_services(agent_id, is_active);
CREATE INDEX idx_windows_services_running ON assets.windows_services(status) WHERE status = 'running';

-- =====================================================================
-- ИСТОРИЯ ИЗМЕНЕНИЙ В АКТИВАХ (ДЛЯ АУДИТА ЦБ)
-- =====================================================================

CREATE TABLE assets.asset_changes (
    change_id BIGSERIAL PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES assets.agents(agent_id),
    change_type VARCHAR(50) NOT NULL, -- software_installed, software_removed, service_added, etc
    change_details JSONB, -- JSON с деталями
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    severity SMALLINT DEFAULT 0, -- 0-info, 1-low, 2-medium, 3-high, 4-critical

    CONSTRAINT ck_asset_changes_type CHECK (change_type IN (
        'software_installed', 'software_removed', 'software_updated',
        'service_added', 'service_removed', 'service_changed',
        'config_changed', 'user_added', 'user_removed'
    ))
);

CREATE INDEX idx_asset_changes_agent ON assets.asset_changes(agent_id, detected_at DESC);
CREATE INDEX idx_asset_changes_type ON assets.asset_changes(change_type, detected_at DESC);
CREATE INDEX idx_asset_changes_critical ON assets.asset_changes(severity, detected_at DESC) WHERE severity >= 3;

-- =====================================================================
-- ОСНОВНАЯ ТАБЛИЦА СОБЫТИЙ БЕЗОПАСНОСТИ (С TIMESCALEDB)
-- =====================================================================

CREATE TABLE security_events.events (
    event_id BIGSERIAL,
    event_guid UUID DEFAULT gen_random_uuid(), -- Для гарантированной уникальности
    agent_id UUID NOT NULL,

    -- Временные метки
    event_time TIMESTAMP NOT NULL, -- Время события на источнике
    received_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Время получения сервером
    processed_time TIMESTAMP, -- Время обработки AI

    -- Источник события
    source_type VARCHAR(50) NOT NULL, -- windows_security, windows_system, sysmon, powershell, defender
    event_code INTEGER,
    channel VARCHAR(100),
    provider VARCHAR(100),
    computer VARCHAR(255), -- Имя хоста из события

    -- Нормализованные поля (ECS-подобные)
    severity SMALLINT DEFAULT 0, -- 0-info, 1-low, 2-medium, 3-high, 4-critical
    category VARCHAR(50), -- authentication, process, network, file, registry, service
    action VARCHAR(50), -- success, failure, created, deleted, modified, connected
    outcome VARCHAR(20), -- success, failure, unknown

    -- Субъект (кто выполнил действие)
    subject_user VARCHAR(200),
    subject_domain VARCHAR(100),
    subject_sid VARCHAR(100),
    subject_logon_id VARCHAR(50),

    -- Объект (над чем выполнено действие)
    target_user VARCHAR(200),
    target_domain VARCHAR(100),
    target_sid VARCHAR(100),
    target_host VARCHAR(255),
    target_ip VARCHAR(45),
    target_port INTEGER,

    -- Процесс
    process_name VARCHAR(500),
    process_id INTEGER,
    process_path VARCHAR(1000),
    process_command_line TEXT,
    process_hash VARCHAR(128), -- SHA256

    -- Родительский процесс
    parent_process_name VARCHAR(500),
    parent_process_id INTEGER,
    parent_process_path VARCHAR(1000),
    parent_process_command_line TEXT,

    -- Сеть
    source_ip VARCHAR(45),
    source_port INTEGER,
    source_hostname VARCHAR(255),
    destination_ip VARCHAR(45),
    destination_port INTEGER,
    destination_hostname VARCHAR(255),
    protocol VARCHAR(20), -- TCP, UDP, ICMP

    -- DNS (для Event ID 22 Sysmon)
    dns_query VARCHAR(500),
    dns_response JSONB, -- JSON array IP-адресов

    -- Файл
    file_path VARCHAR(1000),
    file_name VARCHAR(255),
    file_hash VARCHAR(128), -- SHA256
    file_extension VARCHAR(20),
    file_size BIGINT,

    -- Реестр
    registry_path VARCHAR(1000),
    registry_key VARCHAR(500),
    registry_value TEXT,
    registry_value_type VARCHAR(50),

    -- Дополнительные поля
    message TEXT, -- Описание события
    raw_event JSONB, -- Исходное событие в JSON
    tags JSONB, -- JSON array тегов

    -- MITRE ATT&CK маппинг
    mitre_attack_tactic VARCHAR(50),
    mitre_attack_technique VARCHAR(20),
    mitre_attack_subtechnique VARCHAR(30),

    -- AI-анализ (DeepSeek / Yandex GPT)
    ai_processed BOOLEAN DEFAULT FALSE,
    ai_score NUMERIC(5,2), -- 0.00 - 100.00
    ai_category VARCHAR(100),
    ai_description VARCHAR(1000),
    ai_confidence NUMERIC(5,2), -- Уверенность AI в оценке
    ai_is_attack BOOLEAN,

    -- Геолокация (для внешних IP)
    geo_country CHAR(2), -- ISO код
    geo_city VARCHAR(100),

    -- Ограничения
    CONSTRAINT ck_events_severity CHECK (severity BETWEEN 0 AND 4),
    CONSTRAINT ck_events_outcome CHECK (outcome IN ('success', 'failure', 'unknown'))
);

-- Создаём первичный ключ (будет автоматически создан индекс)
-- В TimescaleDB нельзя использовать составной PK с временем, так что используем event_id
CREATE UNIQUE INDEX idx_events_pkey ON security_events.events(event_time, event_id);

-- =====================================================================
-- TIMESCALEDB: КОНВЕРТАЦИЯ В HYPERTABLE
-- =====================================================================

-- Конвертируем таблицу событий в TimescaleDB hypertable
-- Это включает автоматическое партиционирование по времени
SELECT create_hypertable(
    'security_events.events',
    'event_time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Добавляем compression policy (сжатие старых данных через 7 дней)
ALTER TABLE security_events.events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'computer, event_code',
    timescaledb.compress_orderby = 'event_time DESC'
);

SELECT add_compression_policy('security_events.events', INTERVAL '7 days');

-- Retention policy: удаление данных старше 5 лет (требование ЦБ - хранение 5 лет)
-- ВАЖНО: для production установите INTERVAL '5 years'
-- SELECT add_retention_policy('security_events.events', INTERVAL '5 years');

-- =====================================================================
-- ИНДЕКСЫ ДЛЯ ТАБЛИЦЫ СОБЫТИЙ
-- =====================================================================

-- BRIN индексы для time-range queries (очень быстрые и компактные)
CREATE INDEX idx_events_time_brin ON security_events.events USING BRIN (event_time) WITH (pages_per_range = 128);

-- B-tree индексы для точных поисков и фильтрации
CREATE INDEX idx_events_agent_id ON security_events.events(agent_id, event_time DESC);
CREATE INDEX idx_events_severity ON security_events.events(severity, event_time DESC) WHERE severity >= 3;
CREATE INDEX idx_events_category ON security_events.events(category, event_time DESC) WHERE category IS NOT NULL;
CREATE INDEX idx_events_subject_user ON security_events.events(subject_user, event_time DESC) WHERE subject_user IS NOT NULL;
CREATE INDEX idx_events_source_ip ON security_events.events(source_ip, event_time DESC) WHERE source_ip IS NOT NULL;
CREATE INDEX idx_events_dest_ip ON security_events.events(destination_ip, event_time DESC) WHERE destination_ip IS NOT NULL;
CREATE INDEX idx_events_process_name ON security_events.events(process_name, event_time DESC) WHERE process_name IS NOT NULL;
CREATE INDEX idx_events_ai_processed ON security_events.events(ai_processed, event_time) WHERE ai_processed = FALSE;
CREATE INDEX idx_events_mitre ON security_events.events(mitre_attack_tactic, mitre_attack_technique, event_time DESC) WHERE mitre_attack_tactic IS NOT NULL;
CREATE UNIQUE INDEX idx_events_event_guid ON security_events.events(event_guid);

-- GIN index для JSONB полей (поиск по JSON)
CREATE INDEX idx_events_raw_event_gin ON security_events.events USING GIN (raw_event);
CREATE INDEX idx_events_tags_gin ON security_events.events USING GIN (tags);

COMMENT ON TABLE security_events.events IS 'Основная таблица событий безопасности. TimescaleDB hypertable с автоматическим партиционированием по дням. Хранение: минимум 5 лет (требование ЦБ 683-П).';

-- =====================================================================
-- ПРАВИЛА ДЕТЕКЦИИ
-- =====================================================================

CREATE TABLE config.detection_rules (
    rule_id SERIAL PRIMARY KEY,
    rule_name VARCHAR(200) NOT NULL UNIQUE,
    description VARCHAR(1000),
    is_enabled BOOLEAN DEFAULT TRUE,

    -- Приоритет
    severity SMALLINT DEFAULT 2, -- severity алерта при срабатывании
    priority INTEGER DEFAULT 50, -- Порядок применения (меньше = раньше)

    -- Тип правила
    rule_type VARCHAR(20) NOT NULL, -- simple, threshold, correlation, sigma, ml
    rule_logic JSONB NOT NULL, -- JSON с условиями или Sigma YAML

    -- Временные параметры для threshold/correlation
    time_window_minutes INTEGER,
    threshold_count INTEGER,
    group_by_fields JSONB, -- JSON array полей для группировки

    -- Условия
    source_types JSONB, -- JSON array типов источников
    event_codes JSONB, -- JSON array кодов событий
    categories JSONB, -- JSON array категорий

    -- Действия при срабатывании
    actions JSONB, -- JSON: [{type: "alert", ...}, {type: "notify", ...}]
    auto_escalate BOOLEAN DEFAULT FALSE, -- Автоматически создавать инцидент

    -- MITRE ATT&CK маппинг
    mitre_attack_tactic VARCHAR(50),
    mitre_attack_technique VARCHAR(20),
    mitre_attack_subtechnique VARCHAR(30),

    -- Исключения (whitelist)
    exceptions JSONB, -- JSON с условиями исключений

    -- Статистика
    total_matches BIGINT DEFAULT 0,
    false_positives INTEGER DEFAULT 0,
    last_match TIMESTAMP,

    -- Метаданные
    created_by INTEGER REFERENCES config.users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES config.users(user_id),
    updated_at TIMESTAMP,
    tags JSONB, -- JSON array

    CONSTRAINT ck_detection_rules_type CHECK (rule_type IN ('simple', 'threshold', 'correlation', 'sigma', 'ml')),
    CONSTRAINT ck_detection_rules_severity CHECK (severity BETWEEN 0 AND 4)
);

CREATE INDEX idx_detection_rules_enabled ON config.detection_rules(is_enabled, priority) WHERE is_enabled = TRUE;
CREATE INDEX idx_detection_rules_mitre ON config.detection_rules(mitre_attack_tactic, mitre_attack_technique);

-- =====================================================================
-- АЛЕРТЫ (СРАБОТАВШИЕ ПРАВИЛА)
-- =====================================================================

CREATE TABLE incidents.alerts (
    alert_id BIGSERIAL PRIMARY KEY,
    alert_guid UUID DEFAULT gen_random_uuid(),
    rule_id INTEGER REFERENCES config.detection_rules(rule_id),

    -- Классификация
    severity SMALLINT NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    category VARCHAR(50), -- intrusion, malware, policy_violation, anomaly, recon

    -- Связанные события
    event_ids JSONB, -- JSON array of EventIds
    event_count INTEGER DEFAULT 1,
    first_event_time TIMESTAMP,
    last_event_time TIMESTAMP,

    -- Контекст (из событий)
    agent_id UUID REFERENCES assets.agents(agent_id),
    hostname VARCHAR(255),
    username VARCHAR(200),
    source_ip VARCHAR(45),
    target_ip VARCHAR(45),
    process_name VARCHAR(500),

    -- MITRE ATT&CK
    mitre_attack_tactic VARCHAR(50),
    mitre_attack_technique VARCHAR(20),
    mitre_attack_subtechnique VARCHAR(30),

    -- Статус работы
    status VARCHAR(20) DEFAULT 'new', -- new, acknowledged, investigating, resolved, false_positive
    assigned_to INTEGER REFERENCES config.users(user_id),
    priority SMALLINT DEFAULT 2, -- 1-low, 2-medium, 3-high, 4-critical

    -- AI-анализ
    ai_analysis JSONB, -- JSON с анализом от AI
    ai_recommendations JSONB, -- Рекомендации по реагированию
    ai_confidence NUMERIC(5,2),

    -- Инцидент
    incident_id INTEGER, -- Связь с инцидентом (может быть NULL)

    -- Временные метки
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP,
    updated_at TIMESTAMP,

    -- Комментарии и история
    comments JSONB, -- JSON array комментариев
    actions_taken JSONB, -- JSON array предпринятых действий

    -- Для отчётов ЦБ
    operational_risk_category VARCHAR(100), -- Категория операционного риска (716-П)
    estimated_damage_rub NUMERIC(15,2), -- Оценка ущерба
    is_reportable BOOLEAN DEFAULT TRUE, -- Требует отчёта регулятору

    CONSTRAINT ck_alerts_severity CHECK (severity BETWEEN 0 AND 4),
    CONSTRAINT ck_alerts_status CHECK (status IN ('new', 'acknowledged', 'investigating', 'resolved', 'false_positive')),
    CONSTRAINT ck_alerts_priority CHECK (priority BETWEEN 1 AND 4)
);

-- Индексы для алертов
CREATE INDEX idx_alerts_status ON incidents.alerts(status, created_at DESC);
CREATE INDEX idx_alerts_severity ON incidents.alerts(severity DESC, created_at DESC);
CREATE INDEX idx_alerts_agent_id ON incidents.alerts(agent_id, created_at DESC);
CREATE INDEX idx_alerts_assigned_to ON incidents.alerts(assigned_to, status);
CREATE INDEX idx_alerts_incident ON incidents.alerts(incident_id) WHERE incident_id IS NOT NULL;
CREATE INDEX idx_alerts_unresolved ON incidents.alerts(created_at DESC) WHERE status NOT IN ('resolved', 'false_positive');
CREATE UNIQUE INDEX idx_alerts_alert_guid ON incidents.alerts(alert_guid);

-- =====================================================================
-- ИНЦИДЕНТЫ (ГРУППЫ СВЯЗАННЫХ АЛЕРТОВ)
-- =====================================================================

CREATE TABLE incidents.incidents (
    incident_id SERIAL PRIMARY KEY,
    incident_guid UUID DEFAULT gen_random_uuid(),

    -- Основная информация
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity SMALLINT NOT NULL, -- Максимальный severity среди алертов
    category VARCHAR(50), -- intrusion, malware, data_breach, policy_violation, anomaly

    -- Связанные алерты
    alert_count INTEGER DEFAULT 0,
    event_count INTEGER DEFAULT 0,

    -- Затронутые системы
    affected_agents JSONB, -- JSON array AgentIds
    affected_users JSONB, -- JSON array usernames
    affected_assets INTEGER DEFAULT 0, -- Количество затронутых хостов

    -- Таймлайн
    start_time TIMESTAMP, -- Время первого события
    end_time TIMESTAMP, -- Время последнего события
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Когда инцидент был обнаружен

    -- Статус работы
    status VARCHAR(20) DEFAULT 'open', -- open, investigating, contained, resolved, closed
    assigned_to INTEGER REFERENCES config.users(user_id),
    priority SMALLINT DEFAULT 2,

    -- AI-анализ инцидента
    ai_summary TEXT, -- Краткое описание
    ai_timeline JSONB, -- JSON timeline событий
    ai_root_cause TEXT, -- Предполагаемая причина
    ai_recommendations JSONB, -- Рекомендации
    ai_impact_assessment TEXT, -- Оценка воздействия

    -- MITRE ATT&CK (может быть несколько тактик/техник)
    mitre_attack_tactics JSONB, -- JSON array
    mitre_attack_techniques JSONB, -- JSON array
    attack_chain JSONB, -- JSON описание цепочки атаки

    -- Реагирование
    containment_actions JSONB, -- JSON array действий по сдерживанию
    remediation_actions JSONB, -- JSON array действий по устранению
    lessons_learned TEXT, -- Выводы

    -- Для отчётов ЦБ РФ
    operational_risk_category VARCHAR(100), -- 716-П
    estimated_damage_rub NUMERIC(15,2),
    actual_damage_rub NUMERIC(15,2),
    is_reported_to_cbr BOOLEAN DEFAULT FALSE, -- Отчитались ли в ЦБ
    cbr_report_date TIMESTAMP,
    cbr_incident_number VARCHAR(100), -- Номер инцидента из ФинЦЕРТ

    -- Временные метки
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    closed_at TIMESTAMP,

    -- Комментарии и история
    work_log JSONB, -- JSON array записей о работе

    CONSTRAINT ck_incidents_severity CHECK (severity BETWEEN 0 AND 4),
    CONSTRAINT ck_incidents_status CHECK (status IN ('open', 'investigating', 'contained', 'resolved', 'closed')),
    CONSTRAINT ck_incidents_priority CHECK (priority BETWEEN 1 AND 4)
);

-- Индексы для инцидентов
CREATE INDEX idx_incidents_status ON incidents.incidents(status, severity DESC, created_at DESC);
CREATE INDEX idx_incidents_severity ON incidents.incidents(severity DESC, created_at DESC);
CREATE INDEX idx_incidents_assigned_to ON incidents.incidents(assigned_to, status);
CREATE INDEX idx_incidents_cbr_reportable ON incidents.incidents(is_reported_to_cbr, created_at DESC) WHERE is_reported_to_cbr = FALSE;
CREATE UNIQUE INDEX idx_incidents_incident_guid ON incidents.incidents(incident_guid);

-- Обновление связи алертов с инцидентами
ALTER TABLE incidents.alerts
ADD CONSTRAINT fk_alerts_incident FOREIGN KEY (incident_id) REFERENCES incidents.incidents(incident_id);

-- =====================================================================
-- ОТЧЁТЫ ДЛЯ ЦБ РФ И КОМПЛАЕНСА
-- =====================================================================

-- История экспортов для регулятора
CREATE TABLE compliance.cbr_reports (
    report_id SERIAL PRIMARY KEY,
    report_guid UUID DEFAULT gen_random_uuid(),

    -- Тип отчёта
    report_type VARCHAR(50) NOT NULL, -- form_0403203, fincert_notification, operational_risk, incident_report
    report_period_start TIMESTAMP,
    report_period_end TIMESTAMP,

    -- Содержимое
    report_data JSONB, -- JSON с данными отчёта
    report_format VARCHAR(20), -- json, xml, excel, pdf
    file_content BYTEA, -- Бинарный файл для Excel/PDF
    file_name VARCHAR(255),
    file_hash VARCHAR(64), -- SHA256 для контроля целостности

    -- Связанные сущности
    incident_ids JSONB, -- JSON array
    alert_ids JSONB, -- JSON array

    -- Статус
    status VARCHAR(20) DEFAULT 'draft', -- draft, ready, sent, confirmed
    generated_by INTEGER REFERENCES config.users(user_id),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    sent_by INTEGER REFERENCES config.users(user_id),

    -- Метаданные
    notes TEXT,

    CONSTRAINT ck_cbr_reports_type CHECK (report_type IN ('form_0403203', 'fincert_notification', 'operational_risk', 'incident_report', 'audit_export')),
    CONSTRAINT ck_cbr_reports_status CHECK (status IN ('draft', 'ready', 'sent', 'confirmed'))
);

CREATE INDEX idx_cbr_reports_type ON compliance.cbr_reports(report_type, generated_at DESC);
CREATE INDEX idx_cbr_reports_status ON compliance.cbr_reports(status);
CREATE UNIQUE INDEX idx_cbr_reports_report_guid ON compliance.cbr_reports(report_guid);

COMMENT ON TABLE compliance.cbr_reports IS 'История экспортов данных для ЦБ РФ. Хранит отчёты по формам 683-П, 716-П, 747-П с контрольными суммами.';

-- =====================================================================
-- АУДИТ ИЗМЕНЕНИЙ ДЛЯ СООТВЕТСТВИЯ ГОСТ Р 57580
-- =====================================================================

CREATE TABLE compliance.audit_log (
    log_id BIGSERIAL PRIMARY KEY,
    log_guid UUID DEFAULT gen_random_uuid(),

    -- Кто
    user_id INTEGER REFERENCES config.users(user_id),
    username VARCHAR(100),

    -- Что
    action VARCHAR(50) NOT NULL, -- login, logout, create, update, delete, export, view
    object_type VARCHAR(50), -- event, alert, incident, rule, user, agent, setting
    object_id VARCHAR(100),
    object_name VARCHAR(255),

    -- Детали
    details JSONB, -- JSON с подробностями действия
    old_value JSONB, -- Старое значение (для update)
    new_value JSONB, -- Новое значение (для update)

    -- Контекст
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    session_id UUID,

    -- Результат
    outcome VARCHAR(20) DEFAULT 'success', -- success, failure
    error_message VARCHAR(1000),

    -- Время
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_audit_log_action CHECK (action IN (
        'login', 'logout', 'login_failed',
        'create', 'update', 'delete', 'view',
        'export', 'import',
        'rule_triggered', 'alert_created', 'incident_escalated',
        'setting_changed', 'user_created', 'user_deleted',
        'report_generated', 'report_sent'
    )),
    CONSTRAINT ck_audit_log_outcome CHECK (outcome IN ('success', 'failure'))
);

-- Индексы для аудит лога
CREATE INDEX idx_audit_log_user_id ON compliance.audit_log(user_id, created_at DESC);
CREATE INDEX idx_audit_log_action ON compliance.audit_log(action, created_at DESC);
CREATE INDEX idx_audit_log_object_type ON compliance.audit_log(object_type, object_id, created_at DESC);
CREATE INDEX idx_audit_log_created_at ON compliance.audit_log(created_at DESC);
CREATE UNIQUE INDEX idx_audit_log_log_guid ON compliance.audit_log(log_guid);

COMMENT ON TABLE compliance.audit_log IS 'Журнал аудита всех действий пользователей системы (ГОСТ Р 57580).';

-- =====================================================================
-- PHASE 1: PRODUCTION MVP FEATURES
-- =====================================================================

-- Создание схемы для enrichment
CREATE SCHEMA IF NOT EXISTS enrichment;

-- ---------------------------------------------------------------------
-- SystemSettings - Хранение настроек системы
-- ---------------------------------------------------------------------
CREATE TABLE config.system_settings (
    setting_id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    setting_type VARCHAR(50) DEFAULT 'string', -- string, boolean, integer, json
    category VARCHAR(50), -- freescout, email, ai, threat_intel, system
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_system_settings_key ON config.system_settings(setting_key);
CREATE INDEX idx_system_settings_category ON config.system_settings(category);

COMMENT ON TABLE config.system_settings IS 'Настройки системы (FreeScout, Email, AI, Threat Intel)';

-- ---------------------------------------------------------------------
-- SavedSearches - Сохранённые поисковые запросы
-- ---------------------------------------------------------------------
CREATE TABLE config.saved_searches (
    saved_search_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    search_type VARCHAR(20) NOT NULL, -- events, alerts, incidents
    filters TEXT NOT NULL, -- JSON string with filter parameters
    user_id INTEGER NOT NULL REFERENCES config.users(user_id) ON DELETE CASCADE,
    is_shared BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    CONSTRAINT ck_saved_searches_search_type
        CHECK (search_type IN ('events', 'alerts', 'incidents'))
);

CREATE INDEX idx_saved_searches_name ON config.saved_searches(name);
CREATE INDEX idx_saved_searches_search_type ON config.saved_searches(search_type);
CREATE INDEX idx_saved_searches_user_id ON config.saved_searches(user_id);
CREATE INDEX idx_saved_searches_is_shared ON config.saved_searches(is_shared);
CREATE INDEX idx_saved_searches_created_at ON config.saved_searches(created_at DESC);

COMMENT ON TABLE config.saved_searches IS 'Сохранённые поисковые запросы пользователей';

-- ---------------------------------------------------------------------
-- FreeScoutTickets - Связь с тикетами FreeScout
-- ---------------------------------------------------------------------
CREATE TABLE incidents.freescout_tickets (
    ticket_id SERIAL PRIMARY KEY,
    freescout_conversation_id INTEGER NOT NULL UNIQUE,
    freescout_conversation_number INTEGER NOT NULL,
    alert_id INTEGER REFERENCES incidents.alerts(alert_id) ON DELETE SET NULL,
    incident_id INTEGER REFERENCES incidents.incidents(incident_id) ON DELETE SET NULL,
    ticket_url VARCHAR(500),
    ticket_status VARCHAR(20), -- active, closed, spam
    ticket_subject VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    last_synced_at TIMESTAMP
);

CREATE INDEX idx_freescout_tickets_conversation_id ON incidents.freescout_tickets(freescout_conversation_id);
CREATE INDEX idx_freescout_tickets_alert_id ON incidents.freescout_tickets(alert_id);
CREATE INDEX idx_freescout_tickets_incident_id ON incidents.freescout_tickets(incident_id);
CREATE INDEX idx_freescout_tickets_status ON incidents.freescout_tickets(ticket_status);

COMMENT ON TABLE incidents.freescout_tickets IS 'Связь алертов/инцидентов с тикетами в FreeScout';

-- ---------------------------------------------------------------------
-- EmailNotifications - Журнал отправленных email уведомлений
-- ---------------------------------------------------------------------
CREATE TABLE config.email_notifications (
    notification_id SERIAL PRIMARY KEY,
    recipient_email VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body TEXT,
    alert_id INTEGER REFERENCES incidents.alerts(alert_id) ON DELETE SET NULL,
    incident_id INTEGER REFERENCES incidents.incidents(incident_id) ON DELETE SET NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending', -- pending, sent, failed
    error_message TEXT,
    smtp_message_id VARCHAR(255)
);

CREATE INDEX idx_email_notifications_recipient ON config.email_notifications(recipient_email, sent_at DESC);
CREATE INDEX idx_email_notifications_alert_id ON config.email_notifications(alert_id);
CREATE INDEX idx_email_notifications_incident_id ON config.email_notifications(incident_id);
CREATE INDEX idx_email_notifications_sent_at ON config.email_notifications(sent_at DESC);
CREATE INDEX idx_email_notifications_status ON config.email_notifications(status);

COMMENT ON TABLE config.email_notifications IS 'Журнал отправленных email уведомлений';

-- ---------------------------------------------------------------------
-- ThreatIntelligence - Кэш результатов threat intelligence
-- ---------------------------------------------------------------------
CREATE TABLE enrichment.threat_intelligence (
    intel_id SERIAL PRIMARY KEY,
    lookup_type VARCHAR(20) NOT NULL, -- ip, file_hash, domain
    lookup_value VARCHAR(255) NOT NULL,
    source VARCHAR(50) NOT NULL, -- virustotal, abuseipdb, misp, etc.
    result JSONB NOT NULL, -- результат запроса в JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL, -- кэш истекает через 24 часа

    CONSTRAINT ck_threat_intel_lookup_type
        CHECK (lookup_type IN ('ip', 'file_hash', 'domain', 'url'))
);

-- Уникальный индекс для предотвращения дублей (один тип запроса + значение + источник)
CREATE UNIQUE INDEX idx_threat_intel_unique ON enrichment.threat_intelligence(lookup_type, lookup_value, source);
CREATE INDEX idx_threat_intel_lookup_value ON enrichment.threat_intelligence(lookup_value);
CREATE INDEX idx_threat_intel_source ON enrichment.threat_intelligence(source);
CREATE INDEX idx_threat_intel_created_at ON enrichment.threat_intelligence(created_at DESC);
CREATE INDEX idx_threat_intel_expires_at ON enrichment.threat_intelligence(expires_at);

COMMENT ON TABLE enrichment.threat_intelligence IS 'Кэш результатов threat intelligence (VirusTotal, AbuseIPDB) с TTL 24 часа';

-- =====================================================================
-- SOAR AUTOMATION SCHEMA
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS automation;

-- Playbook Actions - Individual steps that can be executed
CREATE TABLE automation.playbook_actions (
    action_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    action_type VARCHAR(50) NOT NULL,
    config JSONB NOT NULL,
    timeout_seconds INTEGER DEFAULT 300 NOT NULL,
    retry_count INTEGER DEFAULT 0 NOT NULL,
    retry_delay_seconds INTEGER DEFAULT 60 NOT NULL,
    continue_on_failure BOOLEAN DEFAULT FALSE NOT NULL,
    rollback_action_id INTEGER REFERENCES automation.playbook_actions(action_id),
    is_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    created_by INTEGER REFERENCES config.users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

CREATE INDEX idx_playbook_actions_type ON automation.playbook_actions(action_type);
CREATE INDEX idx_playbook_actions_enabled ON automation.playbook_actions(is_enabled) WHERE is_enabled = TRUE AND is_deleted = FALSE;

COMMENT ON TABLE automation.playbook_actions IS 'SOAR playbook actions - individual executable steps';

-- Playbooks - Automated response workflows
CREATE TABLE automation.playbooks (
    playbook_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    trigger_on_severity INTEGER[],
    trigger_on_mitre_tactic VARCHAR(100)[],
    trigger_on_rule_name VARCHAR(255)[],
    trigger_conditions JSONB,
    action_ids INTEGER[],
    requires_approval BOOLEAN DEFAULT FALSE NOT NULL,
    auto_approve_for_severity INTEGER[],
    is_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    created_by INTEGER REFERENCES config.users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP,
    last_executed_at TIMESTAMP,
    execution_count INTEGER DEFAULT 0 NOT NULL,
    success_count INTEGER DEFAULT 0 NOT NULL,
    failure_count INTEGER DEFAULT 0 NOT NULL,
    tags VARCHAR(50)[]
);

CREATE INDEX idx_playbooks_enabled ON automation.playbooks(is_enabled) WHERE is_enabled = TRUE AND is_deleted = FALSE;
CREATE INDEX idx_playbooks_severity ON automation.playbooks USING GIN (trigger_on_severity);

COMMENT ON TABLE automation.playbooks IS 'SOAR playbooks - automated response workflows';

-- Playbook Executions - History of playbook runs
CREATE TABLE automation.playbook_executions (
    execution_id SERIAL PRIMARY KEY,
    playbook_id INTEGER NOT NULL REFERENCES automation.playbooks(playbook_id),
    alert_id BIGINT REFERENCES incidents.alerts(alert_id),
    incident_id INTEGER REFERENCES incidents.incidents(incident_id),
    triggered_by_user_id INTEGER REFERENCES config.users(user_id),
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    requires_approval BOOLEAN DEFAULT FALSE NOT NULL,
    approved_by_user_id INTEGER REFERENCES config.users(user_id),
    approved_at TIMESTAMP,
    approval_comment TEXT,
    success BOOLEAN,
    error_message TEXT,
    execution_log JSONB,
    rolled_back BOOLEAN DEFAULT FALSE NOT NULL,
    rollback_execution_id INTEGER REFERENCES automation.playbook_executions(execution_id),
    rollback_reason TEXT,

    CONSTRAINT ck_playbook_executions_status CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled', 'awaiting_approval', 'approved', 'rejected', 'rolled_back'))
);

CREATE INDEX idx_playbook_executions_playbook ON automation.playbook_executions(playbook_id, started_at DESC);
CREATE INDEX idx_playbook_executions_status ON automation.playbook_executions(status, started_at DESC);
CREATE INDEX idx_playbook_executions_alert ON automation.playbook_executions(alert_id) WHERE alert_id IS NOT NULL;

COMMENT ON TABLE automation.playbook_executions IS 'SOAR playbook execution history';

-- Action Results - Results of individual action executions
CREATE TABLE automation.action_results (
    result_id SERIAL PRIMARY KEY,
    execution_id INTEGER NOT NULL REFERENCES automation.playbook_executions(execution_id),
    action_id INTEGER NOT NULL REFERENCES automation.playbook_actions(action_id),
    sequence_number INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    result JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0 NOT NULL,
    output_variables JSONB,

    CONSTRAINT ck_action_results_status CHECK (status IN ('pending', 'running', 'success', 'failed', 'skipped', 'timeout'))
);

CREATE INDEX idx_action_results_execution ON automation.action_results(execution_id, sequence_number);
CREATE INDEX idx_action_results_action ON automation.action_results(action_id);

COMMENT ON TABLE automation.action_results IS 'SOAR action execution results';

-- =====================================================================
-- ЗАВЕРШЕНИЕ
-- =====================================================================

-- Выводим статистику созданных объектов
DO $$
DECLARE
    table_count INTEGER;
    index_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count FROM information_schema.tables
    WHERE table_schema IN ('security_events', 'config', 'incidents', 'assets', 'compliance', 'enrichment', 'automation');

    SELECT COUNT(*) INTO index_count FROM pg_indexes
    WHERE schemaname IN ('security_events', 'config', 'incidents', 'assets', 'compliance', 'enrichment', 'automation');

    RAISE NOTICE 'Схема базы данных SIEM_DB успешно создана!';
    RAISE NOTICE 'Создано:';
    RAISE NOTICE '  - 7 схем (security_events, config, incidents, assets, compliance, enrichment, automation)';
    RAISE NOTICE '  - % таблиц с индексами и ограничениями', table_count;
    RAISE NOTICE '  - % индексов', index_count;
    RAISE NOTICE '  - TimescaleDB hypertable для событий с автоматическим партиционированием';
    RAISE NOTICE '  - BRIN индексы для time-range queries';
    RAISE NOTICE '  - Compression policy (сжатие через 7 дней)';
    RAISE NOTICE '  - Защита от изменений через контрольные суммы';
    RAISE NOTICE '  - Phase 1 таблицы (SystemSettings, SavedSearches, FreeScout, Email, ThreatIntel)';
    RAISE NOTICE '';
    RAISE NOTICE 'Следующий шаг: Запустить database_postgresql/seed.sql для создания начальных данных';
END $$;
