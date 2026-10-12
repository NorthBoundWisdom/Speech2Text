from __future__ import annotations

import os
import tempfile

import pytest

# Establish the root before test collection imports module-level path constants.
_TEST_DATA = tempfile.TemporaryDirectory(prefix="atot-tests-")
os.environ["ATOT_DATA_ROOT"] = _TEST_DATA.name


class MemoryCredentials:
    def __init__(self):
        self.values = {}

    def get_password(self, service, username):
        return self.values.get((service, username))

    def set_password(self, service, username, password):
        self.values[service, username] = password

    def delete_password(self, service, username):
        self.values.pop((service, username), None)


@pytest.fixture(autouse=True)
def isolated_credentials(monkeypatch, tmp_path):
    # Tests never touch the developer's real OS credential store.
    from atot import config, config_v2
    monkeypatch.setattr(config, "config_path", lambda: tmp_path / "config.toml")
    monkeypatch.setattr(config_v2, "config_path", lambda: tmp_path / "config.toml")
    from atot import credentials
    backend = MemoryCredentials()
    monkeypatch.setattr(credentials, "credential_backend", lambda: backend)
    return backend
