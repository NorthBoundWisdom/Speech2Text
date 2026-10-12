import importlib.util
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "repository_language", Path(__file__).resolve().parents[2] / "configs/check_repository_language.py"
)
assert spec is not None and spec.loader is not None
language = importlib.util.module_from_spec(spec)
spec.loader.exec_module(language)


def test_unapproved_chinese_documentation_and_ui_fail():
    text = "UI label: " + chr(0x8D44) + chr(0x6599)
    policy = {"resources": {}, "embedded": {}}
    assert language.check_text("README.md", text, policy)
    assert language.check_text("app/Sources/View.swift", text, policy)


def test_language_exceptions_are_exact_and_do_not_cover_new_ui():
    fixture = 'text = "' + chr(0x4F60) + chr(0x597D) + '"'
    path = "src/tests/test_language.py"
    policy = {
        "resources": {},
        "embedded": {path: {"line_hashes": [language.line_hash(fixture)]}},
    }
    assert language.check_text(path, fixture, policy) == []
    assert language.check_text(path, fixture + "\n" + 'label = "' + chr(0x540C) + '"', policy)
    assert language.check_text("other.py", fixture, policy)


def test_localized_resource_exception_requires_the_exact_path():
    policy = {"resources": {"src/atot/data/prompt.zh.txt": "ASR prompt"}, "embedded": {}}
    text = chr(0x4F60)
    assert language.check_text("src/atot/data/prompt.zh.txt", text, policy) == []
    assert language.check_text("src/atot/data/new_prompt.txt", text, policy)
