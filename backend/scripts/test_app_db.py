"""
Test Neon DB connection using the app's SQLAlchemy engine (same as production).
Run from backend/: .venv\Scripts\python scripts\test_app_db.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force reload settings (in case lru_cache was primed with old values)
from app.config import get_settings
get_settings.cache_clear()

from app.database import engine
from sqlalchemy.sql import text


async def test():
    settings = get_settings()
    url = settings.database_url
    # Mask password for display
    display_url = url.split("@")[0].rsplit(":", 1)[0] + ":***@" + url.split("@")[-1] if "@" in url else url

    print("=" * 65)
    print("  App DB Connection Test (SQLAlchemy + asyncpg)")
    print("=" * 65)
    print(f"  URL: {display_url}")
    print()

    try:
        async with engine.connect() as conn:
            # Basic connectivity
            val = await conn.execute(text("SELECT 1"))
            print(f"[OK]  Basic query (SELECT 1): {val.scalar()}")

            # Server version
            ver = await conn.execute(text("SELECT version()"))
            print(f"[OK]  PG Version: {ver.scalar()[:70]}")

            # pgvector
            vec = await conn.execute(text(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            ))
            vec_installed = vec.scalar()
            if vec_installed:
                vec_ver = await conn.execute(text(
                    "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
                ))
                print(f"[OK]  pgvector: INSTALLED (v{vec_ver.scalar()})")
            else:
                print("[!!]  pgvector: NOT INSTALLED — run in Neon SQL editor:")
                print("      CREATE EXTENSION IF NOT EXISTS vector;")

            # Tables
            tables = await conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
            ))
            rows = tables.fetchall()
            if rows:
                print(f"\n[DB]  Public tables ({len(rows)}):")
                for r in rows:
                    print(f"       * {r[0]}")
            else:
                print("\n[DB]  No tables yet in public schema.")

        await engine.dispose()
        print("\n" + "=" * 65)
        print("  [OK] All checks passed!")
        print("=" * 65)

    except Exception as e:
        print(f"\n[FAIL] {type(e).__name__}: {e}")
        await engine.dispose()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test())
