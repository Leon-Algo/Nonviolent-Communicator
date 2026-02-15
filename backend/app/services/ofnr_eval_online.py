from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from app.services.nvc_service import (
    generate_assistant_reply_online,
    generate_rewrite_online,
)
from app.services.ofnr_eval import load_evalset_jsonl

RewriteGenerator = Callable[[str], Awaitable[str | None]]
AssistantGenerator = Callable[[str, str], Awaitable[str | None]]

OFNR_DIMENSIONS = ("observation", "feeling", "need", "request")
OFNR_HINTS: dict[str, tuple[str, ...]] = {
    "observation": ("观察到", "注意到", "过去", "本周", "昨天", "变更", "延期", "次"),
    "feeling": ("我感到", "我有些", "我觉得", "焦虑", "担心", "紧张", "压力", "失望"),
    "need": ("我需要", "我希望", "对我来说", "稳定", "明确", "可预测", "资源", "标准"),
    "request": ("你愿意", "是否可以", "能否", "可否", "请你", "一起", "吗", "？", "?"),
}
UNSAFE_PATTERNS = (
    "后果自负",
    "升级到",
    "投诉",
    "追责",
    "根本不专业",
    "垃圾",
    "无能",
    "离谱",
    "马上滚",
)


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(item in text for item in patterns)


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return str(value).strip()


def _count_ofnr_dimensions(text: str) -> int:
    if not text:
        return 0
    return sum(1 for key in OFNR_DIMENSIONS if _contains_any(text, OFNR_HINTS[key]))


def _match_keywords(text: str, expected_keywords: list[str]) -> tuple[int, int]:
    if not expected_keywords:
        return (0, 0)
    matched = 0
    for item in expected_keywords:
        if item and item in text:
            matched += 1
    return (matched, len(expected_keywords))


def _is_safe_text(text: str) -> bool:
    if not text:
        return False
    if len(text) > 260:
        return False
    return not _contains_any(text, UNSAFE_PATTERNS)


def _half_or_more(matched: int, total: int) -> bool:
    if total <= 0:
        return True
    minimum = (total + 1) // 2
    return matched >= minimum


@dataclass(slots=True)
class OnlineEvalCaseResult:
    case_id: str
    rewrite_generated: bool
    assistant_generated: bool
    rewrite_ofnr_match_count: int
    rewrite_ofnr_total_count: int
    rewrite_keyword_match_count: int
    rewrite_keyword_total_count: int
    rewrite_safe: bool
    assistant_safe: bool
    case_passed: bool
    failure_reasons: list[str]


@dataclass(slots=True)
class OnlineEvalSummary:
    case_count: int
    rewrite_generation_success_rate: float
    assistant_generation_success_rate: float
    rewrite_ofnr_dimension_accuracy: float
    rewrite_keyword_hit_rate: float
    safety_pass_rate: float
    case_pass_rate: float
    overall_score: float
    failed_case_ids: list[str]
    case_results: list[OnlineEvalCaseResult]

    def to_dict(self) -> dict:
        return {
            "case_count": self.case_count,
            "rewrite_generation_success_rate": self.rewrite_generation_success_rate,
            "assistant_generation_success_rate": self.assistant_generation_success_rate,
            "rewrite_ofnr_dimension_accuracy": self.rewrite_ofnr_dimension_accuracy,
            "rewrite_keyword_hit_rate": self.rewrite_keyword_hit_rate,
            "safety_pass_rate": self.safety_pass_rate,
            "case_pass_rate": self.case_pass_rate,
            "overall_score": self.overall_score,
            "failed_case_ids": self.failed_case_ids,
            "case_results": [
                {
                    "case_id": item.case_id,
                    "rewrite_generated": item.rewrite_generated,
                    "assistant_generated": item.assistant_generated,
                    "rewrite_ofnr_match_count": item.rewrite_ofnr_match_count,
                    "rewrite_ofnr_total_count": item.rewrite_ofnr_total_count,
                    "rewrite_keyword_match_count": item.rewrite_keyword_match_count,
                    "rewrite_keyword_total_count": item.rewrite_keyword_total_count,
                    "rewrite_safe": item.rewrite_safe,
                    "assistant_safe": item.assistant_safe,
                    "case_passed": item.case_passed,
                    "failure_reasons": item.failure_reasons,
                }
                for item in self.case_results
            ],
        }


async def _evaluate_case(
    row: dict,
    rewrite_generator: RewriteGenerator,
    assistant_generator: AssistantGenerator,
) -> OnlineEvalCaseResult:
    case_id = _normalize_text(row.get("case_id")) or "unknown"
    message = _normalize_text(row.get("input_message"))
    scenario = _normalize_text(row.get("scenario")) or "NVC practice"
    expected = row.get("expected", {})
    expected_keywords = []
    if isinstance(expected, dict):
        rewrite_contains = expected.get("rewrite_contains", [])
        if isinstance(rewrite_contains, list):
            expected_keywords = [
                _normalize_text(item) for item in rewrite_contains if _normalize_text(item)
            ]

    failure_reasons: list[str] = []
    hard_failure_reasons: list[str] = []

    rewrite_generated = False
    rewrite_text = ""
    try:
        rewrite_text = _normalize_text(await rewrite_generator(message))
        rewrite_generated = bool(rewrite_text)
    except Exception:
        failure_reasons.append("rewrite_exception")
        hard_failure_reasons.append("rewrite_exception")

    rewrite_ofnr_match_count = _count_ofnr_dimensions(rewrite_text) if rewrite_generated else 0
    rewrite_keyword_match_count, rewrite_keyword_total_count = _match_keywords(
        rewrite_text, expected_keywords
    )
    rewrite_safe = _is_safe_text(rewrite_text) if rewrite_generated else False

    assistant_generated = False
    assistant_text = ""
    try:
        assistant_text = _normalize_text(await assistant_generator(scenario, message))
        assistant_generated = bool(assistant_text)
    except Exception:
        failure_reasons.append("assistant_exception")
        hard_failure_reasons.append("assistant_exception")
    assistant_safe = _is_safe_text(assistant_text) if assistant_generated else False

    if not rewrite_generated:
        failure_reasons.append("rewrite_empty")
        hard_failure_reasons.append("rewrite_empty")
    if rewrite_generated and rewrite_ofnr_match_count < 3:
        failure_reasons.append("rewrite_ofnr_low")
        hard_failure_reasons.append("rewrite_ofnr_low")
    if rewrite_generated and rewrite_keyword_total_count > 0 and not _half_or_more(
        rewrite_keyword_match_count, rewrite_keyword_total_count
    ):
        failure_reasons.append("rewrite_keywords_low")
    if rewrite_generated and not rewrite_safe:
        failure_reasons.append("rewrite_not_safe")
        hard_failure_reasons.append("rewrite_not_safe")

    if not assistant_generated:
        failure_reasons.append("assistant_empty")
        hard_failure_reasons.append("assistant_empty")
    if assistant_generated and not assistant_safe:
        failure_reasons.append("assistant_not_safe")
        hard_failure_reasons.append("assistant_not_safe")

    case_passed = len(hard_failure_reasons) == 0

    return OnlineEvalCaseResult(
        case_id=case_id,
        rewrite_generated=rewrite_generated,
        assistant_generated=assistant_generated,
        rewrite_ofnr_match_count=rewrite_ofnr_match_count,
        rewrite_ofnr_total_count=len(OFNR_DIMENSIONS),
        rewrite_keyword_match_count=rewrite_keyword_match_count,
        rewrite_keyword_total_count=rewrite_keyword_total_count,
        rewrite_safe=rewrite_safe,
        assistant_safe=assistant_safe,
        case_passed=case_passed,
        failure_reasons=failure_reasons,
    )


async def evaluate_evalset_online(
    evalset_path: Path,
    rewrite_generator: RewriteGenerator | None = None,
    assistant_generator: AssistantGenerator | None = None,
    concurrency: int = 3,
    timeout_seconds: float = 35.0,
    max_cases: int = 0,
) -> OnlineEvalSummary:
    rows = load_evalset_jsonl(evalset_path)
    if max_cases > 0:
        rows = rows[:max_cases]
    rewrite_fn = rewrite_generator or generate_rewrite_online
    assistant_fn = assistant_generator or generate_assistant_reply_online

    worker_limit = max(1, int(concurrency))
    semaphore = asyncio.Semaphore(worker_limit)

    async def _worker(row: dict) -> OnlineEvalCaseResult:
        case_id = _normalize_text(row.get("case_id")) or "unknown"
        async with semaphore:
            try:
                return await asyncio.wait_for(
                    _evaluate_case(row, rewrite_fn, assistant_fn),
                    timeout=max(1.0, float(timeout_seconds)),
                )
            except asyncio.TimeoutError:
                return OnlineEvalCaseResult(
                    case_id=case_id,
                    rewrite_generated=False,
                    assistant_generated=False,
                    rewrite_ofnr_match_count=0,
                    rewrite_ofnr_total_count=len(OFNR_DIMENSIONS),
                    rewrite_keyword_match_count=0,
                    rewrite_keyword_total_count=0,
                    rewrite_safe=False,
                    assistant_safe=False,
                    case_passed=False,
                    failure_reasons=["timeout"],
                )

    case_results = await asyncio.gather(*[_worker(row) for row in rows])
    case_count = len(case_results)

    rewrite_generated_total = sum(1 for item in case_results if item.rewrite_generated)
    assistant_generated_total = sum(1 for item in case_results if item.assistant_generated)
    rewrite_ofnr_match_total = sum(item.rewrite_ofnr_match_count for item in case_results)
    rewrite_ofnr_total = sum(item.rewrite_ofnr_total_count for item in case_results)
    rewrite_keyword_match_total = sum(item.rewrite_keyword_match_count for item in case_results)
    rewrite_keyword_total = sum(item.rewrite_keyword_total_count for item in case_results)
    safety_pass_total = sum(
        1
        for item in case_results
        if item.rewrite_generated
        and item.assistant_generated
        and item.rewrite_safe
        and item.assistant_safe
    )
    case_pass_total = sum(1 for item in case_results if item.case_passed)

    rewrite_generation_success_rate = (
        rewrite_generated_total / case_count if case_count else 0.0
    )
    assistant_generation_success_rate = (
        assistant_generated_total / case_count if case_count else 0.0
    )
    rewrite_ofnr_dimension_accuracy = (
        rewrite_ofnr_match_total / rewrite_ofnr_total if rewrite_ofnr_total else 0.0
    )
    rewrite_keyword_hit_rate = (
        rewrite_keyword_match_total / rewrite_keyword_total
        if rewrite_keyword_total > 0
        else 1.0
    )
    safety_pass_rate = safety_pass_total / case_count if case_count else 0.0
    case_pass_rate = case_pass_total / case_count if case_count else 0.0
    overall_score = (
        0.25 * rewrite_generation_success_rate
        + 0.15 * assistant_generation_success_rate
        + 0.30 * rewrite_ofnr_dimension_accuracy
        + 0.20 * rewrite_keyword_hit_rate
        + 0.10 * safety_pass_rate
    )
    failed_case_ids = [item.case_id for item in case_results if not item.case_passed]

    return OnlineEvalSummary(
        case_count=case_count,
        rewrite_generation_success_rate=round(rewrite_generation_success_rate, 4),
        assistant_generation_success_rate=round(assistant_generation_success_rate, 4),
        rewrite_ofnr_dimension_accuracy=round(rewrite_ofnr_dimension_accuracy, 4),
        rewrite_keyword_hit_rate=round(rewrite_keyword_hit_rate, 4),
        safety_pass_rate=round(safety_pass_rate, 4),
        case_pass_rate=round(case_pass_rate, 4),
        overall_score=round(overall_score, 4),
        failed_case_ids=failed_case_ids,
        case_results=case_results,
    )
