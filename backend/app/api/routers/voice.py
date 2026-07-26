import json
import random
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import AuthUser
from app.db.security import apply_request_rls_context
from app.db.session import get_db_session
from app.db.utils import ensure_user_exists, get_scene_owned_by_user, get_session_owned_by_user
from app.schemas.voice import (
    VoiceSessionStartRequest,
    VoiceSessionStartResponse,
    VoiceSessionStopResponse,
    VoiceTranscriptSyncRequest,
    VoiceTranscriptSyncResponse,
)
from app.services.nvc_service import analyze_message
from app.services.voice_agent import VoiceAgentConfigurationError, VoiceAgentService

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])
voice_agent_service = VoiceAgentService()


def _rtc_uid() -> int:
    return random.randint(1000, 9999999)


def _allocate_rtc_uids() -> tuple[int, int]:
    user_uid = _rtc_uid()
    agent_uid = _rtc_uid()
    while agent_uid == user_uid:
        agent_uid = _rtc_uid()
    return user_uid, agent_uid


@router.post(
    "/sessions",
    response_model=VoiceSessionStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_voice_session(
    payload: VoiceSessionStartRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> VoiceSessionStartResponse:
    await apply_request_rls_context(db, user)
    await ensure_user_exists(db, user)

    scene = await get_scene_owned_by_user(db, payload.scene_id, user.user_id)
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scene not found")
    if scene["status"] != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="scene is not active")

    session_result = await db.execute(
        text(
            """
            INSERT INTO sessions (user_id, scene_id, state, target_turns, current_turn, modality)
            VALUES (:user_id, :scene_id, 'ACTIVE', :target_turns, 0, :modality)
            RETURNING id, state, current_turn, created_at
            """
        ),
        {
            "user_id": str(user.user_id),
            "scene_id": str(payload.scene_id),
            "target_turns": payload.target_turns,
            "modality": "VOICE",
        },
    )
    session = session_result.mappings().one()
    session_id = session["id"]
    channel_name = f"nvc-{session_id}"
    user_uid, agent_uid = _allocate_rtc_uids()

    try:
        config = voice_agent_service.generate_config(
            channel_name=channel_name,
            user_uid=user_uid,
            agent_uid=agent_uid,
        )
        start_result = await voice_agent_service.start_agent(
            channel_name=channel_name,
            agent_uid=agent_uid,
            user_uid=user_uid,
        )
    except VoiceAgentConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="voice agent service unavailable",
        ) from exc
    agent_id = start_result["agent_id"]

    try:
        await db.execute(
            text(
                """
                UPDATE sessions
                SET voice_channel_name = :voice_channel_name,
                    voice_agent_id = :voice_agent_id,
                    voice_user_uid = :voice_user_uid,
                    voice_agent_uid = :voice_agent_uid,
                    voice_status = 'STARTED',
                    voice_started_at = NOW(),
                    voice_expires_at = :voice_expires_at
                WHERE id = :session_id
                """
            ),
            {
                "voice_channel_name": channel_name,
                "voice_agent_id": agent_id,
                "voice_user_uid": str(user_uid),
                "voice_agent_uid": str(agent_uid),
                "voice_expires_at": datetime.fromisoformat(config["expires_at"]),
                "session_id": str(session_id),
            },
        )
        await db.commit()
    except Exception:
        await voice_agent_service.stop_agent(agent_id)
        raise

    return VoiceSessionStartResponse(
        session_id=session_id,
        app_id=config["app_id"],
        token=config["token"],
        uid=config["uid"],
        channel_name=config["channel_name"],
        agent_uid=config["agent_uid"],
        agent_id=agent_id,
        expires_at=config["expires_at"],
    )


@router.post(
    "/sessions/{session_id}/stop",
    response_model=VoiceSessionStopResponse,
)
async def stop_voice_session(
    session_id: UUID,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> VoiceSessionStopResponse:
    await apply_request_rls_context(db, user)

    session = await get_session_owned_by_user(db, session_id, user.user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    if session.get("modality") != "VOICE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="session is not a voice session",
        )

    agent_id = session.get("voice_agent_id")
    if agent_id:
        try:
            await voice_agent_service.stop_agent(agent_id)
        except Exception:
            # 远端停不掉不阻塞本地收尾；agent 有 idle_timeout 会自动退出
            pass

    final_state = "COMPLETED" if session["state"] == "COMPLETED" else "ABANDONED"
    await db.execute(
        text(
            """
            UPDATE sessions
            SET voice_status = 'STOPPED',
                voice_ended_at = NOW(),
                ended_at = COALESCE(ended_at, NOW()),
                state = :state
            WHERE id = :session_id
            """
        ),
        {
            "state": final_state,
            "session_id": str(session_id),
        },
    )
    await db.commit()
    return VoiceSessionStopResponse(session_id=session_id, status="STOPPED")


@router.post(
    "/sessions/{session_id}/transcripts",
    response_model=VoiceTranscriptSyncResponse,
)
async def sync_voice_transcripts(
    session_id: UUID,
    payload: VoiceTranscriptSyncRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> VoiceTranscriptSyncResponse:
    await apply_request_rls_context(db, user)

    session = await get_session_owned_by_user(db, session_id, user.user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    if session.get("modality") != "VOICE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="session is not a voice session",
        )
    if session["state"] not in {"ACTIVE", "COMPLETED"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"session is {session['state'].lower()}",
        )

    inserted_count = 0
    current_turn = int(session["current_turn"] or 0)

    for turn in payload.turns:
        turn_no = current_turn + 1 if turn.role == "USER" else max(current_turn, 1)
        inserted = await _insert_transcript_message(
            db=db,
            session_id=session_id,
            role=turn.role,
            turn_no=turn_no,
            content=turn.content,
            external_turn_id=turn.external_turn_id,
            metadata=turn.metadata,
        )
        if inserted:
            inserted_count += 1
            if turn.role == "USER":
                current_turn += 1
                analysis = analyze_message(turn.content)
                await _insert_feedback(
                    db=db,
                    session_id=session_id,
                    user_message_id=inserted,
                    analysis=analysis,
                )

    completed = current_turn >= int(session["target_turns"])
    next_state = "COMPLETED" if completed else session["state"]
    await db.execute(
        text(
            """
            UPDATE sessions
            SET current_turn = :current_turn,
                state = :state,
                ended_at = CASE WHEN :completed THEN COALESCE(ended_at, NOW()) ELSE ended_at END
            WHERE id = :session_id
            """
        ),
        {
            "current_turn": current_turn,
            "state": next_state,
            "completed": completed,
            "session_id": str(session_id),
        },
    )
    await db.commit()
    return VoiceTranscriptSyncResponse(
        session_id=session_id,
        inserted_count=inserted_count,
        current_turn=current_turn,
        state=next_state,
    )


async def _insert_transcript_message(
    *,
    db: AsyncSession,
    session_id: UUID,
    role: str,
    turn_no: int,
    content: str,
    external_turn_id: str,
    metadata: dict,
):
    result = await db.execute(
        text(
            """
            INSERT INTO messages (session_id, role, turn_no, content, source, external_turn_id, metadata)
            VALUES (
                :session_id,
                :role,
                :turn_no,
                :content,
                'VOICE_TRANSCRIPT',
                :external_turn_id,
                CAST(:metadata AS jsonb)
            )
            ON CONFLICT (session_id, external_turn_id, role)
            WHERE external_turn_id IS NOT NULL
            DO NOTHING
            RETURNING id
            """
        ),
        {
            "session_id": str(session_id),
            "role": role,
            "turn_no": turn_no,
            "content": content,
            "external_turn_id": external_turn_id,
            "metadata": json.dumps(metadata),
        },
    )
    try:
        return result.scalar_one()
    except NoResultFound:
        return None


async def _insert_feedback(*, db: AsyncSession, session_id: UUID, user_message_id, analysis) -> None:
    await db.execute(
        text(
            """
            INSERT INTO feedback_items (
                session_id,
                user_message_id,
                overall_score,
                risk_level,
                ofnr_detail,
                next_best_sentence
            )
            VALUES (
                :session_id,
                :user_message_id,
                :overall_score,
                :risk_level,
                CAST(:ofnr_detail AS jsonb),
                :next_best_sentence
            )
            ON CONFLICT (user_message_id) DO NOTHING
            """
        ),
        {
            "session_id": str(session_id),
            "user_message_id": str(user_message_id),
            "overall_score": analysis.feedback.overall_score,
            "risk_level": analysis.feedback.risk_level.value,
            "ofnr_detail": json.dumps(analysis.feedback.ofnr.model_dump(mode="json")),
            "next_best_sentence": analysis.feedback.next_best_sentence,
        },
    )
