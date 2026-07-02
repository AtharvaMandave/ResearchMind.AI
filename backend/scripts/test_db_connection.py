"""
Supabase connection test for ResearchMind AI.
Builds the asyncpg URL safely from individual parts so special characters
in the password can never break URL parsing.

Run:  .venv\Scripts\python scripts\test_db_connection.py
"""
import asyncio
import sys
import os
from urllib.parse import quote_plus

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env manually so we can read raw POSTGRES_* parts
from dotenv import dotenv_values

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
env = dotenv_values(env_path)

import asyncpg


async def test_connection():
    # ── Build URL safely from individual parts ────────────────────────────────
    user = env.get("POSTGRES_USER", "postgres")
    password = env.get("POSTGRES_PASSWORD", "")
    host = env.get("POSTGRES_HOST", "localhost")
    port = env.get("POSTGRES_PORT", "5432").strip()
    db = env.get("POSTGRES_DB", "postgres")

    # quote_plus encodes @ -> %40, spaces -> +, etc.
    safe_password = quote_plus(password)

    asyncpg_url = f"postgresql://{user}:{safe_password}@{host}:{port}/{db}"

    print(f"\n{'='*62}")
    print("  ResearchMind AI - Supabase Connection Test")
    print(f"{'='*62}")
    print(f"  User  : {user}")
    print(f"  Host  : {host}")
    print(f"  Port  : {port}")
    print(f"  DB    : {db}")
    print(f"  Pass  : {'*' * len(password)}  (raw, {len(password)} chars)")
    print(f"  Encoded pass: {safe_password}")
    print(f"{'='*62}\n")

    try:
        print("[...] Connecting with SSL required...")
        conn = await asyncpg.connect(asyncpg_url, ssl="require", timeout=15)

        # 1. Server version
        version = await conn.fetchval("SELECT version();")
        print(f"[OK]  Connected!")
        print(f"      Server: {version[:75]}")

        # 2. pgvector check
        vec = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');"
        )
        if vec:
            vec_ver = await conn.fetchval(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
            )
            print(f"[OK]  pgvector: INSTALLED (v{vec_ver})")
        else:
            print("[!!]  pgvector: NOT INSTALLED")
            print("      -> Run in Supabase SQL editor:")
            print("         CREATE EXTENSION IF NOT EXISTS vector;")

        # 3. uuid-ossp check
        uuid_ext = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp');"
        )
        print(f"[{'OK' if uuid_ext else '!!'}]  uuid-ossp: {'INSTALLED' if uuid_ext else 'NOT INSTALLED'}")

        # 4. Existing public tables
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
        )
        if tables:
            print(f"\n[DB]  Existing tables ({len(tables)}):")
            for t in tables:
                print(f"       * {t['tablename']}")
        else:
            print("\n[DB]  No tables yet - Alembic will create them next.")

        await conn.close()
        print(f"\n{'='*62}")
        print("  [OK] All checks passed! Ready for Alembic migrations.")
        print(f"{'='*62}\n")
        return True

    except asyncpg.InvalidPasswordError:
        print("\n[FAIL] Wrong password. Check POSTGRES_PASSWORD in .env")
    except asyncpg.InvalidCatalogNameError:
        print(f"\n[FAIL] Database '{db}' does not exist on this server.")
    except OSError as e:
        print(f"\n[FAIL] Network/DNS error: {e}")
        print("\nPossible causes:")
        print(f"  1. Supabase project is PAUSED  ->  go to supabase.com/dashboard and restore it")
        print(f"  2. Wrong host: currently '{host}'")
        print(f"     Check: Project Settings -> Database -> Connection string")
        print(f"  3. Firewall blocking port {port}")
    except Exception as e:
        print(f"\n[FAIL] {type(e).__name__}: {e}")
    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_connection())
