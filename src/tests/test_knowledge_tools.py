from atot.local_summary import LocalSummaryOptions, write_local_summary
from atot.search import build_search_index, search_index
from atot.utils import read_json


def test_write_local_summary_requires_explicit_command(tmp_path):
    output = tmp_path / "episode"
    output.mkdir()
    (output / "transcript.readable.md").write_text(
        "# 节目\n\n第一段讨论 ChatGPT。\n第二段讨论本地模型。", encoding="utf-8"
    )

    try:
        write_local_summary(LocalSummaryOptions(output_dir=output))
    except ValueError as exc:
        assert "Local summary command is required." in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected local summary without command to fail.")

    payload = read_json(output / "local/summary.json")
    assert payload["success"] is False
    assert payload["source"] == "failed"
    assert payload["output"] == ""
    assert not (output / "local/summary.md").exists()


def test_search_index_finds_cross_episode_keyword_and_timestamp(tmp_path):
    first = tmp_path / "output/0528/first"
    second = tmp_path / "output/0529/second"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    (first / "transcript.readable.md").write_text(
        "[00:00:03] 本期讨论 ChatGPT 和论文。", encoding="utf-8"
    )
    (second / "transcript.readable.md").write_text(
        "[00:01:00] 本期讨论播客剪辑。", encoding="utf-8"
    )
    index = tmp_path / "search.json"

    payload = build_search_index(tmp_path / "output", index)
    hits = search_index("ChatGPT", index)

    assert payload["document_count"] == 2
    assert len(hits) == 1
    assert hits[0].episode == "first"
    assert hits[0].timestamp == "00:00:03"
