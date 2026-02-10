from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.core.security import AuthUser
from app.schemas.progress import WeeklyProgressResponse

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])


@router.get("/weekly", response_model=WeeklyProgressResponse)
async def get_weekly_progress(
    week_start: date = Query(..., description="Date in YYYY-MM-DD format"),
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> WeeklyProgressResponse:
    week_end = week_start + timedelta(days=7)

    metrics_result = await db.execute(
        text(
            """
            SELECT
              (
                SELECT COUNT(*)
                FROM sessions s
                WHERE s.user_id = :user_id
                  AND s.created_at >= :week_start
                  AND s.created_at < :week_end
              ) AS practice_count,
              (
                SELECT COUNT(*)
                FROM summaries sm
                JOIN sessions s ON s.id = sm.session_id
                WHERE s.user_id = :user_id
                  AND sm.created_at >= :week_start
                  AND sm.created_at < :week_end
              ) AS summary_count,
              (
                SELECT COUNT(*)
                FROM reflections r
                WHERE r.user_id = :user_id
                  AND r.used_in_real_world = TRUE
                  AND r.created_at >= :week_start
                  AND r.created_at < :week_end
              ) AS real_world_used_count,
              (
                SELECT COALESCE(AVG(r.outcome_score), 0)
                FROM reflections r
                WHERE r.user_id = :user_id
                  AND r.created_at >= :week_start
                  AND r.created_at < :week_end
              ) AS avg_outcome_score
            """
        ),
        {
            "user_id": str(user.user_id),
            "week_start": week_start,
            "week_end": week_end,
        },
    )
    row = metrics_result.mappings().one()

    return WeeklyProgressResponse(
        week_start=week_start,
        practice_count=int(row["practice_count"] or 0),
        summary_count=int(row["summary_count"] or 0),
        real_world_used_count=int(row["real_world_used_count"] or 0),
        avg_outcome_score=float(row["avg_outcome_score"] or 0.0),
    )
