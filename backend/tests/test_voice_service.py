import asyncio
from datetime import datetime, timezone

import pytest

from app.core.config import Settings


def _settings(**overrides):
    payload = {
        "APP_ENV": "test",
        "AUTH_MODE": "mock",
        "MOCK_AUTH_ENABLED": "true",
        "DATABASE_URL": "postgresql://postgres:postgres@127.0.0.1:5432/postgres",
        "CORS_ORIGINS": "*",
        "AGORA_APP_ID": "agora-app-id",
        "AGORA_APP_CERTIFICATE": "agora-cert",
    }
    payload.update(overrides)
    return Settings(**payload)


def test_generate_config_requires_agora_credentials():
    from app.services.voice_agent import VoiceAgentConfigurationError, VoiceAgentService

    service = VoiceAgentService(
        settings=_settings(AGORA_APP_ID="", AGORA_APP_CERTIFICATE="")
    )

    with pytest.raises(VoiceAgentConfigurationError):
        service.generate_config(
            channel_name="nvc-session-1",
            user_uid=1001,
            agent_uid=2002,
        )


def test_generate_config_returns_short_lived_rtc_rtm_token(monkeypatch):
    from app.services import voice_agent

    captured = {}

    def fake_generate_token(**kwargs):
        captured.update(kwargs)
        return "token-abc"

    monkeypatch.setattr(voice_agent, "_generate_convo_ai_token", fake_generate_token)

    service = voice_agent.VoiceAgentService(settings=_settings())
    result = service.generate_config(
        channel_name="nvc-session-1",
        user_uid=1001,
        agent_uid=2002,
        token_expire=3600,
    )

    assert result["app_id"] == "agora-app-id"
    assert result["token"] == "token-abc"
    assert result["uid"] == "1001"
    assert result["channel_name"] == "nvc-session-1"
    assert result["agent_uid"] == "2002"
    assert datetime.fromisoformat(result["expires_at"]) > datetime.now(timezone.utc)
    assert captured == {
        "app_id": "agora-app-id",
        "app_certificate": "agora-cert",
        "channel_name": "nvc-session-1",
        "uid": 1001,
        "token_expire": 3600,
    }


def test_start_agent_validates_positive_uids():
    from app.services.voice_agent import VoiceAgentService

    service = VoiceAgentService(settings=_settings())

    with pytest.raises(ValueError, match="agent_uid"):
        asyncio.run(
            service.start_agent(
                channel_name="nvc-session-1",
                agent_uid=0,
                user_uid=1001,
            )
        )

    with pytest.raises(ValueError, match="user_uid"):
        asyncio.run(
            service.start_agent(
                channel_name="nvc-session-1",
                agent_uid=2002,
                user_uid=0,
            )
        )


def test_start_agent_returns_agent_id_from_created_session(monkeypatch):
    from app.services import voice_agent

    captured = {}

    class FakeSession:
        async def start(self):
            return "agent-123"

    def fake_create_session(self, **kwargs):
        captured.update(kwargs)
        return FakeSession()

    monkeypatch.setattr(voice_agent.VoiceAgentService, "_create_session", fake_create_session)

    service = voice_agent.VoiceAgentService(settings=_settings())
    result = asyncio.run(
        service.start_agent(
            channel_name="nvc-session-1",
            agent_uid=2002,
            user_uid=1001,
        )
    )

    assert result == {
        "agent_id": "agent-123",
        "channel_name": "nvc-session-1",
        "status": "started",
    }
    assert captured["channel_name"] == "nvc-session-1"
    assert captured["agent_uid"] == 2002
    assert captured["user_uid"] == 1001


def test_create_session_uses_current_agora_agent_constructor(monkeypatch):
    from app.services import voice_agent
    from agora_agent import agentkit
    from agora_agent.agentkit import vendors

    captured = {}

    class FakeVendor:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeAgent:
        def __init__(self, *, client, instructions, greeting, failure_message, **kwargs):
            captured["constructor"] = {
                "client": client,
                "instructions": instructions,
                "greeting": greeting,
                "failure_message": failure_message,
                **kwargs,
            }

        def with_stt(self, vendor):
            captured["stt"] = vendor.kwargs
            return self

        def with_llm(self, vendor):
            captured["llm"] = vendor.kwargs
            return self

        def with_tts(self, vendor):
            captured["tts"] = vendor.kwargs
            return self

        def create_async_session(self, **kwargs):
            captured["session"] = kwargs
            return "session-object"

    monkeypatch.setattr(agentkit, "Agent", FakeAgent)
    monkeypatch.setattr(vendors, "DeepgramSTT", FakeVendor)
    monkeypatch.setattr(vendors, "OpenAI", FakeVendor)
    monkeypatch.setattr(vendors, "MiniMaxTTS", FakeVendor)

    service = voice_agent.VoiceAgentService(settings=_settings())
    service._client = object()
    result = service._create_session(
        channel_name="nvc-session-1",
        agent_uid=2002,
        user_uid=1001,
    )

    assert result == "session-object"
    assert captured["constructor"]["client"] is service._client
    assert "name" not in captured["constructor"]
    assert captured["session"]["name"].startswith("agent_nvc-session-1_2002_")
    assert captured["session"]["agent_uid"] == "2002"
    assert captured["session"]["remote_uids"] == ["1001"]


def test_stop_agent_uses_stateless_client_and_treats_conflict_as_success():
    from app.services.voice_agent import VoiceAgentService

    class ConflictError(Exception):
        body = {"detail": "ErrConflict: agent is shutting down"}

    class FakeClient:
        def __init__(self):
            self.agent_ids = []

        async def stop_agent(self, agent_id):
            self.agent_ids.append(agent_id)
            raise ConflictError()

    fake_client = FakeClient()
    service = VoiceAgentService(settings=_settings())
    service._client = fake_client

    asyncio.run(service.stop_agent("agent-123"))

    assert fake_client.agent_ids == ["agent-123"]
