from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def ensure_user_exists(db: AsyncSession, user_id: UUID) -> None:
    await db.execute(
        text(
            """
            INSERT INTO users (id, email, display_name)
            VALUES (:user_id, :email, :display_name)
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {
            "user_id": str(user_id),
            "email": f"{user_id}@mock.local",
            "display_name": "Mock User",
        },
    )


async def get_scene_owned_by_user(db: AsyncSession, scene_id: UUID, user_id: UUID):
    result = await db.execute(
        text(
            """
            SELECT id, user_id, context, status
            FROM scenes
            WHERE id = :scene_id AND user_id = :user_id
            LIMIT 1
            """
        ),
        {"scene_id": str(scene_id), "user_id": str(user_id)},
    )
    return result.mappings().first()


async def get_session_owned_by_user(db: AsyncSession, session_id: UUID, user_id: UUID):
    result = await db.execute(
        text(
            """
            SELECT s.id, s.user_id, s.scene_id, s.state, s.target_turns, s.current_turn
            FROM sessions s
            WHERE s.id = :session_id AND s.user_id = :user_id
            LIMIT 1
            """
        ),
        {"session_id": str(session_id), "user_id": str(user_id)},
    )
    return result.mappings().first()
