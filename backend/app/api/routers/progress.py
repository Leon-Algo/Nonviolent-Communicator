from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.security import AuthUser

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])


@router.get("/weekly")
def get_weekly_progress(
    week_start: str = Query(..., description="Date in YYYY-MM-DD format"),
    user: AuthUser = Depends(get_current_user),
) -> dict:
    return {
        "message": "not_implemented",
        "week_start": week_start,
        "user_id": user.user_id,
    }
