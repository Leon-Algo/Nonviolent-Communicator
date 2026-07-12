# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NVC (Nonviolent Communication) practice coach MVP. Users follow a "login -> practice -> review" flow to build communication skills. The core chain is: scene -> session -> message feedback -> summary -> reflection -> weekly progress.

## Common Commands

### Backend
```bash
cd backend
pip install -e "[dev]"          # install dependencies
uvicorn app.main:app --reload --port 8000  # run dev server
pytest tests -q                 # run all tests
pytest tests/test_nvc_service.py -q        # run single test file
pytest tests/test_nvc_service.py::test_x -q  # run single test
AUTH_MODE=mock uvicorn app.main:app --reload --port 8000  # local dev with mock auth
```

### DB integration tests (requires local Postgres)
```bash
RUN_DB_TESTS=1 pytest tests/test_api_flow_integration.py -q
```

### Pre-flight & smoke tests (from repo root)
```bash
bash scripts/release_preflight.sh https://nvc-practice-api.vercel.app
bash scripts/rls_isolation_check.sh
bash scripts/supabase_jwt_api_smoke_test.sh <front_domain>
bash scripts/pwa_smoke_check.sh
python scripts/run_ofnr_eval.py --mode offline  # OFNR regression eval
```

### Deploy
```bash
# Frontend (Cloudflare Pages)
bash scripts/cloudflare_pages_release.sh deploy nonviolent-communicator-stable main web functions
bash scripts/cloudflare_pages_release.sh deploy nonviolent-communicator main web functions
# Backend (Vercel)
bash scripts/vercel_release.sh preview api
bash scripts/vercel_release.sh prod api
```

### Lint
```bash
cd backend && ruff check .      # lint
ruff format .                   # format
```

## Architecture

### Deployment Topology
- **Frontend**: Cloudflare Pages (static HTML/CSS/JS + PWA)
- **Backend**: Vercel serverless (FastAPI)
- **Database**: Supabase PostgreSQL (RLS-enabled)
- **API proxy**: Cloudflare Pages Functions at `/api/*` reverse-proxy to Vercel backend
- **Auth**: Supabase JWT (production) / Mock tokens (local dev, `AUTH_MODE=mock`)
- **LLM**: ModelScope OpenAI-compatible API

### Backend Layering (`backend/app/`)
- `api/routers/` — request validation, routing, error mapping (scenes, sessions, reflections, progress, health)
- `api/deps.py` — auth dependency injection (`get_current_user`)
- `services/` — business logic: NVC analysis engine (`nvc_service.py`), OFNR evaluation
- `db/` — SQLAlchemy async session management, RLS context injection (`db/security.py`)
- `core/` — config, error contract (`ApiError`/`ErrorCode`), security, Supabase JWT verification, observability metrics
- `schemas/` — Pydantic v2 request/response models

### Frontend (`web/`)
- Single-page vanilla JS app (`app.js`, ~3000 lines). No build step — served as-is.
- `sw.js` — Service Worker: caches static assets only (styles, images, fonts). Does NOT cache `app.js` or intercept API/navigation requests.
- `manifest.webmanifest` — PWA manifest
- `index.html` — entry point with view routing via JS

### API Proxy (`functions/`)
- `api/[[path]].js` — catch-all reverse proxy: forwards `/api/*` to Vercel backend, sets `x-api-proxy: cloudflare-pages`
- `health-backend.js` — standalone backend reachability check

### DB Migrations (`db/migrations/`)
Must run in order: `0001` through `0005`. Core tables have RLS policies; `apply_request_rls_context()` sets the per-request DB role and user claim.

## Key Patterns

### Auth flow
- `get_current_user()` in `api/deps.py` dispatches on `settings.auth_mode`: `mock` parses `Bearer mock_<uuid>`, `supabase` verifies JWT via JWKS.
- Production enforces `MOCK_AUTH_ENABLED=false` via model validator.

### Error contract
All errors return `{ "error_code": "<ErrorCode>", "message": "...", "request_id": "..." }`. Raise `ApiError` in services/routers for structured errors. Unhandled exceptions are caught globally and return 500 with `INTERNAL_ERROR`.

### Request observability
Every request gets a `request_id` (from `x-request-id` header or generated), logged as JSON with route, status, latency. In-memory metrics at `/ops/metrics`.

### DB session strategy
- Production/test: `NullPool` (serverless-safe, avoids stale connections)
- Development: default pooling

### Frontend API calls
Production forces same-origin `/api/*` (no custom base URL). Only local dev allows configuring `api_base_url`.

## Critical Rules (from migration postmortem)

When changing API routing strategy, update ALL three: `web/app.js`, `functions/api/[[path]].js`, `docs/SETUP_AND_TESTING.md`.

When changing SW cache strategy: bump `SW_VERSION`, document whether `app.js` is cached, run PWA smoke test.

## Critical Rules (from 2026-07-12 auth outage)

> Root cause: `web/app.js` hardcoded `DEFAULT_SUPABASE_URL` to a non-existent project (`wiafjgjfdrajlxnlkray`, DNS NXDOMAIN) since commit 498e4fc, while `.env`/backend used the real project (`sggtwlnluvvhtgsiritg`). Auth was broken in production from launch and went undetected because go-live verification ran curl/JWT via the backend and never exercised a real browser signup.

### `.env` is the single source of truth for config
- All project config (Supabase URL/keys, Agora, LLM, Vercel, Cloudflare, Volcengine) lives in root `.env`.
- Frontend defaults in `web/app.js` (`DEFAULT_SUPABASE_URL`, `DEFAULT_SUPABASE_ANON_KEY`) MUST stay aligned with `.env`. Changing one without the other = outage. State the alignment explicitly in the commit message.
- Real Supabase project ref: `sggtwlnluvvhtgsiritg` (`.env` `SUPABASE_URL`; backend `DATABASE_URL`). Frontend, backend, and `.env` must all reference the same project.
- `.env` holds secrets (service-role key, DB password, platform tokens) — never commit, never paste into chat/logs. The anon key is public and may live in the frontend.

### Auth vs data take different network paths
- **Auth (signup/login)**: the browser hits Supabase DIRECTLY (`${SUPABASE_URL}/auth/v1/*`), NOT the same-origin proxy. So `SUPABASE_URL` must be a real project the browser can reach.
- **Data API**: browser → same-origin `/api/*` (CF Pages Function) → `api.leoalgo.site` (Vercel) → Supabase/Agora.
- Email confirmation is ON: a fresh signup cannot log in until the confirmation email link is clicked. To unblock E2E testing, confirm the user via admin API with `.env` `SUPABASE_SERVICE_ROLE_KEY` (never expose this key).

### Verification must include a real browser E2E pass
- For auth/routing/config changes, verify in a real browser: home → signup → login → create scene → send → (voice start/stop). Any network/JS error = not release-ready.
- curl + JWT / backend-contract passing ≠ releasable. Config-class bugs (wrong endpoint, wrong project, wrong key) only surface through the real user path.
- Run `scripts/release_preflight.sh` + `scripts/pwa_smoke_check.sh` before release (they include `node --check web/app.js`, PWA contract check, manifest validation).

### Supabase ops gotchas
- Free-tier projects auto-PAUSE after ~7 days of inactivity → the next signup fails. Add a daily DB keepalive or upgrade the tier.
- Deleting `auth.users` does NOT cascade into the public schema. To remove a user's data, delete child tables first in FK order (see `db/migrations/0001`: messages/feedback_items/rewrites/summaries → sessions → scenes → users).

## CI

- `backend-tests.yml`: runs `pytest backend/tests -q` on push/PR to main (Python 3.12, Postgres 16 service container)
- `release-preflight.yml`: manual dispatch for full pre-flight checks
