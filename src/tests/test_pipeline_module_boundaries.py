import importlib


def test_pipeline_modules_import_without_side_effect_cycles():
    package_modules = [
        "atot.pipeline.asr",
        "atot.pipeline.audio_cache",
        "atot.pipeline.chunks",
        "atot.pipeline.identity",
        "atot.pipeline.postprocess",
        "atot.pipeline.runinfo",
    ]
    compat_modules = [
        "atot.pipeline_asr",
        "atot.pipeline_audio",
        "atot.pipeline_chunks",
        "atot.pipeline_identity",
        "atot.pipeline_postprocess",
        "atot.pipeline_runinfo",
    ]

    imported = [importlib.import_module(name) for name in package_modules + compat_modules]

    assert [module.__name__ for module in imported[: len(package_modules)]] == package_modules
    assert (
        importlib.import_module("atot.pipeline_asr").ASRChunkCacheDecision
        is importlib.import_module("atot.pipeline.asr").ASRChunkCacheDecision
    )
    assert (
        importlib.import_module("atot.pipeline_identity")._sha256_json
        is importlib.import_module("atot.pipeline.identity")._sha256_json
    )
