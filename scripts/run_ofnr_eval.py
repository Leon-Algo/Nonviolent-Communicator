#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.ofnr_eval import evaluate_evalset  # noqa: E402
from app.services.ofnr_eval_online import evaluate_evalset_online  # noqa: E402


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
        default=str(ROOT_DIR / "spec" / "evals" / "ofnr_evalset_v0.2.jsonl"),
        help="Path to evalset jsonl",
    )
    parser.add_argument(
        "--mode",
        choices=["offline", "online", "both"],
        default=os.getenv("OFNR_EVAL_MODE", "offline").strip().lower() or "offline",
        help="Run offline deterministic eval, online model eval, or both",
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
    parser.add_argument(
        "--online-min-overall",
        type=float,
        default=_float_env("OFNR_ONLINE_EVAL_MIN_OVERALL", 0.45),
        help="Minimum online overall score threshold",
    )
    parser.add_argument(
        "--online-min-success",
        type=float,
        default=_float_env("OFNR_ONLINE_EVAL_MIN_SUCCESS", 0.6),
        help="Minimum online rewrite generation success rate threshold",
    )
    parser.add_argument(
        "--online-concurrency",
        type=int,
        default=max(1, int(os.getenv("OFNR_ONLINE_EVAL_CONCURRENCY", "1"))),
        help="Parallelism for online eval requests",
    )
    parser.add_argument(
        "--online-timeout-seconds",
        type=float,
        default=_float_env("OFNR_ONLINE_EVAL_TIMEOUT_SECONDS", 35.0),
        help="Timeout seconds per online eval case",
    )
    parser.add_argument(
        "--online-max-cases",
        type=int,
        default=max(0, int(os.getenv("OFNR_ONLINE_EVAL_MAX_CASES", "8"))),
        help="Online eval case cap (0 means all)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    evalset_path = Path(args.evalset).resolve()
    payload: dict = {"mode": args.mode}
    offline_passed = True
    online_passed = True

    if args.mode in {"offline", "both"}:
        summary = evaluate_evalset(evalset_path)
        payload["offline"] = summary.to_dict()

        print(
            "[OFNR-EVAL][offline] "
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
            print("[OFNR-EVAL][offline] failed cases:")
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

        offline_passed = (
            summary.overall_score >= args.min_overall
            and summary.risk_accuracy >= args.min_risk_accuracy
        )

    if args.mode in {"online", "both"}:
        online_summary = asyncio.run(
            evaluate_evalset_online(
                evalset_path,
                concurrency=args.online_concurrency,
                timeout_seconds=args.online_timeout_seconds,
                max_cases=args.online_max_cases,
            )
        )
        payload["online"] = online_summary.to_dict()

        print(
            "[OFNR-EVAL][online] "
            f"cases={online_summary.case_count} "
            f"overall={online_summary.overall_score:.4f} "
            f"rewrite_success={online_summary.rewrite_generation_success_rate:.4f} "
            f"assistant_success={online_summary.assistant_generation_success_rate:.4f} "
            f"rewrite_ofnr={online_summary.rewrite_ofnr_dimension_accuracy:.4f} "
            f"rewrite_keywords={online_summary.rewrite_keyword_hit_rate:.4f} "
            f"case_pass={online_summary.case_pass_rate:.4f}"
        )

        failures_to_show = max(0, args.show_failures)
        if online_summary.failed_case_ids and failures_to_show > 0:
            print("[OFNR-EVAL][online] failed cases:")
            shown = 0
            for case in online_summary.case_results:
                if case.case_id not in online_summary.failed_case_ids:
                    continue
                print(
                    f"  - {case.case_id}: reasons={','.join(case.failure_reasons) or '-'} "
                    f"rewrite_ofnr={case.rewrite_ofnr_match_count}/{case.rewrite_ofnr_total_count}"
                )
                shown += 1
                if shown >= failures_to_show:
                    break

        online_passed = (
            online_summary.overall_score >= args.online_min_overall
            and online_summary.rewrite_generation_success_rate >= args.online_min_success
        )

    if args.json_out:
        out_path = Path(args.json_out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[OFNR-EVAL] summary written: {out_path}")

    passed = offline_passed and online_passed
    if passed:
        print("[OFNR-EVAL] PASS")
        return 0

    if not offline_passed:
        print(
            "[OFNR-EVAL][offline] FAIL "
            f"(overall<{args.min_overall:.4f} or risk<{args.min_risk_accuracy:.4f})"
        )
    if not online_passed:
        print(
            "[OFNR-EVAL][online] FAIL "
            "(overall or rewrite_success below threshold)"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
