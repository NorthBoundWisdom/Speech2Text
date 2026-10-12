from pathlib import Path

from atot.utils import read_json, write_json_atomic
from scripts.validate_backend_promotion import validate_backend_promotion


def _write_gate(path: Path, *, success: bool = True, guardrail_pass: bool = True) -> None:
    rows = []
    for index in range(3):
        rows.append(
            {
                "audio": f"process/0000/episode_{index}/episode.m4a",
                "success": success,
                "metric_guardrail_pass": guardrail_pass,
                "metric_guardrail_failures": [] if guardrail_pass else ["timestamp_incompatible"],
                "candidate_srt_vtt_compatible": True,
                "comparison": f"output/benchmark/candidate/{index}/comparison.md",
            }
        )
    write_json_atomic(
        path,
        {
            "candidate": "sensevoice-small",
            "audio_count": 3,
            "success": success and guardrail_pass,
            "failed_count": 0 if success else 3,
            "guardrail_failed_count": 0 if guardrail_pass else 3,
            "rows": rows,
        },
    )


def _write_review(path: Path, *, decision: str = "promote", semantic_errors: int = 0) -> None:
    write_json_atomic(
        path,
        {
            "candidate": "sensevoice-small",
            "decision": decision,
            "reviewer": "human-reviewer",
            "reviewed_audios": [
                "process/0000/episode_0/episode.m4a",
                "process/0000/episode_1/episode.m4a",
                "process/0000/episode_2/episode.m4a",
            ],
            "gold_fixture_count": 1,
            "full_length_audio_count": 3,
            "content_types": ["interview", "solo", "knowledge"],
            "summary": "Candidate preserves meaning on reviewed audio.",
            "quality_notes": "No observed term or timestamp regressions.",
            "risk_notes": "Runtime and installation risk are acceptable for candidate promotion.",
            "semantic_errors": semantic_errors,
            "hallucination_risk": "low",
            "qa_blocker_regressions": 0,
            "review_issue_regressions": 0,
            "character_density_stable": True,
            "runtime_acceptable": True,
            "memory_acceptable": True,
        },
    )


def test_validate_backend_promotion_accepts_gate_and_semantic_review(tmp_path):
    gate = tmp_path / "gate.json"
    review = tmp_path / "semantic_review.json"
    _write_gate(gate)
    _write_review(review)

    assert validate_backend_promotion(gate, review) == []


def test_validate_backend_promotion_rejects_guardrail_failures(tmp_path):
    gate = tmp_path / "gate.json"
    review = tmp_path / "semantic_review.json"
    _write_gate(gate, guardrail_pass=False)
    _write_review(review)

    errors = validate_backend_promotion(gate, review)

    assert any("guardrail_failed_count must be 0" in error for error in errors)
    assert any("metric_guardrail_pass must be true" in error for error in errors)


def test_validate_backend_promotion_rejects_semantic_review_without_promotion(tmp_path):
    gate = tmp_path / "gate.json"
    review = tmp_path / "semantic_review.json"
    _write_gate(gate)
    _write_review(review, decision="hold", semantic_errors=1)

    errors = validate_backend_promotion(gate, review)

    assert any("decision must be `promote`" in error for error in errors)
    assert any("semantic_errors must be 0" in error for error in errors)


def test_validate_backend_promotion_requires_full_promotion_evidence(tmp_path):
    gate = tmp_path / "gate.json"
    review = tmp_path / "semantic_review.json"
    _write_gate(gate)
    _write_review(review)
    payload = read_json(review)
    payload["gold_fixture_count"] = 0
    payload["full_length_audio_count"] = 1
    payload["content_types"] = ["interview"]
    payload["character_density_stable"] = False
    write_json_atomic(review, payload)

    errors = validate_backend_promotion(gate, review)

    assert any("gold_fixture_count must be at least 1" in error for error in errors)
    assert any("full_length_audio_count must be at least 3" in error for error in errors)
    assert any("content_types must include at least 3 distinct items" in error for error in errors)
    assert any("character_density_stable must be true" in error for error in errors)
