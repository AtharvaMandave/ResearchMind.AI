-- ─────────────────────────────────────────────────────────────────────────────
--  ResearchMind AI – PostgreSQL Initialisation Script
--  Run automatically by Docker on first container start.
-- ─────────────────────────────────────────────────────────────────────────────

-- Enable the pgvector extension (required for vector similarity search)
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify extensions are active
SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp');
