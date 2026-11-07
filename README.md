# Móyee — Research with clarity

Móyee is an evidence-grounded research intelligence workspace for undergraduate students, postgraduate researchers, and professionals.

## Repository Layout

- `docs/` — Product Definition, MVP Specification, UX Specification, and Technical Architecture.
- `apps/api/` — Python 3.12+ FastAPI modular monolith (`users`, `projects`, `billing`, and upcoming research modules).
- `apps/web/` — Next.js 15 (App Router) + TypeScript + Tailwind CSS v4 frontend.
- `supabase/migrations/` — PostgreSQL + `pgvector` schema and Row-Level Security (RLS) policies.

## Running Locally

### 1. Backend API (`apps/api`)

```bash
cd apps/api
cp .env.example .env
# Edit .env with your DATABASE_URL and SUPABASE_URL when connecting to Supabase
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Run tests and linter:

```bash
cd apps/api
.venv/bin/pytest
.venv/bin/ruff check app tests
```

### 2. Frontend Web (`apps/web`)

```bash
cd apps/web
cp .env.example .env.local
# Edit .env.local with NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY
npm run dev
```

Open `http://localhost:3000`.
