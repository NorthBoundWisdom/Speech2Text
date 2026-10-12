from pathlib import Path

from scripts.validate_gold_set import validate_gold_dir


def test_validate_committed_gold_set():
    assert validate_gold_dir(Path("tests/gold")) == []


def test_validate_gold_set_requires_categories(tmp_path):
    gold = tmp_path / "gold"
    gold.mkdir()
    (gold / "sample.ref.txt").write_text("短文本", encoding="utf-8")

    errors = validate_gold_dir(gold)

    assert any("reference text is too short" in error for error in errors)
    assert any("missing gold categories" in error for error in errors)
