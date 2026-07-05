from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.sessions import (
    SessionHistoryDetailResponse,
    SessionHistoryListItem,
    SessionHistoryScene,
    SessionState,
)


def test_history_list_item_exposes_modality_with_text_default():
    item = SessionHistoryListItem(
        session_id=uuid4(),
        scene_id=uuid4(),
        scene_title="场景",
        state=SessionState.ACTIVE,
        current_turn=0,
        target_turns=6,
        created_at=datetime.now(timezone.utc),
        has_summary=False,
        has_reflection=False,
    )

    assert item.modality == "TEXT"


def test_history_detail_exposes_voice_modality():
    detail = SessionHistoryDetailResponse(
        session_id=uuid4(),
        scene=SessionHistoryScene(
            scene_id=uuid4(),
            title="场景",
            goal="目标",
            context="背景",
            template_id="CUSTOM",
        ),
        state=SessionState.ACTIVE,
        modality="VOICE",
        current_turn=1,
        target_turns=6,
        created_at=datetime.now(timezone.utc),
        turns=[],
    )

    assert detail.modality == "VOICE"
