from __future__ import annotations

from atot import platform_defaults


def test_default_asr_backend_uses_faster_whisper_on_windows(monkeypatch):
    monkeypatch.setattr(platform_defaults.platform, "system", lambda: "Windows")

    assert platform_defaults.default_asr_backend() == "faster-whisper"


def test_default_asr_backend_keeps_mlx_elsewhere(monkeypatch):
    monkeypatch.setattr(platform_defaults.platform, "system", lambda: "Darwin")

    assert platform_defaults.default_asr_backend() == "mlx-whisper"


def test_default_library_storage_uses_local_on_windows(monkeypatch):
    monkeypatch.setattr(platform_defaults.platform, "system", lambda: "Windows")

    assert platform_defaults.default_library_storage() == "local"


def test_default_library_storage_keeps_icloud_elsewhere(monkeypatch):
    monkeypatch.setattr(platform_defaults.platform, "system", lambda: "Darwin")

    assert platform_defaults.default_library_storage() == "icloud"
