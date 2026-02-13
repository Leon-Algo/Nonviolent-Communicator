#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.ofnr_eval import evaluate_evalset  # noqa: E402


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic OFNR quality regression eval."
    )
    parser.add_argument(
        "--evalset",
        default=str(ROOT_DIR / "spec" / "evals" / "ofnr_evalset_v0.1.jsonl"),
        help="Path to evalset jsonl",
    )
    parser.add_argument(
        "--min-overall",
        type=float,
        default=_float_env("OFNR_EVAL_MIN_OVERALL", 0.72),
        help="Minimum overall score threshold",
    )
    parser.add_argument(
        "--min-risk-accuracy",
        type=float,
        default=_float_env("OFNR_EVAL_MIN_RISK_ACCURACY", 0.75),
        help="Minimum risk accuracy threshold",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional path to write summary json",
    )
    parser.add_argument(
        "--show-failures",
        type=int,
        default=10,
        help="Max failed cases to print",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    evalset_path = Path(args.evalset).resolve()
    summary = evaluate_evalset(evalset_path)
    payload = summary.to_dict()

    print(
        "[OFNR-EVAL] "
        f"cases={summary.case_count} "
        f"overall={summary.overall_score:.4f} "
        f"risk={summary.risk_accuracy:.4f} "
        f"ofnr_dim={summary.ofnr_dimension_accuracy:.4f} "
        f"ofnr_case={summary.ofnr_case_pass_rate:.4f} "
        f"flags={summary.must_flag_hit_rate:.4f} "
        f"rewrite={summary.rewrite_keyword_hit_rate:.4f}"
    )

    failures_to_show = max(0, args.show_failures)
    if summary.failed_case_ids and failures_to_show > 0:
        print("[OFNR-EVAL] failed cases:")
        shown = 0
        for case in summary.case_results:
            if case.case_id not in summary.failed_case_ids:
                continue
            print(
                f"  - {case.case_id}: risk={case.actual_risk}/{case.expected_risk}, "
                f"ofnr={case.ofnr_match_count}/{case.ofnr_total_count}"
            )
            shown += 1
            if shown >= failures_to_show:
                break

    if args.json_out:
        out_path = Path(args.json_out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[OFNR-EVAL] summary written: {out_path}")

    passed = (
        summary.overall_score >= args.min_overall
        and summary.risk_accuracy >= args.min_risk_accuracy
    )
    if passed:
        print("[OFNR-EVAL] PASS")
        return 0

    print(
        "[OFNR-EVAL] FAIL "
        f"(overall<{args.min_overall:.4f} or risk<{args.min_risk_accuracy:.4f})"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

