"""
Database Migration Runner
Автоматически применяет SQL миграции из backend/migrations/
"""

import os
import logging
from pathlib import Path
from typing import List, Tuple
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Manages database schema migrations"""

    def __init__(self, db: Session, migrations_dir: str = "backend/migrations"):
        self.db = db
        self.migrations_dir = Path(migrations_dir)

    def ensure_migrations_table(self):
        """Create schema_migrations table if it doesn't exist"""
        try:
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS config.schema_migrations (
                    migration_id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_schema_migrations_name
                ON config.schema_migrations(migration_name);

                CREATE INDEX IF NOT EXISTS idx_schema_migrations_applied_at
                ON config.schema_migrations(applied_at DESC);
            """))
            self.db.commit()
            logger.info("✓ schema_migrations table ready")
        except Exception as e:
            logger.error(f"Failed to create schema_migrations table: {e}")
            self.db.rollback()
            raise

    def get_applied_migrations(self) -> List[str]:
        """Get list of already applied migrations"""
        try:
            result = self.db.execute(text("""
                SELECT migration_name
                FROM config.schema_migrations
                WHERE success = TRUE
                ORDER BY migration_name
            """))
            return [row[0] for row in result]
        except Exception as e:
            logger.warning(f"Could not fetch applied migrations: {e}")
            return []

    def get_pending_migrations(self) -> List[Tuple[str, Path]]:
        """Get list of migrations that haven't been applied yet"""
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return []

        # Get all .sql files in migrations directory
        all_migrations = sorted(self.migrations_dir.glob("*.sql"))

        # Get already applied migrations
        applied = set(self.get_applied_migrations())

        # Filter out already applied
        pending = []
        for migration_file in all_migrations:
            migration_name = migration_file.name
            if migration_name not in applied:
                pending.append((migration_name, migration_file))

        return pending

    def apply_migration(self, migration_name: str, migration_file: Path) -> bool:
        """Apply a single migration"""
        logger.info(f"Applying migration: {migration_name}")

        try:
            # Read migration SQL
            with open(migration_file, 'r', encoding='utf-8') as f:
                sql = f.read()

            # Execute migration
            # PostgreSQL migrations use $$ for dollar-quoted strings
            # We need to execute them as raw SQL
            self.db.execute(text(sql))

            # Record successful migration
            self.db.execute(text("""
                INSERT INTO config.schema_migrations (migration_name, applied_at, success)
                VALUES (:name, CURRENT_TIMESTAMP, TRUE)
            """), {"name": migration_name})

            self.db.commit()
            logger.info(f"✓ Migration {migration_name} applied successfully")
            return True

        except Exception as e:
            self.db.rollback()

            # Record failed migration
            try:
                self.db.execute(text("""
                    INSERT INTO config.schema_migrations (migration_name, applied_at, success, error_message)
                    VALUES (:name, CURRENT_TIMESTAMP, FALSE, :error)
                    ON CONFLICT (migration_name) DO UPDATE
                    SET success = FALSE, error_message = :error, applied_at = CURRENT_TIMESTAMP
                """), {"name": migration_name, "error": str(e)})
                self.db.commit()
            except:
                pass

            logger.error(f"✗ Migration {migration_name} failed: {e}")
            return False

    def run_migrations(self, auto_apply: bool = True) -> Tuple[int, int]:
        """
        Run all pending migrations

        Returns:
            Tuple of (applied_count, failed_count)
        """
        # Ensure migrations table exists
        self.ensure_migrations_table()

        # Get pending migrations
        pending = self.get_pending_migrations()

        if not pending:
            logger.info("No pending migrations")
            return (0, 0)

        logger.info(f"Found {len(pending)} pending migrations")

        applied_count = 0
        failed_count = 0

        for migration_name, migration_file in pending:
            if auto_apply:
                success = self.apply_migration(migration_name, migration_file)
                if success:
                    applied_count += 1
                else:
                    failed_count += 1
            else:
                logger.info(f"Pending migration (not applied): {migration_name}")

        return (applied_count, failed_count)


def run_migrations_on_startup(db: Session):
    """
    Run database migrations on application startup

    This should be called during FastAPI lifespan events
    """
    try:
        logger.info("=" * 70)
        logger.info("Running database migrations...")
        logger.info("=" * 70)

        runner = MigrationRunner(db)
        applied, failed = runner.run_migrations(auto_apply=True)

        if applied > 0:
            logger.info(f"✓ Successfully applied {applied} migration(s)")

        if failed > 0:
            logger.error(f"✗ {failed} migration(s) failed")
            logger.warning("Application may not function correctly!")

        if applied == 0 and failed == 0:
            logger.info("✓ Database schema is up to date")

        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"Migration runner failed: {e}", exc_info=True)
        # Don't crash the application, just warn
        logger.warning("Application starting without migrations!")
