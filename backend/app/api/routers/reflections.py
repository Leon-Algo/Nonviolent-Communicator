from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.db.utils import ensure_user_exists, get_session_owned_by_user
from app.core.security import AuthUser
from app.schemas.reflections import ReflectionCreateRequest, ReflectionCreateResponse

router = APIRouter(prefix="/api/v1/reflections", tags=["reflections"])


@router.post("", response_model=ReflectionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_reflection(
    payload: ReflectionCreateRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ReflectionCreateResponse:
    await ensure_user_exists(db, user)
    session = await get_session_owned_by_user(db, payload.session_id, user.user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")

    try:
        result = await db.execute(
            text(
                """
                INSERT INTO reflections (
                    user_id,
                    session_id,
                    used_in_real_world,
                    outcome_score,
                    blocker_code,
                    blocker_note
                )
                VALUES (
                    :user_id,
                    :session_id,
                    :used_in_real_world,
                    :outcome_score,
                    :blocker_code,
                    :blocker_note
                )
                RETURNING id, created_at
                """
            ),
            {
                "user_id": str(user.user_id),
                "session_id": str(payload.session_id),
                "used_in_real_world": payload.used_in_real_world,
                "outcome_score": payload.outcome_score,
                "blocker_code": payload.blocker_code.value if payload.blocker_code else None,
                "blocker_note": payload.blocker_note,
            },
        )
        row = result.mappings().one()
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="reflection already exists for this session",
        ) from exc

    return ReflectionCreateResponse(reflection_id=row["id"], created_at=row["created_at"])
