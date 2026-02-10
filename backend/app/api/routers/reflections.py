from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.security import AuthUser

router = APIRouter(prefix="/api/v1/reflections", tags=["reflections"])


@router.post("")
def create_reflection(user: AuthUser = Depends(get_current_user)) -> dict:
    return {"message": "not_implemented", "user_id": user.user_id}
