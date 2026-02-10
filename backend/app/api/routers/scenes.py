from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.security import AuthUser

router = APIRouter(prefix="/api/v1/scenes", tags=["scenes"])


@router.post("")
def create_scene(user: AuthUser = Depends(get_current_user)) -> dict:
    # Placeholder endpoint for next implementation phase.
    return {"message": "not_implemented", "user_id": user.user_id}
