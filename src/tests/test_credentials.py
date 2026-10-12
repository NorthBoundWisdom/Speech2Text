import os

import pytest

from atot import credentials
from atot.config import load_app_config
from atot.config_v2 import load_atot_config, set_config_value


def test_legacy_key_migration_preserves_config_and_removes_plaintext(tmp_path, isolated_credentials):
    path = tmp_path / 'config.toml'
    path.write_text('# keep this comment\n[cloud]\napi_key = "legacy-test-key"\nmodel = "test"\n[ui]\ntheme = "dark"\n')
    assert load_app_config(path).cloud.api_key == 'legacy-test-key'
    text = path.read_text()
    assert 'legacy-test-key' not in text
    assert 'keep this comment' in text and 'theme = "dark"' in text
    assert load_atot_config(path).cloud.api_key == 'legacy-test-key'
    if os.name != 'nt':
        assert path.stat().st_mode & 0o777 == 0o600


def test_migration_failure_keeps_original_config(tmp_path, monkeypatch):
    path = tmp_path / 'config.toml'
    original = '[cloud]\napi_key = "legacy-test-key"\n'
    path.write_text(original)
    def unavailable():
        raise RuntimeError('unavailable')
    monkeypatch.setattr(credentials, 'credential_backend', unavailable)
    with pytest.raises(RuntimeError, match='system storage'):
        load_app_config(path)
    assert path.read_text() == original


def test_set_key_uses_system_store_and_empty_value_removes_it(tmp_path):
    path = tmp_path / 'config.toml'
    set_config_value('cloud.api_key', 'test-key', path=path)
    assert 'test-key' not in path.read_text()
    assert load_atot_config(path).cloud.api_key == 'test-key'
    set_config_value('cloud.api_key', '', path=path)
    assert load_atot_config(path).cloud.api_key == ''
    assert credentials.credential_backend().get_password(credentials.SERVICE, credentials.account(path)) is None


def test_local_config_read_does_not_require_a_cloud_credential(tmp_path):
    path = tmp_path / 'config.toml'
    path.write_text('[cloud]\napi_key_store = "system"\n[local]\nasr_model = "large-v3-turbo"\n')
    before = path.read_bytes()
    assert load_atot_config(path, include_api_key=False).local.asr_model == 'large-v3-turbo'
    assert load_app_config(path, include_api_key=False).local.asr_model == 'large-v3-turbo'
    assert path.read_bytes() == before
    with pytest.raises(RuntimeError, match='missing'):
        load_app_config(path)


def test_writes_to_symlink_config_are_rejected(tmp_path):
    victim = tmp_path / 'victim'
    victim.write_text('untouched')
    path = tmp_path / 'config.toml'
    path.symlink_to(victim)
    with pytest.raises(ValueError, match='symlink'):
        credentials.write_private_config(path, 'replacement')
    assert victim.read_text() == 'untouched'


def test_cli_stdin_key_is_not_echoed_or_written_to_config(tmp_path, monkeypatch, capsys):
    from io import StringIO
    from atot import cli
    monkeypatch.setattr(cli.sys, 'stdin', StringIO('synthetic-stdin-key\n'))
    assert cli.main(['config', 'set', 'cloud.api_key', '--stdin']) == 0
    output = capsys.readouterr()
    assert 'synthetic-stdin-key' not in output.out + output.err
    assert 'synthetic-stdin-key' not in (tmp_path / 'config.toml').read_text()
    assert load_atot_config(tmp_path / 'config.toml').cloud.api_key == 'synthetic-stdin-key'


def test_config_errors_do_not_echo_values():
    from atot.config_v2 import parse_toml_value
    secret = 'synthetic-sensitive-value'
    with pytest.raises(ValueError) as error:
        parse_toml_value('"' + secret)
    assert secret not in str(error.value)


def test_explicit_key_override_can_clear_or_replace_without_reading_keychain(tmp_path):
    path = tmp_path / 'config.toml'
    path.write_text('[cloud]\napi_key_store = "system"\n')
    assert load_atot_config(path, overrides=['cloud.api_key=""']).cloud.api_key == ''
    assert load_atot_config(path, overrides=['cloud.api_key="test-override"']).cloud.api_key == 'test-override'
    assert 'test-override' not in path.read_text()
