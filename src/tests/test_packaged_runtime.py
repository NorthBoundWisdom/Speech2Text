import json
import os
import sys

import pytest

from configs import check_packaged_runtime as checker


def marker(client='qt'):
    return json.dumps({'type': 'sonafolio.native_startup', 'version': 1,
                       'client': client, 'first_frame': True})


@pytest.mark.parametrize('text', ['', 'QML loaded', marker('swift'),
                                  json.dumps({'type': 'sonafolio.native_startup',
                                              'version': 1, 'client': 'qt', 'first_frame': False})])
def test_successful_process_without_matching_native_frame_is_rejected(text):
    with pytest.raises(RuntimeError, match='first-frame'):
        checker.require_frame(text, 'qt')


def test_native_marker_can_follow_loader_diagnostics():
    checker.require_frame('Qt loader diagnostics\n' + marker() + '\n', 'qt')


def test_package_environment_has_no_developer_library_search_paths(tmp_path, monkeypatch):
    monkeypatch.setenv('QT_PLUGIN_PATH', 'private-sdk')
    monkeypatch.setenv('QML_IMPORT_PATH', 'private-qml')
    monkeypatch.setenv('LD_LIBRARY_PATH', 'private-libraries')
    monkeypatch.setenv('DYLD_FRAMEWORK_PATH', 'private-frameworks')
    monkeypatch.setenv('PATH', 'private-sdk/bin')
    monkeypatch.setenv('SystemRoot', str(tmp_path / 'Windows'))
    env = checker.runtime_environment(tmp_path)
    for key in ('QT_PLUGIN_PATH', 'QML_IMPORT_PATH', 'LD_LIBRARY_PATH', 'DYLD_FRAMEWORK_PATH'):
        assert key not in env
    assert 'private-sdk' not in env['PATH']
    assert env['QT_QPA_PLATFORM'] not in {'offscreen', 'minimal'}
    assert env['ATOT_DATA_ROOT'] == str(tmp_path / 'data')


def test_failure_preserves_loader_output(tmp_path):
    with pytest.raises(RuntimeError, match='exited 3'):
        checker.run_logged([sys.executable, '-c',
                            'import sys; print("missing-library diagnostic"); sys.exit(3)'],
                           tmp_path, dict(os.environ), 'loader')
    assert 'missing-library diagnostic' in (tmp_path / 'loader.log').read_text()


def test_provenance_failure_is_recorded_without_running_package(tmp_path, monkeypatch):
    artifact = tmp_path / 'package.dmg'
    artifact.write_bytes(b'synthetic-package')
    artifact.with_suffix('.dmg.build.json').write_text(json.dumps({
        'asset': artifact.name, 'sha256': checker.sha256(artifact), 'commit': 'wrong',
    }))
    monkeypatch.setattr(checker, 'launch_package', lambda *_: pytest.fail('Package must not run.'))
    evidence = tmp_path / 'evidence.json'
    with pytest.raises(RuntimeError, match='provenance'):
        checker.verify(artifact, 'qt', tmp_path / 'work', evidence, 'expected')
    assert json.loads(evidence.read_text())['success'] is False
