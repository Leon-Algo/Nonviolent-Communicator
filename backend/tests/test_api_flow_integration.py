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

    history_list_resp = client.get("/api/v1/sessions?limit=10&offset=0", headers=headers)
    assert history_list_resp.status_code == 200
    history_list = history_list_resp.json()
    assert history_list["total"] >= 1
    assert len(history_list["items"]) >= 1
    assert history_list["items"][0]["session_id"] == session_id
    assert history_list["items"][0]["scene_id"] == scene_id
    assert history_list["items"][0]["scene_title"] == "和同事沟通延期风险"
    assert history_list["items"][0]["has_summary"] is True
    assert history_list["items"][0]["has_reflection"] is True

    history_detail_resp = client.get(f"/api/v1/sessions/{session_id}/history", headers=headers)
    assert history_detail_resp.status_code == 200
    history_detail = history_detail_resp.json()
    assert history_detail["session_id"] == session_id
    assert history_detail["scene"]["scene_id"] == scene_id
    assert history_detail["scene"]["title"] == "和同事沟通延期风险"
    assert history_detail["summary"]["summary_id"] == summary_body["summary_id"]
    assert history_detail["reflection"]["used_in_real_world"] is True
    assert len(history_detail["turns"]) >= 1
    first_turn = history_detail["turns"][0]
    assert first_turn["turn"] == 1
    assert first_turn["user_content"] == "你们总是拖延，根本不专业。"
    assert first_turn["assistant_content"]
    assert first_turn["feedback"]["overall_score"] >= 0

    second_scene_resp = client.post(
        "/api/v1/scenes",
        headers=headers,
        json={
            "title": "跨团队冲突同步",
            "template_id": "CROSS_TEAM_CONFLICT",
            "counterparty_role": "OTHER",
            "relationship_level": "TENSE",
            "goal": "对齐接口交付边界",
            "pain_points": ["双方都在甩锅"],
            "context": "跨团队接口时间反复变化。",
            "power_dynamic": "PEER_LEVEL",
        },
    )
    assert second_scene_resp.status_code == 201
    second_scene_id = second_scene_resp.json()["scene_id"]

    second_session_resp = client.post(
        "/api/v1/sessions",
        headers=headers,
        json={"scene_id": second_scene_id, "target_turns": 6},
    )
    assert second_session_resp.status_code == 201
    second_session_id = second_session_resp.json()["session_id"]

    second_msg_resp = client.post(
        f"/api/v1/sessions/{second_session_id}/messages",
        headers=headers,
        json={
            "client_message_id": str(uuid4()),
            "content": "我们先把责任边界和接口时间点对齐。",
        },
    )
    assert second_msg_resp.status_code == 200

    _run_sql(
        f"""
        UPDATE sessions
        SET state = 'ABANDONED',
            created_at = NOW() - INTERVAL '3 day'
        WHERE id = '{second_session_id}'
        """
    )

    abandoned_list_resp = client.get(
        "/api/v1/sessions?limit=10&offset=0&state=ABANDONED",
        headers=headers,
    )
    assert abandoned_list_resp.status_code == 200
    abandoned_list = abandoned_list_resp.json()
    assert abandoned_list["total"] == 1
    assert abandoned_list["items"][0]["session_id"] == second_session_id
    assert abandoned_list["items"][0]["state"] == "ABANDONED"

    keyword_list_resp = client.get(
        "/api/v1/sessions?limit=10&offset=0&keyword=%E8%B7%A8%E5%9B%A2%E9%98%9F",
        headers=headers,
    )
    assert keyword_list_resp.status_code == 200
    keyword_list = keyword_list_resp.json()
    assert keyword_list["total"] == 1
    assert keyword_list["items"][0]["session_id"] == second_session_id

    today = date.today().isoformat()
    date_window_resp = client.get(
        f"/api/v1/sessions?limit=10&offset=0&created_from={today}&created_to={today}",
        headers=headers,
    )
    assert date_window_resp.status_code == 200
    date_window = date_window_resp.json()
    assert date_window["total"] >= 1
    assert all(item["session_id"] != second_session_id for item in date_window["items"])

    invalid_window_resp = client.get(
        f"/api/v1/sessions?limit=10&offset=0&created_from={today}&created_to=2020-01-01",
        headers=headers,
    )
    assert invalid_window_resp.status_code == 400
    assert invalid_window_resp.json()["error_code"] == "VALIDATION_ERROR"


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

    session_resp = client.post(
        "/api/v1/sessions",
        headers=user_a_headers,
        json={"scene_id": scene_id, "target_turns": 6},
    )
    assert session_resp.status_code == 201
    session_id = session_resp.json()["session_id"]

    user_a_message_resp = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        headers=user_a_headers,
        json={
            "client_message_id": str(uuid4()),
            "content": "这是 A 的第一条消息。",
        },
    )
    assert user_a_message_resp.status_code == 200

    user_b_history_detail = client.get(
        f"/api/v1/sessions/{session_id}/history",
        headers=user_b_headers,
    )
    assert user_b_history_detail.status_code == 404
    assert user_b_history_detail.json()["error_code"] == "NOT_FOUND"

    user_b_history_list = client.get("/api/v1/sessions?limit=10&offset=0", headers=user_b_headers)
    assert user_b_history_list.status_code == 200
    assert user_b_history_list.json()["total"] == 0
