# Agora Voice Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the Agora voice agent into the existing NVC product without keeping the quickstart as a separate nested app.

**Architecture:** Keep the existing Vanilla PWA and Vercel FastAPI backend. Add `/api/v1/voice/*` to the main backend, persist all voice session state in Supabase, and make Agora start/stop calls stateless so the implementation can run on Vercel first and be extracted later if needed.

**Tech Stack:** FastAPI, SQLAlchemy async, Supabase PostgreSQL/RLS, Vercel Python runtime, Cloudflare Pages Functions, Vanilla JS PWA, Agora RTC/RTM, `agora-agent-server-sdk`, `agora-agent-client-toolkit`.

---

## File Structure

- Create `db/migrations/0006_add_voice_session_support.sql`
  - Adds voice metadata columns to existing `sessions/messages`.
  - Adds constraints/indexes for modality/source/external turn IDs.
  - Updates RLS only if existing policies do not automatically cover new columns.
- Modify `backend/pyproject.toml`
  - Adds `agora-agent-server-sdk`.
- Modify `backend/.env.example`
  - Adds `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `AGENT_GREETING`.
- Modify `backend/app/core/config.py`
  - Adds typed Agora settings with safe defaults and production validation.
- Create `backend/app/services/voice_agent.py`
  - Stateless wrapper around Agora token/start/stop.
  - No correctness dependency on in-memory `_sessions`.
- Create `backend/app/schemas/voice.py`
  - Pydantic request/response models for voice bootstrap, stop, and transcript sync.
- Create `backend/app/api/routers/voice.py`
  - Authenticated `/api/v1/voice/*` endpoints.
  - Owns scene/session authorization, persistence, idempotency, and calls `voice_agent.py`.
- Modify `backend/app/main.py`
  - Registers `voice_router`.
- Modify `backend/app/schemas/sessions.py` and `backend/app/api/routers/sessions.py`
  - Exposes modality/source metadata in history only where useful.
  - Keeps existing text flow compatible.
- Create `backend/tests/test_voice_service.py`
  - Pure unit tests with mocked Agora SDK.
- Create `backend/tests/test_voice_api.py`
  - FastAPI tests with mocked service/database boundaries where possible.
- Modify `backend/tests/test_config_security.py`
  - Verifies Agora settings are accepted and secrets are not exposed in error payloads.
- Modify `backend/tests/test_api_flow_integration.py`
  - Adds migration/table cleanup awareness for new fields.
- Modify `spec/openapi/nvc-practice-coach.v1.yaml`
  - Adds `/api/v1/voice/*` contract and schemas.
- Modify `web/index.html`, `web/app.js`, `web/styles.css`, `web/sw.js`
  - Adds voice practice mode in current PWA.
  - Loads browser Agora SDK/toolkit in the least invasive way available.
- Create optional `web/vendor/voice/voice-sdk.js` or equivalent generated asset only if the Agora browser SDK cannot be loaded safely as an external module.
- Modify `functions/api/[[path]].js`
  - Usually no code change expected; verify `/api/v1/voice/*` passes through existing proxy.
- Modify `docs/TECHNICAL_SOLUTION.md`, `docs/SETUP_AND_TESTING.md`, `README.md`
  - Documents voice architecture, env vars, smoke test path, and fallback extraction criteria.
- Add or modify `scripts/voice_smoke_test.sh`
  - Exercises backend voice config/start/stop with mock or live mode.

## Task 1: Database Migration

**Files:**
- Create: `db/migrations/0006_add_voice_session_support.sql`
- Modify: `backend/tests/test_api_flow_integration.py`

- [ ] **Step 1: Write migration**

Add columns conservatively:

```sql
ALTER TABLE sessions
  ADD COLUMN IF NOT EXISTS modality VARCHAR(16) NOT NULL DEFAULT 'TEXT',
  ADD COLUMN IF NOT EXISTS voice_channel_name TEXT,
  ADD COLUMN IF NOT EXISTS voice_agent_id TEXT,
  ADD COLUMN IF NOT EXISTS voice_user_uid TEXT,
  ADD COLUMN IF NOT EXISTS voice_agent_uid TEXT,
  ADD COLUMN IF NOT EXISTS voice_status VARCHAR(24),
  ADD COLUMN IF NOT EXISTS voice_started_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS voice_ended_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS voice_expires_at TIMESTAMPTZ;

ALTER TABLE messages
  ADD COLUMN IF NOT EXISTS source VARCHAR(24) NOT NULL DEFAULT 'TEXT_INPUT',
  ADD COLUMN IF NOT EXISTS external_turn_id TEXT,
  ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE sessions
  DROP CONSTRAINT IF EXISTS sessions_modality_check,
  ADD CONSTRAINT sessions_modality_check CHECK (modality IN ('TEXT', 'VOICE'));

ALTER TABLE messages
  DROP CONSTRAINT IF EXISTS messages_source_check,
  ADD CONSTRAINT messages_source_check CHECK (source IN ('TEXT_INPUT', 'VOICE_TRANSCRIPT'));

CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_session_external_turn_role
  ON messages (session_id, external_turn_id, role)
  WHERE external_turn_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_sessions_voice_agent_id
  ON sessions (voice_agent_id)
  WHERE voice_agent_id IS NOT NULL;
```

- [ ] **Step 2: Update DB integration test migration list**

Add `0006_add_voice_session_support.sql` to `MIGRATIONS` in `backend/tests/test_api_flow_integration.py`.

- [ ] **Step 3: Run DB integration migration test**

Run: `cd backend && RUN_DB_TESTS=1 pytest tests/test_api_flow_integration.py -q`

Expected: existing flow still passes; no RLS regression.

## Task 2: Stateless Agora Service

**Files:**
- Create: `backend/app/services/voice_agent.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/.env.example`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/test_voice_service.py`
- Test: `backend/tests/test_config_security.py`

- [ ] **Step 1: Add failing tests**

Cover:
- Missing Agora env raises a clear configuration error.
- `generate_config()` returns `app_id`, `token`, `uid`, `channel_name`, `agent_uid`, `expires_at`.
- `start_agent()` validates positive UIDs and returns `agent_id`.
- `stop_agent()` calls stateless `client.stop_agent(agent_id)` and treats already-stopping conflicts as success.

- [ ] **Step 2: Run tests to verify failure**

Run: `cd backend && pytest tests/test_voice_service.py -q`

Expected: FAIL because module does not exist.

- [ ] **Step 3: Implement minimal service**

Port only the necessary logic from `agent-quickstart-python/server/src/agent.py`:
- Use `AsyncAgora`.
- Generate Token007 with `generate_convo_ai_token`.
- Build `AgoraAgent` with NVC coach prompt.
- Do not store sessions in memory as the source of truth.
- Optional in-memory session cache is allowed only as a best-effort optimization.

- [ ] **Step 4: Add dependency/env docs**

Add `agora-agent-server-sdk>=1.4.1` to `backend/pyproject.toml`.

Add typed settings to `backend/app/core/config.py`:

```python
agora_app_id: str | None = Field(default=None, alias="AGORA_APP_ID")
agora_app_certificate: str | None = Field(default=None, alias="AGORA_APP_CERTIFICATE")
agent_greeting: str = Field(
    default="你好！我是小和，你的非暴力沟通语音教练。今天想练习什么场景呢？",
    alias="AGENT_GREETING",
)
```

Include these fields in existing string stripping validators. Do not require Agora settings at global app startup; require them only when a voice endpoint is called, so text-only deployments still boot.

Add:

```env
AGORA_APP_ID=your_agora_app_id
AGORA_APP_CERTIFICATE=your_agora_app_certificate
AGENT_GREETING=你好！我是小和，你的非暴力沟通语音教练。今天想练习什么场景呢？
```

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/test_voice_service.py tests/test_config_security.py -q`

Expected: PASS.

## Task 3: Voice API Router

**Files:**
- Create: `backend/app/schemas/voice.py`
- Create: `backend/app/api/routers/voice.py`
- Modify: `backend/app/main.py`
- Modify: `spec/openapi/nvc-practice-coach.v1.yaml`
- Test: `backend/tests/test_voice_api.py`

- [ ] **Step 1: Write failing API tests**

Cover:
- Unauthenticated requests return 401.
- Starting voice session requires an owned active scene.
- Start creates a `sessions` row with `modality='VOICE'`.
- Start persists channel, uid, agent id, status, expiry.
- Stop is idempotent and can run without in-memory session.
- User A cannot stop User B's voice session.
- Transcript sync inserts stable USER/ASSISTANT transcript messages once.
- User transcript creates `feedback_items` through existing `analyze_message()`.
- Transcript sync updates `sessions.current_turn` based on stable USER turns.
- Stop marks `voice_status`, `voice_ended_at`, and `sessions.ended_at` appropriately without completing text sessions accidentally.

- [ ] **Step 2: Run tests to verify failure**

Run: `cd backend && pytest tests/test_voice_api.py -q`

Expected: FAIL because routes do not exist.

- [ ] **Step 3: Implement schemas**

Create models:
- `VoiceSessionStartRequest(scene_id, target_turns=6)`
- `VoiceSessionStartResponse(session_id, app_id, token, uid, channel_name, agent_uid, agent_id, expires_at)`
- `VoiceSessionStopResponse(session_id, status)`
- `VoiceTranscriptTurn(role, content, external_turn_id, metadata={})`
- `VoiceTranscriptSyncRequest(turns: list[VoiceTranscriptTurn])`

- [ ] **Step 4: Implement routes**

Suggested endpoints:
- `POST /api/v1/voice/sessions`
- `POST /api/v1/voice/sessions/{session_id}/stop`
- `POST /api/v1/voice/sessions/{session_id}/transcripts`

Rules:
- Always call `apply_request_rls_context()` and `ensure_user_exists()`.
- Derive channel name server-side, e.g. `nvc-{session_id}` after row creation.
- Persist all Agora IDs before returning.
- Stop uses persisted `voice_agent_id`, not memory.
- Transcript sync uses `external_turn_id` unique index for idempotency.
- Transcript sync increments `sessions.current_turn` only for newly inserted stable USER turns.
- Transcript sync marks `sessions.state='COMPLETED'` and `ended_at=NOW()` when `current_turn >= target_turns`.
- Stop marks `voice_status='STOPPED'`, sets `voice_ended_at`, and sets `sessions.ended_at` if the session is not already ended. If stopped before target turns, keep `sessions.state='ABANDONED'` unless product code explicitly completed it.

- [ ] **Step 5: Register router**

Add `app.include_router(voice_router)` in `backend/app/main.py`.

- [ ] **Step 6: Update OpenAPI contract**

Add paths and schemas for:
- `POST /api/v1/voice/sessions`
- `POST /api/v1/voice/sessions/{session_id}/stop`
- `POST /api/v1/voice/sessions/{session_id}/transcripts`

Run any existing OpenAPI lint/check command if present; otherwise validate YAML parses.

- [ ] **Step 7: Run route tests**

Run: `cd backend && pytest tests/test_voice_api.py -q`

Expected: PASS.

## Task 4: History Compatibility

**Files:**
- Modify: `backend/app/schemas/sessions.py`
- Modify: `backend/app/api/routers/sessions.py`
- Test: `backend/tests/test_api_flow_integration.py`

- [ ] **Step 1: Add history assertions for modality**

Extend DB integration test or add a focused DB test so voice sessions appear in existing history list/detail without breaking text sessions.

- [ ] **Step 2: Implement minimal response additions**

Expose `modality` in history list/detail if needed by UI. Do not expose raw Agora token or certificate-derived material.

- [ ] **Step 3: Run tests**

Run:

```bash
cd backend
pytest tests/test_api_flow_integration.py tests/test_voice_api.py -q
```

Expected: PASS in default mode, DB-only sections skipped unless `RUN_DB_TESTS=1`.

## Task 5: PWA Voice Mode

**Files:**
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Modify: `web/sw.js`
- Create optional: `web/vendor/voice/voice-sdk.js`
- Test manually with local or deployed backend.

- [ ] **Step 1: Add UI shell**

Add a mode switch near Step 2:
- `文字对练`
- `语音对练`

Voice mode should reuse selected scene fields and target turns.

- [ ] **Step 2: Add voice state machine**

In `web/app.js`, keep a small state object:

```js
const voiceState = {
  sessionId: "",
  channelName: "",
  agentId: "",
  rtcClient: null,
  rtmClient: null,
  micTrack: null,
  transcript: [],
  started: false,
};
```

- [ ] **Step 3: Add API helpers**

Add:
- `startVoiceSession()`
- `stopVoiceSession()`
- `syncVoiceTranscript()`

All calls go through same auth header path as existing `/api/v1/*` calls.

- [ ] **Step 4: Integrate Agora browser SDK**

Preferred order:
1. If the toolkit has a browser-compatible bundled artifact, load it explicitly.
2. If not, add a tiny build artifact only for voice SDK glue instead of migrating the app to Next/React.

Do not import `agora-agent-uikit`.
If a generated or vendored asset is added under `web/vendor/voice/`, decide explicitly whether `web/sw.js` should cache it. If cached, bump the service worker version; if not cached, document why.

- [ ] **Step 5: Render transcript and controls**

Provide:
- start voice
- mute/unmute
- stop voice
- live transcript list
- error/status line

Only stable transcript turns are synced to backend.

- [ ] **Step 6: Manual browser smoke**

Before browser smoke, run:

```bash
node --check web/app.js
bash scripts/pwa_smoke_check.sh
```

Expected: JavaScript parses; PWA smoke still passes.

Then run local frontend/backend and verify:
- login
- create scene
- start voice
- browser joins Agora
- microphone permission denied shows a recoverable error
- transcript appears
- repeated transcript sync does not duplicate messages
- stop voice releases mic track and disconnects RTC/RTM
- refresh during an active voice session can stop or mark the session safely
- history contains voice session

## Task 6: Smoke Tests And Release Checks

**Files:**
- Create or modify: `scripts/voice_smoke_test.sh`
- Modify: `scripts/release_preflight.sh`
- Modify: `docs/SETUP_AND_TESTING.md`
- Modify CI docs/workflows if dependency install checks live outside `release_preflight.sh`.

- [ ] **Step 1: Add backend smoke script**

Script should accept base URL and token:

```bash
bash scripts/voice_smoke_test.sh https://nonviolent-communicator-stable.pages.dev "$SUPABASE_ACCESS_TOKEN"
```

It should test:
- health
- create scene
- start voice session
- stop voice session
- repeated stop

- [ ] **Step 2: Wire optional preflight**

Add `RUN_VOICE_SMOKE=1` guard to `scripts/release_preflight.sh`.

- [ ] **Step 3: Add syntax and dependency checks**

Ensure release checks include:

```bash
bash -n scripts/voice_smoke_test.sh
cd backend && python -m pip install -e ".[dev]"
cd backend && python - <<'PY'
import agora_agent
print("agora_agent import ok")
PY
```

Run these checks on the same Python minor version used by Vercel, currently Python 3.12 unless the project pins otherwise.

- [ ] **Step 4: Document live requirements**

Document that full voice smoke requires Agora credentials and a real browser/microphone for end-to-end audio.

## Task 7: Documentation And Fallback Criteria

**Files:**
- Modify: `README.md`
- Modify: `docs/TECHNICAL_SOLUTION.md`
- Modify: `docs/SETUP_AND_TESTING.md`

- [ ] **Step 1: Document final architecture**

Add:

```text
PWA -> Cloudflare /api/* -> Vercel FastAPI /api/v1/voice/* -> Supabase + Agora
```

- [ ] **Step 2: Document why Cloudflare is proxy-only**

State that Cloudflare Pages Functions remain the same-origin proxy; Python Workers are not the first host for the Agora SDK path.

- [ ] **Step 3: Document fallback triggers**

Extract `/api/v1/voice/*` to a container service only if:
- Vercel cannot build/import `agora-agent-server-sdk`.
- start/stop p95 is unacceptable.
- serverless lifecycle causes orphaned agent cleanup issues.
- a background worker or fixed egress IP becomes necessary.

## Final Verification

- [ ] Run backend unit tests:

```bash
cd backend
pytest tests -q
```

- [ ] Verify dependency install/import:

```bash
cd backend
python -m pip install -e ".[dev]"
python - <<'PY'
import agora_agent
print("agora_agent import ok")
PY
```

- [ ] Run DB integration tests if local Postgres is available:

```bash
cd backend
RUN_DB_TESTS=1 pytest tests/test_api_flow_integration.py tests/test_voice_api.py -q
```

- [ ] Run OFNR regression:

```bash
python scripts/run_ofnr_eval.py --mode offline
```

- [ ] Run release preflight:

```bash
bash scripts/release_preflight.sh https://nonviolent-communicator-stable.pages.dev
```

- [ ] Run static browser checks:

```bash
node --check web/app.js
bash scripts/pwa_smoke_check.sh
```

- [ ] Run voice smoke when Agora env is configured:

```bash
RUN_VOICE_SMOKE=1 bash scripts/release_preflight.sh https://nonviolent-communicator-stable.pages.dev
```

## Review Handoff

After each task:
- Update the checklist in this file.
- Record test output in the implementation progress notes.
- Ask 扣子 to validate behavior after Task 3, Task 5, and final verification.
