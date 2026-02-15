from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.services.nvc_service import analyze_message, build_rewrite_sentence

DIMENSIONS = ("observation", "feeling", "need", "request")


def _normalize_flag(text: str) -> str:
    value = text.strip()
    if "绝对化" in value:
        return "绝对化"
    if "讽刺" in value:
        return "讽刺"
    if "威胁" in value:
        return "威胁"
    if "命令" in value:
        return "命令式请求"
    if "请求不具体" in value or "请求模糊" in value:
        return "请求不具体"
    if "隐性评判" in value:
        return "隐性评判"
    if "人格化归因" in value:
        return "人格化归因"
    if "人格" in value or "评判" in value or "评价" in value:
        return "人格评价"
    return value


def _flag_equivalent(expected: str, actual: str) -> bool:
    expected_norm = _normalize_flag(expected)
    actual_norm = _normalize_flag(actual)
    if expected_norm == actual_norm:
        return True

    equivalents = {
        "人格化归因": {"人格化归因", "人格评价"},
        "人格评价": {"人格评价", "人格化归因"},
        "请求模糊": {"请求模糊", "请求不具体"},
        "请求不具体": {"请求不具体", "请求模糊"},
    }
    accepted = equivalents.get(expected_norm, {expected_norm})
    return actual_norm in accepted


@dataclass(slots=True)
class EvalCaseResult:
    case_id: str
    risk_match: bool
    ofnr_match_count: int
    ofnr_total_count: int
    strict_ofnr_match: bool
    flag_expected_count: int
    flag_match_count: int
    rewrite_expected_count: int
    rewrite_match_count: int
    expected_risk: str
    actual_risk: str
    ofnr_mismatches: list[str]


@dataclass(slots=True)
class EvalSummary:
    case_count: int
    risk_accuracy: float
    ofnr_dimension_accuracy: float
    ofnr_case_pass_rate: float
    strict_case_pass_rate: float
    must_flag_hit_rate: float
    rewrite_keyword_hit_rate: float
    overall_score: float
    failed_case_ids: list[str]
    case_results: list[EvalCaseResult]

    def to_dict(self) -> dict:
        return {
            "case_count": self.case_count,
            "risk_accuracy": self.risk_accuracy,
            "ofnr_dimension_accuracy": self.ofnr_dimension_accuracy,
            "ofnr_case_pass_rate": self.ofnr_case_pass_rate,
            "strict_case_pass_rate": self.strict_case_pass_rate,
            "must_flag_hit_rate": self.must_flag_hit_rate,
            "rewrite_keyword_hit_rate": self.rewrite_keyword_hit_rate,
            "overall_score": self.overall_score,
            "failed_case_ids": self.failed_case_ids,
            "case_results": [
                {
                    "case_id": item.case_id,
                    "risk_match": item.risk_match,
                    "ofnr_match_count": item.ofnr_match_count,
                    "ofnr_total_count": item.ofnr_total_count,
                    "strict_ofnr_match": item.strict_ofnr_match,
                    "flag_expected_count": item.flag_expected_count,
                    "flag_match_count": item.flag_match_count,
                    "rewrite_expected_count": item.rewrite_expected_count,
                    "rewrite_match_count": item.rewrite_match_count,
                    "expected_risk": item.expected_risk,
                    "actual_risk": item.actual_risk,
                    "ofnr_mismatches": item.ofnr_mismatches,
                }
                for item in self.case_results
            ],
        }


def load_evalset_jsonl(path: Path) -> list[dict]:
    payloads: list[dict] = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        normalized = line.strip()
        if not normalized:
            continue
        try:
            payload = json.loads(normalized)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid json at line {idx}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"line {idx} is not object json")
        payloads.append(payload)
    if not payloads:
        raise ValueError("empty evalset")
    return payloads


def evaluate_evalset(evalset_path: Path) -> EvalSummary:
    rows = load_evalset_jsonl(evalset_path)
    case_results: list[EvalCaseResult] = []

    risk_match_total = 0
    ofnr_match_total = 0
    ofnr_total = 0
    ofnr_case_pass_total = 0
    strict_case_pass_total = 0
    flag_expected_total = 0
    flag_match_total = 0
    rewrite_expected_total = 0
    rewrite_match_total = 0

    for row in rows:
        expected = row.get("expected", {})
        expected_risk = str(expected.get("risk_level", "")).strip()
        expected_ofnr = expected.get("ofnr", {}) if isinstance(expected.get("ofnr"), dict) else {}
        expected_flags = expected.get("must_flag", [])
        expected_rewrite_contains = expected.get("rewrite_contains", [])

        message = str(row.get("input_message", "")).strip()
        analysis = analyze_message(message)
        rewrite = build_rewrite_sentence(message)

        actual_risk = analysis.feedback.risk_level.value
        risk_match = actual_risk == expected_risk
        risk_match_total += int(risk_match)

        actual_ofnr = analysis.feedback.ofnr.model_dump(mode="json")
        ofnr_match_count = 0
        mismatches: list[str] = []
        for dimension in DIMENSIONS:
            expected_status = str(expected_ofnr.get(dimension, "")).strip()
            actual_status = str(actual_ofnr.get(dimension, {}).get("status", "")).strip()
            if expected_status and expected_status == actual_status:
                ofnr_match_count += 1
            else:
                mismatches.append(
                    f"{dimension}: expected={expected_status or '-'} actual={actual_status or '-'}"
                )

        ofnr_total += len(DIMENSIONS)
        ofnr_match_total += ofnr_match_count
        ofnr_case_pass = ofnr_match_count >= 3
        strict_ofnr_match = ofnr_match_count == len(DIMENSIONS)
        ofnr_case_pass_total += int(ofnr_case_pass)
        strict_case_pass = risk_match and strict_ofnr_match
        strict_case_pass_total += int(strict_case_pass)

        normalized_actual_flags = [_normalize_flag(item) for item in analysis.risk_triggers]
        flag_expected_count = 0
        flag_match_count = 0
        if isinstance(expected_flags, list):
            for item in expected_flags:
                expected_flag = str(item).strip()
                if not expected_flag:
                    continue
                flag_expected_count += 1
                if any(_flag_equivalent(expected_flag, actual) for actual in normalized_actual_flags):
                    flag_match_count += 1
        flag_expected_total += flag_expected_count
        flag_match_total += flag_match_count

        rewrite_expected_count = 0
        rewrite_match_count = 0
        if isinstance(expected_rewrite_contains, list):
            for item in expected_rewrite_contains:
                expected_keyword = str(item).strip()
                if not expected_keyword:
                    continue
                rewrite_expected_count += 1
                if expected_keyword in rewrite:
                    rewrite_match_count += 1
        rewrite_expected_total += rewrite_expected_count
        rewrite_match_total += rewrite_match_count

        case_results.append(
            EvalCaseResult(
                case_id=str(row.get("case_id", "unknown")),
                risk_match=risk_match,
                ofnr_match_count=ofnr_match_count,
                ofnr_total_count=len(DIMENSIONS),
                strict_ofnr_match=strict_ofnr_match,
                flag_expected_count=flag_expected_count,
                flag_match_count=flag_match_count,
                rewrite_expected_count=rewrite_expected_count,
                rewrite_match_count=rewrite_match_count,
                expected_risk=expected_risk,
                actual_risk=actual_risk,
                ofnr_mismatches=mismatches,
            )
        )

    case_count = len(case_results)
    risk_accuracy = risk_match_total / case_count
    ofnr_dimension_accuracy = ofnr_match_total / ofnr_total if ofnr_total else 0.0
    ofnr_case_pass_rate = ofnr_case_pass_total / case_count
    strict_case_pass_rate = strict_case_pass_total / case_count
    must_flag_hit_rate = (
        flag_match_total / flag_expected_total if flag_expected_total > 0 else 1.0
    )
    rewrite_keyword_hit_rate = (
        rewrite_match_total / rewrite_expected_total if rewrite_expected_total > 0 else 1.0
    )

    overall_score = (
        0.45 * risk_accuracy
        + 0.35 * ofnr_dimension_accuracy
        + 0.15 * must_flag_hit_rate
        + 0.05 * rewrite_keyword_hit_rate
    )
    failed_case_ids = [
        item.case_id
        for item in case_results
        if not item.risk_match or item.ofnr_match_count < 3
    ]
    return EvalSummary(
        case_count=case_count,
        risk_accuracy=round(risk_accuracy, 4),
        ofnr_dimension_accuracy=round(ofnr_dimension_accuracy, 4),
        ofnr_case_pass_rate=round(ofnr_case_pass_rate, 4),
        strict_case_pass_rate=round(strict_case_pass_rate, 4),
        must_flag_hit_rate=round(must_flag_hit_rate, 4),
        rewrite_keyword_hit_rate=round(rewrite_keyword_hit_rate, 4),
        overall_score=round(overall_score, 4),
        failed_case_ids=failed_case_ids,
        case_results=case_results,
    )
