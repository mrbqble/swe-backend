"""Drop all database objects (tables, indexes, sequences, types, etc.).

This script completely clears the database by dropping all objects,
regardless of what they are. This is useful for database resets.
"""

from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app module
sys.path.insert(0, str(Path(__file__).parent.parent))


async def drop_all_objects():
    """Drop all objects from the database."""
    # Convert async URL to sync URL for connection
    database_url = settings.DATABASE_URL

    # Create async engine
    engine = create_async_engine(database_url, echo=False)

    try:
        async with engine.begin() as conn:
            print("[*] Dropping all database objects...")

            # Drop all tables (CASCADE to handle foreign keys)
            print("  - Dropping all tables...")
            await conn.execute(
                text("""
                    DO $$ DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                        END LOOP;
                    END $$;
                """)
            )

            # Drop all sequences
            print("  - Dropping all sequences...")
            await conn.execute(
                text("""
                    DO $$ DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public') LOOP
                            EXECUTE 'DROP SEQUENCE IF EXISTS ' || quote_ident(r.sequence_name) || ' CASCADE';
                        END LOOP;
                    END $$;
                """)
            )

            # Drop all custom types (ENUMs, etc.)
            print("  - Dropping all custom types...")
            await conn.execute(
                text("""
                    DO $$ DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (SELECT typname FROM pg_type WHERE typtype = 'e' AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')) LOOP
                            EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(r.typname) || ' CASCADE';
                        END LOOP;
                    END $$;
                """)
            )

            # Drop all views
            print("  - Dropping all views...")
            await conn.execute(
                text("""
                    DO $$ DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (SELECT table_name FROM information_schema.views WHERE table_schema = 'public') LOOP
                            EXECUTE 'DROP VIEW IF EXISTS ' || quote_ident(r.table_name) || ' CASCADE';
                        END LOOP;
                    END $$;
                """)
            )

            # Drop all functions
            print("  - Dropping all functions...")
            await conn.execute(
                text("""
                    DO $$ DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (
                            SELECT proname, oidvectortypes(proargtypes) as argtypes
                            FROM pg_proc
                            WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                        ) LOOP
                            EXECUTE 'DROP FUNCTION IF EXISTS ' || quote_ident(r.proname) || '(' || r.argtypes || ') CASCADE';
                        END LOOP;
                    END $$;
                """)
            )

            # Drop all indexes (in case any remain)
            print("  - Dropping remaining indexes...")
            await conn.execute(
                text("""
                    DO $$ DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (
                            SELECT indexname FROM pg_indexes WHERE schemaname = 'public'
                        ) LOOP
                            EXECUTE 'DROP INDEX IF EXISTS ' || quote_ident(r.indexname) || ' CASCADE';
                        END LOOP;
                    END $$;
                """)
            )

            print("[OK] All database objects dropped successfully")

    except Exception as e:
        print(f"[ERROR] Failed to drop database objects: {e}")
        raise
    finally:
        await engine.dispose()


async def main():
    """Main entry point."""
    try:
        await drop_all_objects()
    except Exception as e:
        print(f"[ERROR] Database reset failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
