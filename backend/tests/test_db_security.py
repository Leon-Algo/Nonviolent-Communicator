import asyncio
from uuid import UUID

from app.core.security import AuthUser
from app.db.security import apply_request_rls_context


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        return None


def test_apply_request_rls_context_sets_role_and_claims():
    session = _FakeSession()
    user = AuthUser(user_id=UUID("8a4c3f2a-2f88-4c74-9bc0-3123d26df302"))

    asyncio.run(apply_request_rls_context(session, user))

    assert len(session.calls) == 3
    assert "SET LOCAL ROLE authenticated" in session.calls[0][0]
    assert "request.jwt.claim.role" in session.calls[1][0]
    assert "request.jwt.claim.sub" in session.calls[2][0]
    assert session.calls[2][1] == {"user_id": str(user.user_id)}
