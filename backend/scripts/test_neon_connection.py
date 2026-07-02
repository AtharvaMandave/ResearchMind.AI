"""
Test Neon DB connection using asyncpg directly.
Run: .venv\Scripts\python scripts\test_neon_connection.py
"""
import asyncio
import sys

# Neon DB URL from .env
NEON_URL = "postgresql://neondb_owner:npg_cg5aqAno4IRl@ep-restless-bonus-at6207r1-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# asyncpg uses postgresql:// so we keep it as-is (asyncpg accepts both postgresql:// and postgres://)

import asyncpg

async def test_neon():
    print("=" * 60)
    print("  Neon DB Connection Test")
    print("=" * 60)

    host = "ep-restless-bonus-at6207r1-pooler.c-9.us-east-1.aws.neon.tech"

    # DNS check first
    import socket
    try:
        ip = socket.gethostbyname(host)
        print(f"[OK]  DNS resolved: {host} -> {ip}")
    except Exception as e:
        print(f"[FAIL] DNS resolution failed: {e}")
        sys.exit(1)

    # Now try asyncpg connection
    try:
        print(f"\n[...] Connecting with asyncpg + SSL...")
        conn = await asyncpg.connect(
            user="neondb_owner",
            password="npg_cg5aqAno4IRl",
            host=host,
            port=5432,
            database="neondb",
            ssl="require",
            timeout=15,
        )

        version = await conn.fetchval("SELECT version();")
        print(f"[OK]  Connected!")
        print(f"      Server: {version[:80]}")

        # Check pgvector
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
            print("      -> Run in Neon SQL editor:")
            print("         CREATE EXTENSION IF NOT EXISTS vector;")

        # List existing tables
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
        )
        if tables:
            print(f"\n[DB]  Existing tables ({len(tables)}):")
            for t in tables:
                print(f"       * {t['tablename']}")
        else:
            print("\n[DB]  No tables yet in public schema.")

        await conn.close()
        print("\n" + "=" * 60)
        print("  [OK] Neon DB connection successful!")
        print("=" * 60)

    except asyncpg.InvalidPasswordError:
        print("[FAIL] Wrong password.")
        sys.exit(1)
    except asyncpg.InvalidCatalogNameError:
        print("[FAIL] Database 'neondb' does not exist.")
        sys.exit(1)
    except OSError as e:
        print(f"[FAIL] Network error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_neon())
