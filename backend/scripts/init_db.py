"""
Database initialization script
Checks connection and optionally creates/updates schema
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import settings
from app.database import engine, check_db_connection
from sqlalchemy import text
import time


def print_header(text_content):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text_content}")
    print("=" * 70)


def check_connection():
    """Check if database connection works"""
    print_header("Checking Database Connection")

    print(f"\nConnection settings:")
    print(f"  Server:   {settings.mssql_server}:{settings.mssql_port}")
    print(f"  Database: {settings.mssql_database}")
    print(f"  User:     {settings.mssql_user}")
    print(f"  Driver:   {settings.mssql_driver}")

    print(f"\nTesting connection...")

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            if check_db_connection():
                print(f"✓ Connection successful!")
                return True
            else:
                print(f"✗ Connection failed (attempt {attempt}/{max_retries})")
        except Exception as e:
            print(f"✗ Connection failed (attempt {attempt}/{max_retries}): {e}")

        if attempt < max_retries:
            print(f"  Retrying in 2 seconds...")
            time.sleep(2)

    print("\n✗ Could not connect to database after all retries")
    print("\nTroubleshooting:")
    print("  1. Check if MS SQL Server is running")
    print("  2. Verify connection settings in .env file")
    print("  3. Check if SIEM_DB database exists")
    print("  4. Verify SQL user has permissions")
    print("  5. Check firewall settings")

    return False


def check_database_exists():
    """Check if SIEM_DB exists"""
    print_header("Checking Database Existence")

    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM sys.databases WHERE name = 'SIEM_DB'"
            ))
            exists = result.scalar() > 0

            if exists:
                print("✓ Database SIEM_DB exists")
                return True
            else:
                print("✗ Database SIEM_DB does not exist")
                print("\nPlease run the installation scripts first:")
                print("  sqlcmd -S localhost -i database/schema.sql")
                return False

    except Exception as e:
        print(f"✗ Error checking database: {e}")
        return False


def check_tables():
    """Check if required tables exist"""
    print_header("Checking Tables")

    required_tables = [
        ('config', 'Users'),
        ('config', 'Settings'),
        ('assets', 'Agents'),
        ('security_events', 'Events'),
        ('incidents', 'Alerts'),
        ('incidents', 'Incidents'),
        ('compliance', 'AuditLog'),
    ]

    all_exist = True

    try:
        with engine.connect() as conn:
            for schema, table in required_tables:
                result = conn.execute(text(f"""
                    SELECT COUNT(*)
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = '{schema}'
                    AND TABLE_NAME = '{table}'
                """))

                exists = result.scalar() > 0

                status = "✓" if exists else "✗"
                print(f"  {status} {schema}.{table}")

                if not exists:
                    all_exist = False

        if all_exist:
            print("\n✓ All required tables exist")
        else:
            print("\n✗ Some tables are missing")
            print("\nPlease run the installation scripts:")
            print("  sqlcmd -S localhost -i database/schema.sql")

        return all_exist

    except Exception as e:
        print(f"✗ Error checking tables: {e}")
        return False


def check_stored_procedures():
    """Check if stored procedures exist"""
    print_header("Checking Stored Procedures")

    required_procedures = [
        'security_events.InsertEventsBatch',
        'security_events.SearchEvents',
        'security_events.GetDashboardStats',
        'assets.UpdateAgentInfo',
        'incidents.CreateAlert',
    ]

    all_exist = True

    try:
        with engine.connect() as conn:
            for proc in required_procedures:
                schema, name = proc.split('.')
                result = conn.execute(text(f"""
                    SELECT COUNT(*)
                    FROM INFORMATION_SCHEMA.ROUTINES
                    WHERE ROUTINE_SCHEMA = '{schema}'
                    AND ROUTINE_NAME = '{name}'
                    AND ROUTINE_TYPE = 'PROCEDURE'
                """))

                exists = result.scalar() > 0
                status = "✓" if exists else "✗"
                print(f"  {status} {proc}")

                if not exists:
                    all_exist = False

        if all_exist:
            print("\n✓ All required procedures exist")
        else:
            print("\n✗ Some procedures are missing")
            print("\nPlease run:")
            print("  sqlcmd -S localhost -i database/procedures.sql")

        return all_exist

    except Exception as e:
        print(f"✗ Error checking procedures: {e}")
        return False


def check_default_user():
    """Check if default admin user exists"""
    print_header("Checking Default Users")

    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT Username, Role, IsActive
                FROM config.Users
                WHERE Username IN ('admin', 'analyst', 'viewer')
            """))

            users = result.fetchall()

            if users:
                print(f"\n✓ Found {len(users)} default users:")
                for user in users:
                    print(f"  - {user[0]:12} | Role: {user[1]:10} | Active: {user[2]}")

                print("\n⚠ Default password: Admin123!")
                print("  Please change passwords after first login!")
                return True
            else:
                print("✗ No default users found")
                print("\nPlease run:")
                print("  sqlcmd -S localhost -i database/seed.sql")
                return False

    except Exception as e:
        print(f"✗ Error checking users: {e}")
        return False


def get_statistics():
    """Get database statistics"""
    print_header("Database Statistics")

    try:
        with engine.connect() as conn:
            # Count events
            result = conn.execute(text("SELECT COUNT(*) FROM security_events.Events"))
            events_count = result.scalar()

            # Count agents
            result = conn.execute(text("SELECT COUNT(*) FROM assets.Agents"))
            agents_count = result.scalar()

            # Count alerts
            result = conn.execute(text("SELECT COUNT(*) FROM incidents.Alerts"))
            alerts_count = result.scalar()

            # Count users
            result = conn.execute(text("SELECT COUNT(*) FROM config.Users"))
            users_count = result.scalar()

            # Count rules
            result = conn.execute(text("SELECT COUNT(*) FROM config.DetectionRules"))
            rules_count = result.scalar()

            print(f"\nCurrent statistics:")
            print(f"  Events:          {events_count:,}")
            print(f"  Agents:          {agents_count:,}")
            print(f"  Alerts:          {alerts_count:,}")
            print(f"  Users:           {users_count:,}")
            print(f"  Detection Rules: {rules_count:,}")

    except Exception as e:
        print(f"✗ Error getting statistics: {e}")


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("  SIEM DATABASE INITIALIZATION")
    print("  Version 1.0.0")
    print("=" * 70)

    # Step 1: Check connection
    if not check_connection():
        sys.exit(1)

    # Step 2: Check database
    if not check_database_exists():
        sys.exit(1)

    # Step 3: Check tables
    tables_ok = check_tables()

    # Step 4: Check stored procedures
    procedures_ok = check_stored_procedures()

    # Step 5: Check users
    users_ok = check_default_user()

    # Step 6: Statistics
    get_statistics()

    # Summary
    print_header("Initialization Summary")

    if tables_ok and procedures_ok and users_ok:
        print("\n✓ Database is ready!")
        print("\nYou can now start the backend:")
        print("  cd backend")
        print("  source venv/bin/activate")
        print("  python -m uvicorn app.main:app --reload")
        sys.exit(0)
    else:
        print("\n✗ Database initialization incomplete")
        print("\nPlease run the missing installation scripts:")
        if not tables_ok:
            print("  sqlcmd -S localhost -i database/schema.sql")
        if not procedures_ok:
            print("  sqlcmd -S localhost -i database/procedures.sql")
        if not users_ok:
            print("  sqlcmd -S localhost -i database/seed.sql")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
