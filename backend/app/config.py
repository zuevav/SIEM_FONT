"""
Configuration module for SIEM Backend API
Loads settings from environment variables
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # ============================================================================
    # APPLICATION
    # ============================================================================
    app_name: str = Field(default="SIEM System", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=False, env="DEBUG")

    # API
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=4, env="API_WORKERS")
    api_reload: bool = Field(default=True, env="API_RELOAD")

    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        env="CORS_ORIGINS"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # ============================================================================
    # DATABASE TYPE SELECTION
    # ============================================================================
    # Options: "postgresql", "mssql"
    database_type: str = Field(default="postgresql", env="DATABASE_TYPE")

    # ============================================================================
    # DATABASE (POSTGRESQL) - Primary supported database
    # ============================================================================
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="siem_db", env="POSTGRES_DB")
    postgres_user: str = Field(default="siem_app", env="POSTGRES_USER")
    postgres_password: str = Field(default="", env="POSTGRES_PASSWORD")

    # ============================================================================
    # DATABASE (MS SQL SERVER) - Legacy support
    # ============================================================================
    mssql_server: str = Field(default="localhost", env="MSSQL_SERVER")
    mssql_port: int = Field(default=1433, env="MSSQL_PORT")
    mssql_database: str = Field(default="SIEM_DB", env="MSSQL_DATABASE")
    mssql_user: str = Field(default="siem_app", env="MSSQL_USER")
    mssql_password: str = Field(default="", env="MSSQL_PASSWORD")
    mssql_driver: str = Field(
        default="ODBC Driver 18 for SQL Server",
        env="MSSQL_DRIVER"
    )
    mssql_trust_cert: str = Field(default="yes", env="MSSQL_TRUST_CERT")

    # Connection pool
    mssql_pool_size: int = Field(default=20, env="MSSQL_POOL_SIZE")
    mssql_max_overflow: int = Field(default=10, env="MSSQL_MAX_OVERFLOW")

    # Debug SQL
    debug_sql: bool = Field(default=False, env="DEBUG_SQL")

    def get_database_url(self) -> str:
        """Build SQLAlchemy connection string based on DATABASE_TYPE"""
        if self.database_type.lower() == "postgresql":
            return (
                f"postgresql://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        else:
            # MS SQL Server (legacy)
            driver = self.mssql_driver.replace(" ", "+")
            return (
                f"mssql+pyodbc://{self.mssql_user}:{self.mssql_password}"
                f"@{self.mssql_server}:{self.mssql_port}/{self.mssql_database}"
                f"?driver={driver}"
                f"&TrustServerCertificate={self.mssql_trust_cert}"
            )

    # ============================================================================
    # AI PROVIDER SELECTION
    # ============================================================================
    # Options: "deepseek", "yandex_gpt"
    # DeepSeek - Free/affordable AI provider (recommended)
    # Yandex GPT - Requires Yandex Cloud account (paid)
    ai_provider: str = Field(default="deepseek", env="AI_PROVIDER")

    # ============================================================================
    # DEEPSEEK AI (FREE/AFFORDABLE)
    # ============================================================================
    deepseek_enabled: bool = Field(default=True, env="DEEPSEEK_ENABLED")
    deepseek_api_key: str = Field(default="", env="DEEPSEEK_API_KEY")
    deepseek_api_url: str = Field(
        default="https://api.deepseek.com/v1/chat/completions",
        env="DEEPSEEK_API_URL"
    )
    deepseek_model: str = Field(default="deepseek-chat", env="DEEPSEEK_MODEL")
    deepseek_temperature: float = Field(default=0.3, env="DEEPSEEK_TEMPERATURE")
    deepseek_max_tokens: int = Field(default=2000, env="DEEPSEEK_MAX_TOKENS")

    # ============================================================================
    # YANDEX GPT (PAID)
    # ============================================================================
    yandex_gpt_enabled: bool = Field(default=False, env="YANDEX_GPT_ENABLED")
    yandex_gpt_api_key: str = Field(default="", env="YANDEX_GPT_API_KEY")
    yandex_gpt_folder_id: str = Field(default="", env="YANDEX_GPT_FOLDER_ID")
    yandex_gpt_api_url: str = Field(
        default="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        env="YANDEX_GPT_API_URL"
    )
    yandex_gpt_model: str = Field(default="yandexgpt-lite", env="YANDEX_GPT_MODEL")
    yandex_gpt_temperature: float = Field(default=0.3, env="YANDEX_GPT_TEMPERATURE")
    yandex_gpt_max_tokens: int = Field(default=2000, env="YANDEX_GPT_MAX_TOKENS")
    yandex_gpt_timeout: int = Field(default=30, env="YANDEX_GPT_TIMEOUT")

    # AI Processing
    ai_batch_size: int = Field(default=10, env="AI_BATCH_SIZE")
    ai_process_interval_sec: int = Field(default=60, env="AI_PROCESS_INTERVAL_SEC")
    ai_retry_attempts: int = Field(default=3, env="AI_RETRY_ATTEMPTS")
    ai_fallback_to_rules: bool = Field(default=True, env="AI_FALLBACK_TO_RULES")

    # Mock (for testing)
    mock_ai: bool = Field(default=False, env="MOCK_AI")

    @property
    def ai_model_uri(self) -> str:
        """Build Yandex GPT model URI"""
        return f"gpt://{self.yandex_gpt_folder_id}/{self.yandex_gpt_model}"

    # ============================================================================
    # DEFAULT ADMIN USER
    # ============================================================================
    default_admin_username: str = Field(default="admin", env="DEFAULT_ADMIN_USERNAME")
    default_admin_password: str = Field(default="Admin123!", env="DEFAULT_ADMIN_PASSWORD")
    default_admin_email: str = Field(default="admin@company.local", env="DEFAULT_ADMIN_EMAIL")

    # ============================================================================
    # SECURITY & AUTHENTICATION
    # ============================================================================
    jwt_secret_key: str = Field(
        default="change_me_in_production",
        env="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")

    @validator('jwt_secret_key')
    def validate_jwt_secret(cls, v, values):
        """SECURITY: Validate JWT secret is not default and has sufficient entropy"""
        weak_secrets = [
            'change_me_in_production',
            'secret',
            'jwt_secret',
            'your_secret_key',
            'generate_random_32_char_string_CHANGE_ME'
        ]
        if v.lower() in [s.lower() for s in weak_secrets]:
            import warnings
            warnings.warn(
                "SECURITY WARNING: JWT_SECRET_KEY is set to a weak default value! "
                "Generate a secure secret with: openssl rand -hex 32",
                RuntimeWarning
            )
        if len(v) < 32:
            import warnings
            warnings.warn(
                f"SECURITY WARNING: JWT_SECRET_KEY is only {len(v)} characters. "
                "Recommended minimum is 32 characters for security.",
                RuntimeWarning
            )
        return v
    jwt_access_token_expire_minutes: int = Field(
        default=480,
        env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # Session
    session_timeout_minutes: int = Field(
        default=480,
        env="SESSION_TIMEOUT_MINUTES"
    )

    # Password Policy
    password_min_length: int = Field(default=12, env="PASSWORD_MIN_LENGTH")
    password_require_uppercase: bool = Field(
        default=True,
        env="PASSWORD_REQUIRE_UPPERCASE"
    )
    password_require_lowercase: bool = Field(
        default=True,
        env="PASSWORD_REQUIRE_LOWERCASE"
    )
    password_require_digits: bool = Field(
        default=True,
        env="PASSWORD_REQUIRE_DIGITS"
    )
    password_require_special: bool = Field(
        default=True,
        env="PASSWORD_REQUIRE_SPECIAL"
    )

    # Account Lockout
    failed_login_attempts: int = Field(default=5, env="FAILED_LOGIN_ATTEMPTS")
    account_lockout_minutes: int = Field(default=30, env="ACCOUNT_LOCKOUT_MINUTES")

    # ============================================================================
    # ACTIVE DIRECTORY (OPTIONAL)
    # ============================================================================
    ad_enabled: bool = Field(default=False, env="AD_ENABLED")
    ad_server: str = Field(default="ldap://localhost:389", env="AD_SERVER")
    ad_base_dn: str = Field(default="DC=company,DC=local", env="AD_BASE_DN")
    ad_bind_user: str = Field(default="", env="AD_BIND_USER")
    ad_bind_password: str = Field(default="", env="AD_BIND_PASSWORD")
    ad_user_search_filter: str = Field(
        default="(&(objectClass=user)(sAMAccountName={username}))",
        env="AD_USER_SEARCH_FILTER"
    )
    ad_sync_enabled: bool = Field(default=False, env="AD_SYNC_ENABLED")
    ad_sync_interval_hours: int = Field(default=24, env="AD_SYNC_INTERVAL_HOURS")

    # ============================================================================
    # EMAIL NOTIFICATIONS
    # ============================================================================
    email_enabled: bool = Field(default=True, env="EMAIL_ENABLED")
    smtp_server: str = Field(default="localhost", env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: str = Field(default="", env="SMTP_USERNAME")
    smtp_password: str = Field(default="", env="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, env="SMTP_USE_TLS")
    smtp_from_email: str = Field(default="siem@company.local", env="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="SIEM System", env="SMTP_FROM_NAME")

    # Recipients
    email_admin_list: str = Field(default="", env="EMAIL_ADMIN_LIST")
    email_analyst_list: str = Field(default="", env="EMAIL_ANALYST_LIST")

    # Mock
    mock_email: bool = Field(default=False, env="MOCK_EMAIL")

    @property
    def email_admins(self) -> List[str]:
        """Parse admin email list"""
        if not self.email_admin_list:
            return []
        return [email.strip() for email in self.email_admin_list.split(",")]

    @property
    def email_analysts(self) -> List[str]:
        """Parse analyst email list"""
        if not self.email_analyst_list:
            return []
        return [email.strip() for email in self.email_analyst_list.split(",")]

    # ============================================================================
    # TELEGRAM (OPTIONAL)
    # ============================================================================
    telegram_enabled: bool = Field(default=False, env="TELEGRAM_ENABLED")
    telegram_bot_token: str = Field(default="", env="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", env="TELEGRAM_CHAT_ID")
    telegram_critical_only: bool = Field(default=True, env="TELEGRAM_CRITICAL_ONLY")
    telegram_min_severity: int = Field(default=3, env="TELEGRAM_MIN_SEVERITY")

    mock_telegram: bool = Field(default=False, env="MOCK_TELEGRAM")

    # ============================================================================
    # REDIS (OPTIONAL)
    # ============================================================================
    redis_enabled: bool = Field(default=False, env="REDIS_ENABLED")
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: str = Field(default="", env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_cache_ttl: int = Field(default=300, env="REDIS_CACHE_TTL")

    # Redis Queues
    redis_queue_enabled: bool = Field(default=False, env="REDIS_QUEUE_ENABLED")
    redis_queue_name: str = Field(default="siem:events", env="REDIS_QUEUE_NAME")

    def get_redis_url(self) -> str:
        """Build Redis connection URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ============================================================================
    # DATA RETENTION
    # ============================================================================
    retention_days: int = Field(default=1825, env="RETENTION_DAYS")  # 5 лет
    retention_alerts_days: int = Field(default=1825, env="RETENTION_ALERTS_DAYS")
    retention_audit_days: int = Field(default=1825, env="RETENTION_AUDIT_DAYS")
    retention_incidents_days: int = Field(default=2555, env="RETENTION_INCIDENTS_DAYS")

    auto_purge_enabled: bool = Field(default=False, env="AUTO_PURGE_ENABLED")
    auto_purge_batch_size: int = Field(default=10000, env="AUTO_PURGE_BATCH_SIZE")
    auto_purge_interval_days: int = Field(default=1, env="AUTO_PURGE_INTERVAL_DAYS")

    # ============================================================================
    # AGENT SETTINGS
    # ============================================================================
    agent_heartbeat_interval_sec: int = Field(
        default=60,
        env="AGENT_HEARTBEAT_INTERVAL_SEC"
    )
    agent_offline_threshold_minutes: int = Field(
        default=5,
        env="AGENT_OFFLINE_THRESHOLD_MINUTES"
    )
    agent_config_update_enabled: bool = Field(
        default=True,
        env="AGENT_CONFIG_UPDATE_ENABLED"
    )
    agent_auto_update_enabled: bool = Field(
        default=False,
        env="AGENT_AUTO_UPDATE_ENABLED"
    )
    agent_max_batch_size: int = Field(default=1000, env="AGENT_MAX_BATCH_SIZE")
    agent_compression_enabled: bool = Field(
        default=True,
        env="AGENT_COMPRESSION_ENABLED"
    )

    # ============================================================================
    # CBR REPORTING (ЦБ РФ)
    # ============================================================================
    cbr_reporting_enabled: bool = Field(default=True, env="CBR_REPORTING_ENABLED")

    # Organization Info
    cbr_org_name: str = Field(default="", env="CBR_ORG_NAME")
    cbr_org_inn: str = Field(default="", env="CBR_ORG_INN")
    cbr_org_ogrn: str = Field(default="", env="CBR_ORG_OGRN")
    cbr_org_kpp: str = Field(default="", env="CBR_ORG_KPP")
    cbr_org_address: str = Field(default="", env="CBR_ORG_ADDRESS")
    cbr_org_phone: str = Field(default="", env="CBR_ORG_PHONE")
    cbr_org_email: str = Field(default="", env="CBR_ORG_EMAIL")

    # Contact Person
    cbr_contact_person: str = Field(default="", env="CBR_CONTACT_PERSON")
    cbr_contact_position: str = Field(default="", env="CBR_CONTACT_POSITION")
    cbr_contact_email: str = Field(default="", env="CBR_CONTACT_EMAIL")
    cbr_contact_phone: str = Field(default="", env="CBR_CONTACT_PHONE")

    # FinCERT
    cbr_fincert_enabled: bool = Field(default=False, env="CBR_FINCERT_ENABLED")
    cbr_fincert_api_url: str = Field(
        default="https://fincert.cbr.ru/api",
        env="CBR_FINCERT_API_URL"
    )
    cbr_fincert_api_key: str = Field(default="", env="CBR_FINCERT_API_KEY")
    cbr_fincert_org_id: str = Field(default="", env="CBR_FINCERT_ORG_ID")

    # Auto-reporting
    cbr_auto_report_enabled: bool = Field(default=False, env="CBR_AUTO_REPORT_ENABLED")
    cbr_auto_report_min_severity: int = Field(
        default=3,
        env="CBR_AUTO_REPORT_MIN_SEVERITY"
    )
    cbr_auto_report_delay_hours: int = Field(
        default=3,
        env="CBR_AUTO_REPORT_DELAY_HOURS"
    )

    # ============================================================================
    # LOGGING
    # ============================================================================
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")  # json or text
    log_file_enabled: bool = Field(default=True, env="LOG_FILE_ENABLED")
    log_file_path: str = Field(default="/var/log/siem/app.log", env="LOG_FILE_PATH")
    log_file_max_size_mb: int = Field(default=100, env="LOG_FILE_MAX_SIZE_MB")
    log_file_backup_count: int = Field(default=10, env="LOG_FILE_BACKUP_COUNT")

    # ============================================================================
    # MONITORING & METRICS
    # ============================================================================
    metrics_enabled: bool = Field(default=False, env="METRICS_ENABLED")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    prometheus_enabled: bool = Field(default=False, env="PROMETHEUS_ENABLED")
    health_check_enabled: bool = Field(default=True, env="HEALTH_CHECK_ENABLED")
    health_check_path: str = Field(default="/health", env="HEALTH_CHECK_PATH")

    # ============================================================================
    # PERFORMANCE
    # ============================================================================
    event_batch_size: int = Field(default=1000, env="EVENT_BATCH_SIZE")
    event_processing_threads: int = Field(default=4, env="EVENT_PROCESSING_THREADS")
    event_queue_size: int = Field(default=10000, env="EVENT_QUEUE_SIZE")

    max_events_per_query: int = Field(default=10000, env="MAX_EVENTS_PER_QUERY")
    query_timeout_sec: int = Field(default=30, env="QUERY_TIMEOUT_SEC")

    db_pool_size: int = Field(default=20, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, env="DB_MAX_OVERFLOW")
    db_pool_recycle_sec: int = Field(default=3600, env="DB_POOL_RECYCLE_SEC")

    # ============================================================================
    # RATE LIMITING
    # ============================================================================
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")

    # ============================================================================
    # FEATURE FLAGS
    # ============================================================================
    feature_ai_analysis: bool = Field(default=True, env="FEATURE_AI_ANALYSIS")
    feature_auto_remediation: bool = Field(
        default=False,
        env="FEATURE_AUTO_REMEDIATION"
    )
    feature_threat_hunting: bool = Field(default=True, env="FEATURE_THREAT_HUNTING")
    feature_ueba: bool = Field(default=True, env="FEATURE_UEBA")
    feature_vulnerability_scan: bool = Field(
        default=False,
        env="FEATURE_VULNERABILITY_SCAN"
    )
    feature_compliance_scan: bool = Field(
        default=True,
        env="FEATURE_COMPLIANCE_SCAN"
    )

    # ============================================================================
    # TIMEZONE
    # ============================================================================
    tz: str = Field(default="Europe/Moscow", env="TZ")

    # ============================================================================
    # TESTING
    # ============================================================================
    testing: bool = Field(default=False, env="TESTING")

    class Config:
        """Pydantic config"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance (for dependency injection)"""
    return settings
