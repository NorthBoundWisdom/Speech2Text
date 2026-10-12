import importlib


def test_qa_modules_import_without_side_effect_cycles():
    package_modules = [
        "atot.qa.artifacts",
        "atot.qa.builder",
        "atot.qa.chunks",
        "atot.qa.confidence",
        "atot.qa.issues",
        "atot.qa.payloads",
        "atot.qa.policy",
        "atot.qa.readable",
        "atot.qa.repair",
        "atot.qa.report",
        "atot.qa.scoring",
        "atot.qa.text",
        "atot.qa.timing",
    ]
    compat_modules = [
        "atot.qa_artifacts",
        "atot.qa_builder",
        "atot.qa_chunks",
        "atot.qa_confidence",
        "atot.qa_issues",
        "atot.qa_payloads",
        "atot.qa_policy",
        "atot.qa_readable",
        "atot.qa_repair",
        "atot.qa_report",
        "atot.qa_scoring",
        "atot.qa_text",
        "atot.qa_timing",
    ]

    imported = [importlib.import_module(name) for name in package_modules + compat_modules]

    assert [module.__name__ for module in imported[: len(package_modules)]] == package_modules
    assert (
        importlib.import_module("atot.qa_policy").IssueType
        is importlib.import_module("atot.qa.policy").IssueType
    )
    assert (
        importlib.import_module("atot.qa_report").qa_to_markdown
        is importlib.import_module("atot.qa.report").qa_to_markdown
    )
