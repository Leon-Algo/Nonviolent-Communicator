from app.schemas.sessions import RiskLevel
from app.services.nvc_service import analyze_message, build_rewrite_sentence


def test_analyze_message_flags_high_risk_for_judgement_and_threat():
    result = analyze_message("你们根本不专业，不改我就投诉。")
    assert result.feedback.risk_level == RiskLevel.HIGH
    assert "人格/能力评判" in result.risk_triggers


def test_build_rewrite_sentence_returns_non_empty_sentence_for_empty_input():
    text = build_rewrite_sentence("")
    assert isinstance(text, str)
    assert text.strip()


def test_analyze_message_has_lower_score_for_aggressive_text():
    aggressive = analyze_message("你们总是拖延，根本不专业。")
    neutral = analyze_message("我观察到最近两周延期了两次，我有些焦虑，我需要更稳定的节奏，你愿意今天一起确认计划吗？")
    assert aggressive.feedback.overall_score < neutral.feedback.overall_score
