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

## Current Status

- FastAPI scaffold ready
- Mock auth dependency ready
- Health endpoint ready
- API route placeholders aligned with `spec/openapi/nvc-practice-coach.v1.yaml`

## Next Implementation Steps

1. Implement repositories and DB session
2. Implement scenes/sessions/messages services
3. Wire AI provider for chat + OFNR + rewrite
4. Add tests for critical flow
