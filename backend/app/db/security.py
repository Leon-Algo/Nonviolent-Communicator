from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthUser


async def apply_request_rls_context(db: AsyncSession, user: AuthUser) -> None:
    # Run queries as the Supabase authenticated role so RLS policies are actually enforced.
    await db.execute(text("SET LOCAL ROLE authenticated"))
    await db.execute(
        text("SELECT set_config('request.jwt.claim.role', 'authenticated', true)")
    )
    await db.execute(
        text("SELECT set_config('request.jwt.claim.sub', :user_id, true)"),
        {"user_id": str(user.user_id)},
    )
