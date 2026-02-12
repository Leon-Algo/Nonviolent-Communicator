# NVC Practice Coach Backend (MVP)

## Quick Start

1. Create virtualenv and install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

2. Copy env:

```bash
cp .env.example .env
```

3. Run locally:

```bash
uvicorn app.main:app --reload --port 8000
```

4. Health check:

```bash
curl http://127.0.0.1:8000/health
```

5. Run tests:

```bash
pytest tests -q
```

DB-backed integration tests (requires local Postgres):

```bash
RUN_DB_TESTS=1 pytest tests/test_api_flow_integration.py -q
```

RLS/JWT smoke scripts (repo root):

```bash
bash scripts/rls_isolation_check.sh
bash scripts/supabase_jwt_api_smoke_test.sh https://nvc-practice-api.vercel.app
bash scripts/release_preflight.sh https://nvc-practice-api.vercel.app
# include DB integration tests in preflight
RUN_DB_TESTS=1 bash scripts/release_preflight.sh https://nvc-practice-api.vercel.app
```

CI manual preflight:

- Workflow: `.github/workflows/release-preflight.yml`
- Requires repo secrets for online checks:
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`

6. Auth mode switch:

```bash
# local mock auth
AUTH_MODE=mock

# Supabase JWT auth
AUTH_MODE=supabase
```

Production guard:

```bash
# keep false in production
MOCK_AUTH_ENABLED=false
ALLOW_MOCK_AUTH_IN_PRODUCTION=false
```

5. Mock auth token format:

```text
Authorization: Bearer mock_<uuid>
```

Example:

```text
Authorization: Bearer mock_8a4c3f2a-2f88-4c74-9bc0-3123d26df302
```

## Implemented Endpoints (MVP Core)

- `POST /api/v1/scenes`
- `POST /api/v1/sessions`
- `POST /api/v1/sessions/{session_id}/messages`
- `POST /api/v1/sessions/{session_id}/rewrite`
- `POST /api/v1/sessions/{session_id}/summary`
- `POST /api/v1/reflections`
- `GET /api/v1/progress/weekly`

## Current Status

- FastAPI scaffold ready
- Mock auth dependency ready
- Supabase JWT verification ready (JWKS + /auth/v1/user fallback)
- Health endpoint ready
- Core API endpoints connected to PostgreSQL
- AI generation supports ModelScope OpenAI-compatible API with local fallback
- Unified error response contract (`error_code`, `message`, `request_id`)
- Message API idempotency support (`client_message_id`)
- DB pooling strategy:
  - production: `NullPool` (serverless-safe)
  - non-production: default pooled connections (better local stability)

## Required DB Migrations

Run in order:

1. `db/migrations/0001_init_nvc_practice.sql`
2. `db/migrations/0002_add_idempotency_keys.sql`
3. `db/migrations/0003_sync_auth_users_to_public_users.sql`
4. `db/migrations/0004_enable_rls_core_tables.sql`
5. `db/migrations/0005_fix_request_user_id_claim_resolution.sql`

## Next Implementation Steps

1. Add integration tests for core flows
2. Add idempotency on `client_message_id`
3. Add stronger OFNR rubric and eval runner
4. Add Supabase RLS before public test
