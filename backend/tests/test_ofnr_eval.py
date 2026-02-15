from pathlib import Path

from app.services.ofnr_eval import evaluate_evalset


def test_ofnr_evalset_runner_returns_valid_summary():
    root_dir = Path(__file__).resolve().parents[2]
    evalset_path = root_dir / "spec" / "evals" / "ofnr_evalset_v0.2.jsonl"

    summary = evaluate_evalset(evalset_path)
    assert summary.case_count >= 30
    assert 0.0 <= summary.risk_accuracy <= 1.0
    assert 0.0 <= summary.ofnr_dimension_accuracy <= 1.0
    assert 0.0 <= summary.ofnr_case_pass_rate <= 1.0
    assert 0.0 <= summary.strict_case_pass_rate <= 1.0
    assert 0.0 <= summary.must_flag_hit_rate <= 1.0
    assert 0.0 <= summary.rewrite_keyword_hit_rate <= 1.0
    assert 0.0 <= summary.overall_score <= 1.0
    assert len(summary.case_results) == summary.case_count


def test_ofnr_evalset_runner_has_reasonable_regression_floor():
    root_dir = Path(__file__).resolve().parents[2]
    evalset_path = root_dir / "spec" / "evals" / "ofnr_evalset_v0.2.jsonl"

    summary = evaluate_evalset(evalset_path)
    assert summary.risk_accuracy >= 0.75
    assert summary.ofnr_dimension_accuracy >= 0.65
