import json

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.db.utils import ensure_user_exists
from app.core.security import AuthUser
from app.schemas.scenes import SceneCreateRequest, SceneCreateResponse

router = APIRouter(prefix="/api/v1/scenes", tags=["scenes"])


@router.post("", response_model=SceneCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_scene(
    payload: SceneCreateRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SceneCreateResponse:
    await ensure_user_exists(db, user.user_id)

    result = await db.execute(
        text(
            """
            INSERT INTO scenes (
              user_id,
              title,
              template_id,
              counterparty_role,
              relationship_level,
              goal,
              pain_points,
              context,
              power_dynamic
            )
            VALUES (
              :user_id,
              :title,
              :template_id,
              :counterparty_role,
              :relationship_level,
              :goal,
              CAST(:pain_points AS jsonb),
              :context,
              :power_dynamic
            )
            RETURNING id, status, created_at
            """
        ),
        {
            "user_id": str(user.user_id),
            "title": payload.title,
            "template_id": payload.template_id.value,
            "counterparty_role": payload.counterparty_role.value,
            "relationship_level": payload.relationship_level.value,
            "goal": payload.goal,
            "pain_points": json.dumps(payload.pain_points),
            "context": payload.context,
            "power_dynamic": payload.power_dynamic.value,
        },
    )
    row = result.mappings().one()
    await db.commit()

    return SceneCreateResponse(
        scene_id=row["id"],
        status=row["status"],
        created_at=row["created_at"],
    )
