import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.security import AuthUser
from app.main import create_app


TEST_USER_ID = UUID("8a4c3f2a-2f88-4c74-9bc0-3123d26df302")
TEST_HEADERS = {"Authorization": f"Bearer mock_{TEST_USER_ID}"}


class FakeMappings:
    def __init__(self, rows):
        self.rows = rows

    def one(self):
        if not self.rows:
            raise AssertionError("expected one row")
        return self.rows[0]

    def first(self):
        return self.rows[0] if self.rows else None


class FakeResult:
    def __init__(self, rows=None, scalar_value=None):
        self.rows = rows or []
        self.scalar_value = scalar_value

    def mappings(self):
        return FakeMappings(self.rows)

    def scalar_one(self):
        return self.scalar_value


class FakeDb:
    def __init__(self):
        self.session_id = uuid4()
        self.user_message_id = uuid4()
        self.assistant_message_id = uuid4()
        self.executions = []
        self.commits = 0
        self.duplicate_external_turn_ids = set()
        self.fail_commit = False

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.executions.append((sql, params or {}))
        if "INSERT INTO sessions" in sql:
            return FakeResult(
                rows=[
                    {
                        "id": self.session_id,
                        "state": "ACTIVE",
                        "current_turn": 0,
                        "created_at": datetime.now(timezone.utc),
                    }
                ]
            )
        if "INSERT INTO messages" in sql:
            role = (params or {}).get("role")
            if (params or {}).get("external_turn_id") in self.duplicate_external_turn_ids:
                return FakeResult()
            return FakeResult(
                scalar_value=(
                    self.assistant_message_id if role == "ASSISTANT" else self.user_message_id
                )
            )
        return FakeResult()

    async def commit(self):
        if self.fail_commit:
            raise RuntimeError("commit failed")
        self.commits += 1


class FakeVoiceService:
    def __init__(self):
        self.started = []
        self.stopped = []

    def generate_config(self, *, channel_name, user_uid, agent_uid, token_expire=3600):
        return {
            "app_id": "agora-app-id",
            "token": "token-abc",
            "uid": str(user_uid),
            "channel_name": channel_name,
            "agent_uid": str(agent_uid),
            "expires_at": datetime.now(timezone.utc).isoformat(),
        }

    async def start_agent(self, *, channel_name, agent_uid, user_uid, output_audio_codec=None):
        self.started.append(
            {
                "channel_name": channel_name,
                "agent_uid": agent_uid,
                "user_uid": user_uid,
                "output_audio_codec": output_audio_codec,
            }
        )
        return {
            "agent_id": "agent-123",
            "channel_name": channel_name,
            "status": "started",
        }

    async def stop_agent(self, agent_id):
        self.stopped.append(agent_id)


def _user():
    return AuthUser(user_id=TEST_USER_ID, email="user@example.com", display_name="User")


def test_start_voice_session_requires_authentication():
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/voice/sessions",
        json={"scene_id": str(uuid4()), "target_turns": 6},
    )

    assert response.status_code == 401


def test_start_voice_session_creates_voice_session_and_starts_agent(monkeypatch):
    from app.api.routers import voice
    from app.schemas.voice import VoiceSessionStartRequest

    fake_db = FakeDb()
    fake_service = FakeVoiceService()
    scene_id = uuid4()

    async def noop(*args, **kwargs):
        return None

    async def fake_scene(*args, **kwargs):
        return {"id": scene_id, "status": "ACTIVE", "context": "场景"}

    monkeypatch.setattr(voice, "apply_request_rls_context", noop)
    monkeypatch.setattr(voice, "ensure_user_exists", noop)
    monkeypatch.setattr(voice, "get_scene_owned_by_user", fake_scene)
    monkeypatch.setattr(voice, "voice_agent_service", fake_service)

    response = asyncio.run(
        voice.start_voice_session(
            VoiceSessionStartRequest(scene_id=scene_id, target_turns=6),
            user=_user(),
            db=fake_db,
        )
    )

    assert response.session_id == fake_db.session_id
    assert response.agent_id == "agent-123"
    assert response.channel_name == f"nvc-{fake_db.session_id}"
    assert response.uid
    assert response.agent_uid
    assert fake_service.started == [
        {
            "channel_name": f"nvc-{fake_db.session_id}",
            "agent_uid": int(response.agent_uid),
            "user_uid": int(response.uid),
            "output_audio_codec": None,
        }
    ]
    session_insert = next(
        params for sql, params in fake_db.executions if "INSERT INTO sessions" in sql
    )
    assert session_insert["modality"] == "VOICE"
    assert session_insert["scene_id"] == str(scene_id)
    assert fake_db.commits == 1
    # Regression: voice_expires_at must be a datetime, not an isoformat string,
    # because asyncpg's TIMESTAMPTZ codec rejects str bindings.
    from datetime import datetime

    update_params = next(
        params for sql, params in fake_db.executions if "voice_expires_at" in sql
    )
    assert isinstance(update_params["voice_expires_at"], datetime)


def test_start_voice_session_rejects_unowned_scene(monkeypatch):
    from fastapi import HTTPException

    from app.api.routers import voice
    from app.schemas.voice import VoiceSessionStartRequest

    async def noop(*args, **kwargs):
        return None

    async def missing_scene(*args, **kwargs):
        return None

    monkeypatch.setattr(voice, "apply_request_rls_context", noop)
    monkeypatch.setattr(voice, "ensure_user_exists", noop)
    monkeypatch.setattr(voice, "get_scene_owned_by_user", missing_scene)

    try:
        asyncio.run(
            voice.start_voice_session(
                VoiceSessionStartRequest(scene_id=uuid4(), target_turns=6),
                user=_user(),
                db=FakeDb(),
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("expected HTTPException")


def test_start_voice_session_stops_agent_if_db_persist_fails(monkeypatch):
    from app.api.routers import voice
    from app.schemas.voice import VoiceSessionStartRequest

    fake_db = FakeDb()
    fake_db.fail_commit = True
    fake_service = FakeVoiceService()
    scene_id = uuid4()

    async def noop(*args, **kwargs):
        return None

    async def fake_scene(*args, **kwargs):
        return {"id": scene_id, "status": "ACTIVE", "context": "场景"}

    monkeypatch.setattr(voice, "apply_request_rls_context", noop)
    monkeypatch.setattr(voice, "ensure_user_exists", noop)
    monkeypatch.setattr(voice, "get_scene_owned_by_user", fake_scene)
    monkeypatch.setattr(voice, "voice_agent_service", fake_service)

    try:
        asyncio.run(
            voice.start_voice_session(
                VoiceSessionStartRequest(scene_id=scene_id, target_turns=6),
                user=_user(),
                db=fake_db,
            )
        )
    except RuntimeError as exc:
        assert str(exc) == "commit failed"
    else:
        raise AssertionError("expected RuntimeError")

    assert fake_service.stopped == ["agent-123"]


def test_stop_voice_session_uses_persisted_agent_id_and_is_idempotent(monkeypatch):
    from app.api.routers import voice

    fake_db = FakeDb()
    fake_service = FakeVoiceService()
    session_id = uuid4()

    async def noop(*args, **kwargs):
        return None

    async def fake_session(*args, **kwargs):
        return {
            "id": session_id,
            "user_id": TEST_USER_ID,
            "scene_id": uuid4(),
            "state": "ACTIVE",
            "modality": "VOICE",
            "target_turns": 6,
            "current_turn": 1,
            "voice_agent_id": "agent-123",
        }

    monkeypatch.setattr(voice, "apply_request_rls_context", noop)
    monkeypatch.setattr(voice, "get_session_owned_by_user", fake_session)
    monkeypatch.setattr(voice, "voice_agent_service", fake_service)

    response = asyncio.run(
        voice.stop_voice_session(
            session_id=session_id,
            user=_user(),
            db=fake_db,
        )
    )

    assert response.session_id == session_id
    assert response.status == "STOPPED"
    assert fake_service.stopped == ["agent-123"]
    update_params = next(
        params for sql, params in fake_db.executions if "voice_status = 'STOPPED'" in sql
    )
    assert update_params["session_id"] == str(session_id)
    assert fake_db.commits == 1


def test_start_voice_session_uses_distinct_rtc_uids(monkeypatch):
    from app.api.routers import voice
    from app.schemas.voice import VoiceSessionStartRequest

    fake_db = FakeDb()
    fake_service = FakeVoiceService()
    scene_id = uuid4()
    issued = iter([1234, 1234, 5678])

    async def noop(*args, **kwargs):
        return None

    async def fake_scene(*args, **kwargs):
        return {"id": scene_id, "status": "ACTIVE", "context": "场景"}

    monkeypatch.setattr(voice, "apply_request_rls_context", noop)
    monkeypatch.setattr(voice, "ensure_user_exists", noop)
    monkeypatch.setattr(voice, "get_scene_owned_by_user", fake_scene)
    monkeypatch.setattr(voice, "voice_agent_service", fake_service)
    monkeypatch.setattr(voice, "_rtc_uid", lambda: next(issued))

    response = asyncio.run(
        voice.start_voice_session(
            VoiceSessionStartRequest(scene_id=scene_id, target_turns=6),
            user=_user(),
            db=fake_db,
        )
    )

    assert response.uid == "1234"
    assert response.agent_uid == "5678"


def test_stop_voice_session_rejects_text_session(monkeypatch):
    from fastapi import HTTPException

    from app.api.routers import voice

    fake_service = FakeVoiceService()
    session_id = uuid4()

    async def noop(*args, **kwargs):
        return None

    async def fake_session(*args, **kwargs):
        return {
            "id": session_id,
            "user_id": TEST_USER_ID,
            "scene_id": uuid4(),
            "state": "ACTIVE",
            "modality": "TEXT",
            "target_turns": 6,
            "current_turn": 1,
            "voice_agent_id": None,
        }

    monkeypatch.setattr(voice, "apply_request_rls_context", noop)
    monkeypatch.setattr(voice, "get_session_owned_by_user", fake_session)
    monkeypatch.setattr(voice, "voice_agent_service", fake_service)

    try:
        asyncio.run(
            voice.stop_voice_session(
                session_id=session_id,
                user=_user(),
                db=FakeDb(),
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("expected HTTPException")
    assert fake_service.stopped == []


def test_sync_voice_transcripts_inserts_messages_feedback_and_updates_turn(monkeypatch):
    from app.api.routers import voice
    from app.schemas.voice import VoiceTranscriptSyncRequest, VoiceTranscriptTurn

    fake_db = FakeDb()
    session_id = uuid4()

    async def noop(*args, **kwargs):
        return None

    async def fake_session(*args, **kwargs):
        return {
            "id": session_id,
            "user_id": TEST_USER_ID,
            "scene_id": uuid4(),
            "state": "ACTIVE",
            "modality": "VOICE",
            "target_turns": 6,
            "current_turn": 0,
            "voice_agent_id": "agent-123",
        }

    monkeypatch.setattr(voice, "apply_request_rls_context", noop)
    monkeypatch.setattr(voice, "get_session_owned_by_user", fake_session)

    response = asyncio.run(
        voice.sync_voice_transcripts(
            session_id=session_id,
            payload=VoiceTranscriptSyncRequest(
                turns=[
                    VoiceTranscriptTurn(
                        role="USER",
                        content="你们总是拖延，根本不专业。",
                        external_turn_id="turn-1-user",
                        metadata={"rtm_ts": 123},
                    ),
                    VoiceTranscriptTurn(
                        role="ASSISTANT",
                        content="我听到你很着急，我们先把观察和感受分开。",
                        external_turn_id="turn-1-agent",
                    ),
                ]
            ),
            user=_user(),
            db=fake_db,
        )
    )

    assert response.session_id == session_id
    assert response.inserted_count == 2
    assert response.current_turn == 1
    inserted_roles = [
        params["role"] for sql, params in fake_db.executions if "INSERT INTO messages" in sql
    ]
    assert inserted_roles == ["USER", "ASSISTANT"]
    assert any("INSERT INTO feedback_items" in sql for sql, _ in fake_db.executions)
    assert any("SET current_turn = :current_turn" in sql for sql, _ in fake_db.executions)
    assert fake_db.commits == 1


def test_sync_voice_transcripts_does_not_increment_turn_for_duplicate_user_turn(
    monkeypatch,
):
    from app.api.routers import voice
    from app.schemas.voice import VoiceTranscriptSyncRequest, VoiceTranscriptTurn

    fake_db = FakeDb()
    fake_db.duplicate_external_turn_ids.add("turn-1-user")
    session_id = uuid4()

    async def noop(*args, **kwargs):
        return None

    async def fake_session(*args, **kwargs):
        return {
            "id": session_id,
            "user_id": TEST_USER_ID,
            "scene_id": uuid4(),
            "state": "ACTIVE",
            "modality": "VOICE",
            "target_turns": 6,
            "current_turn": 1,
            "voice_agent_id": "agent-123",
        }

    monkeypatch.setattr(voice, "apply_request_rls_context", noop)
    monkeypatch.setattr(voice, "get_session_owned_by_user", fake_session)

    response = asyncio.run(
        voice.sync_voice_transcripts(
            session_id=session_id,
            payload=VoiceTranscriptSyncRequest(
                turns=[
                    VoiceTranscriptTurn(
                        role="USER",
                        content="你们总是拖延，根本不专业。",
                        external_turn_id="turn-1-user",
                    )
                ]
            ),
            user=_user(),
            db=fake_db,
        )
    )

    assert response.inserted_count == 0
    assert response.current_turn == 1
    assert not any("INSERT INTO feedback_items" in sql for sql, _ in fake_db.executions)
