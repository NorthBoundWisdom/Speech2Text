from atot.pipeline import _job_dir

from atot.paths import (
    DEFAULT_GLOSSARY_FILE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PROMPT_FILE,
    PROCESS_DIR,
    path_context,
)


def test_default_job_dir_groups_process_input_under_output_root():
    input_path = (
        PROCESS_DIR
        / "0527"
        / "对话日行迹创始人孙天祥"
        / "001-对话日行迹创始人孙天祥-当AI自动写出顶会论文.m4a"
    )

    assert (
        _job_dir(input_path, DEFAULT_OUTPUT_DIR, None)
        == DEFAULT_OUTPUT_DIR / "0527" / "对话日行迹创始人孙天祥"
    )


def test_default_job_dir_keeps_explicit_name_inside_output_batch():
    input_path = (
        PROCESS_DIR
        / "0527"
        / "对话日行迹创始人孙天祥"
        / "001-对话日行迹创始人孙天祥-当AI自动写出顶会论文.m4a"
    )

    assert (
        _job_dir(input_path, DEFAULT_OUTPUT_DIR, "episode-large-turbo")
        == DEFAULT_OUTPUT_DIR / "0527" / "episode-large-turbo"
    )


def test_default_runtime_resources_are_packaged():
    assert DEFAULT_PROMPT_FILE.exists()
    assert DEFAULT_GLOSSARY_FILE.exists()
    assert DEFAULT_PROMPT_FILE.parent.name == "data"
    assert DEFAULT_PROMPT_FILE.parent.parent.name == "atot"


def test_path_context_uses_explicit_data_root_environment(monkeypatch, tmp_path):
    data_root = tmp_path / "SpeechToTextData"
    monkeypatch.setenv("ATOT_DATA_ROOT", str(data_root))

    context = path_context()

    assert context.output_dir == data_root / "work"
    assert context.process_dir == data_root / "materials"
    assert context.materials_dir == context.process_dir
    assert context.work_dir == context.output_dir
    assert _job_dir(context.process_dir / "batch" / "episode.m4a", None, None) == (
        context.output_dir / "batch"
    )
