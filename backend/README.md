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
- Health endpoint ready
- Core API endpoints connected to PostgreSQL
- AI generation supports ModelScope OpenAI-compatible API with local fallback
- Unified error response contract (`error_code`, `message`, `request_id`)
- Message API idempotency support (`client_message_id`)

## Required DB Migrations

Run in order:

1. `db/migrations/0001_init_nvc_practice.sql`
2. `db/migrations/0002_add_idempotency_keys.sql`

## Next Implementation Steps

1. Add integration tests for core flows
2. Add idempotency on `client_message_id`
3. Add stronger OFNR rubric and eval runner
4. Add Supabase RLS before public test
