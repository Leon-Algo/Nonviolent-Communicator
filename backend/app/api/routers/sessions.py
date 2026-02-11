import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.db.utils import ensure_user_exists, get_scene_owned_by_user, get_session_owned_by_user
from app.core.security import AuthUser
from app.schemas.sessions import (
    AssistantMessage,
    MessageCreateRequest,
    MessageCreateResponse,
    RewriteCreateRequest,
    RewriteCreateResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionState,
    SummaryCreateResponse,
)
from app.services.nvc_service import (
    analyze_message,
    generate_assistant_reply,
    generate_rewrite,
)

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])
MESSAGE_ENDPOINT_KEY = "POST:/api/v1/sessions/{session_id}/messages"


async def _get_idempotent_message_response(
    db: AsyncSession,
    user_id: UUID,
    session_id: UUID,
    client_message_id: UUID,
) -> MessageCreateResponse | None:
    existing_result = await db.execute(
        text(
            """
            SELECT response_body
            FROM idempotency_keys
            WHERE user_id = :user_id
              AND session_id = :session_id
              AND endpoint = :endpoint
              AND client_message_id = :client_message_id
            LIMIT 1
            """
        ),
        {
            "user_id": str(user_id),
            "session_id": str(session_id),
            "endpoint": MESSAGE_ENDPOINT_KEY,
            "client_message_id": str(client_message_id),
        },
    )
    row = existing_result.mappings().first()
    if not row:
        return None
    return MessageCreateResponse.model_validate(row["response_body"])


@router.post("", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreateRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SessionCreateResponse:
    await ensure_user_exists(db, user)

    scene = await get_scene_owned_by_user(db, payload.scene_id, user.user_id)
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scene not found")
    if scene["status"] != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="scene is not active")

    result = await db.execute(
        text(
            """
            INSERT INTO sessions (user_id, scene_id, state, target_turns, current_turn)
            VALUES (:user_id, :scene_id, 'ACTIVE', :target_turns, 0)
            RETURNING id, state, current_turn, created_at
            """
        ),
        {
            "user_id": str(user.user_id),
            "scene_id": str(payload.scene_id),
            "target_turns": payload.target_turns,
        },
    )
    row = result.mappings().one()
    await db.commit()

    return SessionCreateResponse(
        session_id=row["id"],
        state=SessionState(row["state"]),
        current_turn=row["current_turn"],
        created_at=row["created_at"],
    )


@router.post("/{session_id}/messages", response_model=MessageCreateResponse)
async def create_session_message(
    session_id: UUID,
    payload: MessageCreateRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MessageCreateResponse:
    await ensure_user_exists(db, user)
    session = await get_session_owned_by_user(db, session_id, user.user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    if session["state"] != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"session is {session['state'].lower()}",
        )

    scene = await get_scene_owned_by_user(db, session["scene_id"], user.user_id)
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scene not found")

    existing_response = await _get_idempotent_message_response(
        db=db,
        user_id=user.user_id,
        session_id=session_id,
        client_message_id=payload.client_message_id,
    )
    if existing_response:
        return existing_response

    turn = int(session["current_turn"]) + 1

    user_message_result = await db.execute(
        text(
            """
            INSERT INTO messages (session_id, role, turn_no, content)
            VALUES (:session_id, 'USER', :turn_no, :content)
            RETURNING id
            """
        ),
        {
            "session_id": str(session_id),
            "turn_no": turn,
            "content": payload.content,
        },
    )
    user_message_id = user_message_result.scalar_one()

    assistant_content = await generate_assistant_reply(scene["context"], payload.content)
    assistant_message_result = await db.execute(
        text(
            """
            INSERT INTO messages (session_id, role, turn_no, content)
            VALUES (:session_id, 'ASSISTANT', :turn_no, :content)
            RETURNING id
            """
        ),
        {
            "session_id": str(session_id),
            "turn_no": turn,
            "content": assistant_content,
        },
    )
    assistant_message_id = assistant_message_result.scalar_one()

    analysis = analyze_message(payload.content)
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

    new_state = "COMPLETED" if turn >= int(session["target_turns"]) else "ACTIVE"
    is_completed = new_state == "COMPLETED"
    await db.execute(
        text(
            """
            UPDATE sessions
            SET current_turn = :current_turn,
                state = :state,
                ended_at = CASE WHEN :is_completed THEN NOW() ELSE ended_at END
            WHERE id = :session_id
            """
        ),
        {
            "current_turn": turn,
            "state": new_state,
            "is_completed": is_completed,
            "session_id": str(session_id),
        },
    )
    response = MessageCreateResponse(
        user_message_id=user_message_id,
        assistant_message=AssistantMessage(
            message_id=assistant_message_id,
            content=assistant_content,
        ),
        feedback=analysis.feedback,
        turn=turn,
    )
    try:
        await db.execute(
            text(
                """
                INSERT INTO idempotency_keys (
                    user_id,
                    session_id,
                    endpoint,
                    client_message_id,
                    response_body
                )
                VALUES (
                    :user_id,
                    :session_id,
                    :endpoint,
                    :client_message_id,
                    CAST(:response_body AS jsonb)
                )
                """
            ),
            {
                "user_id": str(user.user_id),
                "session_id": str(session_id),
                "endpoint": MESSAGE_ENDPOINT_KEY,
                "client_message_id": str(payload.client_message_id),
                "response_body": json.dumps(response.model_dump(mode="json")),
            },
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing_response = await _get_idempotent_message_response(
            db=db,
            user_id=user.user_id,
            session_id=session_id,
            client_message_id=payload.client_message_id,
        )
        if existing_response:
            return existing_response
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="duplicate client message id",
        )

    return response


@router.post("/{session_id}/rewrite", response_model=RewriteCreateResponse)
async def rewrite_session_message(
    session_id: UUID,
    payload: RewriteCreateRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> RewriteCreateResponse:
    session = await get_session_owned_by_user(db, session_id, user.user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")

    message_result = await db.execute(
        text(
            """
            SELECT id, content
            FROM messages
            WHERE id = :message_id
              AND session_id = :session_id
              AND role = 'USER'
            LIMIT 1
            """
        ),
        {"message_id": str(payload.source_message_id), "session_id": str(session_id)},
    )
    message = message_result.mappings().first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="source user message not found",
        )

    rewritten_content = await generate_rewrite(message["content"])
    rewrite_result = await db.execute(
        text(
            """
            INSERT INTO rewrites (session_id, source_message_id, rewrite_style, rewritten_content)
            VALUES (:session_id, :source_message_id, :rewrite_style, :rewritten_content)
            RETURNING id
            """
        ),
        {
            "session_id": str(session_id),
            "source_message_id": str(payload.source_message_id),
            "rewrite_style": payload.rewrite_style.value,
            "rewritten_content": rewritten_content,
        },
    )
    rewrite_id = rewrite_result.scalar_one()
    await db.commit()

    return RewriteCreateResponse(rewrite_id=rewrite_id, rewritten_content=rewritten_content)


@router.post("/{session_id}/summary", response_model=SummaryCreateResponse)
async def create_session_summary(
    session_id: UUID,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SummaryCreateResponse:
    session = await get_session_owned_by_user(db, session_id, user.user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")

    existing_summary_result = await db.execute(
        text(
            """
            SELECT id, opening_line, request_line, fallback_line, risk_triggers, created_at
            FROM summaries
            WHERE session_id = :session_id
            LIMIT 1
            """
        ),
        {"session_id": str(session_id)},
    )
    existing_summary = existing_summary_result.mappings().first()
    if existing_summary:
        return SummaryCreateResponse(
            summary_id=existing_summary["id"],
            opening_line=existing_summary["opening_line"],
            request_line=existing_summary["request_line"],
            fallback_line=existing_summary["fallback_line"] or "",
            risk_triggers=existing_summary["risk_triggers"] or [],
            created_at=existing_summary["created_at"],
        )

    feedback_result = await db.execute(
        text(
            """
            SELECT f.next_best_sentence, m.content AS user_content
            FROM feedback_items f
            JOIN messages m ON m.id = f.user_message_id
            WHERE f.session_id = :session_id
            ORDER BY f.created_at DESC
            LIMIT 1
            """
        ),
        {"session_id": str(session_id)},
    )
    feedback_row = feedback_result.mappings().first()
    if not feedback_row:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="session has no feedback yet",
        )

    sentence = feedback_row["next_best_sentence"]
    parts = [p.strip() for p in sentence.replace("？", "?").split("。") if p.strip()]
    opening_line = parts[0] if parts else sentence
    request_line = parts[1] if len(parts) > 1 else "你愿意和我一起确认下一步安排吗？"
    fallback_line = "如果现在不方便，我们可否约一个具体时间再对齐？"

    risk_triggers = analyze_message(feedback_row["user_content"]).risk_triggers
    summary_result = await db.execute(
        text(
            """
            INSERT INTO summaries (
                session_id,
                opening_line,
                request_line,
                fallback_line,
                risk_triggers
            )
            VALUES (
                :session_id,
                :opening_line,
                :request_line,
                :fallback_line,
                CAST(:risk_triggers AS jsonb)
            )
            RETURNING id, created_at
            """
        ),
        {
            "session_id": str(session_id),
            "opening_line": opening_line,
            "request_line": request_line,
            "fallback_line": fallback_line,
            "risk_triggers": json.dumps(risk_triggers),
        },
    )
    summary_row = summary_result.mappings().one()
    await db.commit()

    return SummaryCreateResponse(
        summary_id=summary_row["id"],
        opening_line=opening_line,
        request_line=request_line,
        fallback_line=fallback_line,
        risk_triggers=risk_triggers,
        created_at=summary_row["created_at"],
    )
