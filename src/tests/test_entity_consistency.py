from atot.entity_consistency import build_entity_consistency_report
from atot.review import review_to_markdown


def test_entity_consistency_reports_review_only_and_ascii_variants():
    report = build_entity_consistency_report(
        [
            {"start": 1.0, "end": 2.0, "text": "Fudan NLP 和 FoodNLP 都被提到了。"},
            {"start": 3.0, "end": 4.0, "text": "后面又说 FudanNLP。"},
        ],
        {
            "organizations": ["FudanNLP"],
            "review_only": {"FoodNLP": ["FudanNLP"]},
        },
    )

    entity = report["entities"][0]
    variants = {item["text"]: item for item in entity["variants"]}
    assert entity["canonical"] == "FudanNLP"
    assert entity["recommendation"] == "review_only"
    assert variants["Fudan NLP"]["sources"] == ["ascii_normalized"]
    assert variants["FoodNLP"]["sources"] == ["review_only"]
    assert variants["FoodNLP"]["timestamps"][0]["time"] == "00:00:01"


def test_entity_consistency_reports_cjk_near_misses_in_review_markdown():
    report = build_entity_consistency_report(
        [{"start": 5.0, "end": 6.0, "text": "今天请到孙天详聊天。"}],
        {"people": ["孙天祥"]},
    )
    review = {"summary": {}, "issues": [], "segments": [], "entity_consistency": report}

    assert report["summary"]["variant_count"] == 1
    assert report["entities"][0]["variants"][0]["text"] == "孙天详"
    markdown = review_to_markdown(review)
    assert "Entity Consistency" in markdown
    assert "孙天详" in markdown
