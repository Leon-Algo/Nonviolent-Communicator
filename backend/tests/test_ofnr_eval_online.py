import asyncio
import json

from app.services.ofnr_eval_online import evaluate_evalset_online


def _write_evalset(path, rows):
    payload = "\n".join(json.dumps(item, ensure_ascii=False) for item in rows) + "\n"
    path.write_text(payload, encoding="utf-8")


def test_online_eval_returns_high_score_with_stubbed_generators(tmp_path):
    evalset = tmp_path / "evalset.jsonl"
    _write_evalset(
        evalset,
        [
            {
                "case_id": "ONLINE-001",
                "input_message": "你们总是拖延，根本不专业。",
                "scenario": "同级协作延期",
                "expected": {"rewrite_contains": ["我观察到", "你愿意"]},
            },
            {
                "case_id": "ONLINE-002",
                "input_message": "我压力很大，你最好尽快给我更多人手。",
                "scenario": "向上沟通资源不足",
                "expected": {"rewrite_contains": ["我需要", "17:00前"]},
            },
        ],
    )

    async def rewrite_generator(_: str) -> str:
        return (
            "我观察到最近两次变更导致延期，我有些担心，"
            "因为我需要稳定节奏。你愿意今天17:00前一起确认计划吗？"
        )

    async def assistant_generator(_: str, __: str) -> str:
        return "我理解你的担心，我们先对齐事实，再确认下一步计划。"

    summary = asyncio.run(
        evaluate_evalset_online(
            evalset,
            rewrite_generator=rewrite_generator,
            assistant_generator=assistant_generator,
            concurrency=2,
            timeout_seconds=5,
        )
    )

    assert summary.case_count == 2
    assert summary.rewrite_generation_success_rate == 1.0
    assert summary.assistant_generation_success_rate == 1.0
    assert summary.rewrite_ofnr_dimension_accuracy == 1.0
    assert summary.rewrite_keyword_hit_rate == 1.0
    assert summary.case_pass_rate == 1.0
    assert summary.failed_case_ids == []


def test_online_eval_marks_unsafe_or_missing_outputs_as_failed(tmp_path):
    evalset = tmp_path / "evalset.jsonl"
    _write_evalset(
        evalset,
        [
            {
                "case_id": "ONLINE-FAIL-001",
                "input_message": "再不配合后果自负。",
                "scenario": "高压沟通",
                "expected": {"rewrite_contains": ["我观察到"]},
            }
        ],
    )

    async def rewrite_generator(_: str) -> str:
        return "根本不专业，马上改，不然追责。"

    async def assistant_generator(_: str, __: str):
        return None

    summary = asyncio.run(
        evaluate_evalset_online(
            evalset,
            rewrite_generator=rewrite_generator,
            assistant_generator=assistant_generator,
            concurrency=1,
            timeout_seconds=5,
        )
    )

    assert summary.case_count == 1
    assert summary.failed_case_ids == ["ONLINE-FAIL-001"]
    case_result = summary.case_results[0]
    assert case_result.case_passed is False
    assert "rewrite_ofnr_low" in case_result.failure_reasons
    assert "rewrite_not_safe" in case_result.failure_reasons
    assert "assistant_empty" in case_result.failure_reasons
