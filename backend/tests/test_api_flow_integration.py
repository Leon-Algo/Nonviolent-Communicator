import asyncio
import os
from datetime import date
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from fastapi.testclient import TestClient

from app.main import create_app

RUN_DB_TESTS = os.getenv("RUN_DB_TESTS", "0") == "1"
pytestmark = pytest.mark.skipif(
    not RUN_DB_TESTS,
    reason="set RUN_DB_TESTS=1 to run DB integration tests",
)

ROOT_DIR = Path(__file__).resolve().parents[2]
MIGRATIONS = [
    ROOT_DIR / "db" / "migrations" / "0001_init_nvc_practice.sql",
    ROOT_DIR / "db" / "migrations" / "0002_add_idempotency_keys.sql",
    ROOT_DIR / "db" / "migrations" / "0004_enable_rls_core_tables.sql",
    ROOT_DIR / "db" / "migrations" / "0005_fix_request_user_id_claim_resolution.sql",
]
TABLES_TO_TRUNCATE = [
    "idempotency_keys",
    "event_logs",
    "reflections",
    "summaries",
    "rewrites",
    "feedback_items",
    "messages",
    "sessions",
    "scenes",
    "users",
]


def _asyncpg_database_url() -> str:
    raw = os.environ["DATABASE_URL"].strip()
    if raw.startswith("postgresql+asyncpg://"):
        return raw.replace("postgresql+asyncpg://", "postgresql://", 1)
    return raw


def _run_sql(sql: str) -> None:
    async def _inner():
        conn = await asyncpg.connect(_asyncpg_database_url(), timeout=20)
        try:
            await conn.execute(sql)
        finally:
            await conn.close()

    asyncio.run(_inner())


@pytest.fixture(scope="session", autouse=True)
def _setup_schema():
    for migration in MIGRATIONS:
        _run_sql(migration.read_text(encoding="utf-8"))
    yield


@pytest.fixture(autouse=True)
def _clean_tables(_setup_schema):
    table_list = ", ".join(TABLES_TO_TRUNCATE)
    _run_sql(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE;")


def _auth_headers(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer mock_{user_id}"}


def test_full_api_flow_with_idempotency_and_progress():
    client = TestClient(create_app())
    user_id = "8a4c3f2a-2f88-4c74-9bc0-3123d26df302"
    headers = _auth_headers(user_id)

    scene_resp = client.post(
        "/api/v1/scenes",
        headers=headers,
        json={
            "title": "和同事沟通延期风险",
            "template_id": "PEER_FEEDBACK",
            "counterparty_role": "PEER",
            "relationship_level": "TENSE",
            "goal": "确认新的里程碑并明确责任",
            "pain_points": ["对方容易防御", "我会急躁"],
            "context": "这个需求已经两次延期，影响发布节奏",
            "power_dynamic": "PEER_LEVEL",
        },
    )
    assert scene_resp.status_code == 201
    scene_id = scene_resp.json()["scene_id"]

    session_resp = client.post(
        "/api/v1/sessions",
        headers=headers,
        json={"scene_id": scene_id, "target_turns": 6},
    )
    assert session_resp.status_code == 201
    session_id = session_resp.json()["session_id"]

    client_message_id = str(uuid4())
    message_payload = {
        "client_message_id": client_message_id,
        "content": "你们总是拖延，根本不专业。",
    }
    first_msg_resp = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        headers=headers,
        json=message_payload,
    )
    assert first_msg_resp.status_code == 200
    first_body = first_msg_resp.json()
    assert first_body["feedback"]["overall_score"] >= 0
    assert first_body["assistant_message"]["content"]

    retry_msg_resp = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        headers=headers,
        json=message_payload,
    )
    assert retry_msg_resp.status_code == 200
    assert retry_msg_resp.json()["user_message_id"] == first_body["user_message_id"]

    rewrite_resp = client.post(
        f"/api/v1/sessions/{session_id}/rewrite",
        headers=headers,
        json={
            "source_message_id": first_body["user_message_id"],
            "rewrite_style": "NEUTRAL",
        },
    )
    assert rewrite_resp.status_code == 200
    assert rewrite_resp.json()["rewritten_content"]

    summary_resp = client.post(f"/api/v1/sessions/{session_id}/summary", headers=headers)
    assert summary_resp.status_code == 200
    summary_body = summary_resp.json()
    assert summary_body["opening_line"]
    assert summary_body["request_line"]

    reflection_resp = client.post(
        "/api/v1/reflections",
        headers=headers,
        json={
            "session_id": session_id,
            "used_in_real_world": True,
            "outcome_score": 4,
            "blocker_code": None,
            "blocker_note": None,
        },
    )
    assert reflection_resp.status_code == 201

    progress_resp = client.get(
        f"/api/v1/progress/weekly?week_start={date.today().isoformat()}",
        headers=headers,
    )
    assert progress_resp.status_code == 200
    progress = progress_resp.json()
    assert progress["practice_count"] >= 1
    assert progress["summary_count"] >= 1
    assert progress["real_world_used_count"] >= 1


def test_user_cannot_create_session_with_other_users_scene():
    client = TestClient(create_app())
    user_a_headers = _auth_headers("8a4c3f2a-2f88-4c74-9bc0-3123d26df302")
    user_b_headers = _auth_headers("0d365f2a-830d-4dbe-8884-59a6d5106dc4")

    scene_resp = client.post(
        "/api/v1/scenes",
        headers=user_a_headers,
        json={
            "title": "A 的场景",
            "template_id": "PEER_FEEDBACK",
            "counterparty_role": "PEER",
            "relationship_level": "NEUTRAL",
            "goal": "目标",
            "pain_points": [],
            "context": "上下文",
            "power_dynamic": "PEER_LEVEL",
        },
    )
    assert scene_resp.status_code == 201
    scene_id = scene_resp.json()["scene_id"]

    forbidden_resp = client.post(
        "/api/v1/sessions",
        headers=user_b_headers,
        json={"scene_id": scene_id, "target_turns": 6},
    )
    assert forbidden_resp.status_code == 404
    assert forbidden_resp.json()["error_code"] == "NOT_FOUND"
