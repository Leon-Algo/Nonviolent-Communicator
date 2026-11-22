import time
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import Settings, settings
from app.services.coach_prompt import VOICE_COACH_PROMPT as NVC_COACH_PROMPT

# 教练人格来自共享的 coach_prompt（知识源：nvc-coach skill）。
# 保留别名 NVC_COACH_PROMPT 以兼容既有引用与测试。


class VoiceAgentConfigurationError(RuntimeError):
    """Raised when Agora voice credentials are missing or unusable."""


def _generate_convo_ai_token(**kwargs) -> str:
    from agora_agent.agentkit.token import generate_convo_ai_token

    try:
        return generate_convo_ai_token(**kwargs)
    except TypeError as exc:
        if "unexpected keyword argument 'uid'" not in str(exc):
            raise
        legacy_kwargs = dict(kwargs)
        legacy_kwargs["account"] = str(legacy_kwargs.pop("uid"))
        return generate_convo_ai_token(**legacy_kwargs)


class VoiceAgentService:
    def __init__(self, settings: Settings = settings):
        self.settings = settings
        self._client = None

    def _credentials(self) -> tuple[str, str]:
        app_id = (self.settings.agora_app_id or "").strip()
        app_certificate = (self.settings.agora_app_certificate or "").strip()
        if not app_id or not app_certificate:
            raise VoiceAgentConfigurationError("Agora voice credentials are not configured")
        return app_id, app_certificate

    def generate_config(
        self,
        *,
        channel_name: str,
        user_uid: int,
        agent_uid: int,
        token_expire: int = 3600,
    ) -> dict[str, str]:
        if user_uid <= 0:
            raise ValueError("user_uid must be positive")
        if agent_uid <= 0:
            raise ValueError("agent_uid must be positive")
        normalized_channel = channel_name.strip()
        if not normalized_channel:
            raise ValueError("channel_name is required")

        app_id, app_certificate = self._credentials()
        token = _generate_convo_ai_token(
            app_id=app_id,
            app_certificate=app_certificate,
            channel_name=normalized_channel,
            uid=user_uid,
            token_expire=token_expire,
        )
        expires_at = datetime.now(UTC) + timedelta(seconds=token_expire)
        return {
            "app_id": app_id,
            "token": token,
            "uid": str(user_uid),
            "channel_name": normalized_channel,
            "agent_uid": str(agent_uid),
            "expires_at": expires_at.isoformat(),
        }

    async def start_agent(
        self,
        *,
        channel_name: str,
        agent_uid: int,
        user_uid: int,
        output_audio_codec: str | None = None,
    ) -> dict[str, str]:
        if agent_uid <= 0:
            raise ValueError("agent_uid must be positive")
        if user_uid <= 0:
            raise ValueError("user_uid must be positive")
        if not channel_name.strip():
            raise ValueError("channel_name is required")

        session = self._create_session(
            channel_name=channel_name.strip(),
            agent_uid=agent_uid,
            user_uid=user_uid,
            output_audio_codec=output_audio_codec,
        )
        agent_id = await session.start()
        return {
            "agent_id": agent_id,
            "channel_name": channel_name.strip(),
            "status": "started",
        }

    async def stop_agent(self, agent_id: str) -> None:
        normalized_agent_id = agent_id.strip()
        if not normalized_agent_id:
            raise ValueError("agent_id is required")

        try:
            await self.client.stop_agent(normalized_agent_id)
        except Exception as exc:
            detail = self._exception_detail(exc)
            if "ErrConflict" in detail or "shutting down" in detail:
                return
            raise

    @property
    def client(self):
        if self._client is None:
            app_id, app_certificate = self._credentials()
            from agora_agent import Area, AsyncAgora

            self._client = AsyncAgora(
                area=getattr(Area, self.settings.agora_area, Area.US),
                app_id=app_id,
                app_certificate=app_certificate,
            )
        return self._client

    def _create_session(
        self,
        *,
        channel_name: str,
        agent_uid: int,
        user_uid: int,
        output_audio_codec: str | None = None,
    ):
        from agora_agent.agentkit import Agent as AgoraAgent
        from agora_agent.agentkit.vendors import DeepgramSTT, MiniMaxTTS, OpenAI

        parameters: dict[str, Any] = {
            "data_channel": "rtm",
            "enable_error_message": True,
            "enable_metrics": True,
        }
        if output_audio_codec and output_audio_codec.strip():
            parameters["output_audio_codec"] = output_audio_codec.strip()

        agent_name = f"agent_{channel_name}_{agent_uid}_{int(time.time())}"
        agora_agent = AgoraAgent(
            client=self.client,
            instructions=NVC_COACH_PROMPT,
            greeting=self.settings.agent_greeting,
            failure_message="Please wait a moment.",
            max_history=50,
            turn_detection={
                "config": {
                    "speech_threshold": 0.5,
                    "start_of_speech": {
                        "mode": "vad",
                        "vad_config": {
                            "interrupt_duration_ms": 160,
                            "prefix_padding_ms": 300,
                        },
                    },
                    "end_of_speech": {
                        "mode": "vad",
                        "vad_config": {
                            "silence_duration_ms": 480,
                        },
                    },
                },
            },
            advanced_features={"enable_rtm": True, "enable_tools": True},
            parameters=parameters,
        )
        agora_agent = (
            agora_agent
            .with_stt(DeepgramSTT(model="nova-3", language="zh"))
            .with_llm(
                OpenAI(
                    model="gpt-4o-mini",
                    greeting_message=self.settings.agent_greeting,
                    failure_message="Please wait a moment.",
                    max_history=15,
                    max_tokens=1024,
                    temperature=0.7,
                    top_p=0.95,
                )
            )
            .with_tts(
                MiniMaxTTS(
                    model="speech_2_6_turbo",
                    voice_id="Chinese (Mandarin)_Warm_Girl",
                )
            )
        )
        return agora_agent.create_async_session(
            channel=channel_name,
            agent_uid=str(agent_uid),
            remote_uids=[str(user_uid)],
            name=agent_name,
            enable_string_uid=False,
            idle_timeout=30,
            expires_in=3600,
        )

    @staticmethod
    def _exception_detail(exc: Exception) -> str:
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            return str(body.get("detail", ""))
        return str(exc)
