from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.security import AuthUser

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post("")
def create_session(user: AuthUser = Depends(get_current_user)) -> dict:
    return {"message": "not_implemented", "user_id": user.user_id}


@router.post("/{session_id}/messages")
def create_session_message(session_id: str, user: AuthUser = Depends(get_current_user)) -> dict:
    return {
        "message": "not_implemented",
        "session_id": session_id,
        "user_id": user.user_id,
    }


@router.post("/{session_id}/rewrite")
def rewrite_session_message(session_id: str, user: AuthUser = Depends(get_current_user)) -> dict:
    return {
        "message": "not_implemented",
        "session_id": session_id,
        "user_id": user.user_id,
    }


@router.post("/{session_id}/summary")
def create_session_summary(session_id: str, user: AuthUser = Depends(get_current_user)) -> dict:
    return {
        "message": "not_implemented",
        "session_id": session_id,
        "user_id": user.user_id,
    }
