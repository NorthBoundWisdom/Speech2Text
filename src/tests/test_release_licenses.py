import hashlib
import json

import pytest

from configs.release_licenses import stage_release_licenses


def manifest(tmp_path, *, license='GPL-3.0-or-later'):
    staged = tmp_path / 'stage'
    staged.mkdir()
    binary = staged / 'ffmpeg.exe'
    binary.write_bytes(b'MZsynthetic-test-runtime')
    materials = tmp_path / 'materials'
    materials.mkdir()
    component = {'name': 'ffmpeg', 'version': 'test', 'license': license,
                 'files': [{'path': binary.name, 'sha256': hashlib.sha256(binary.read_bytes()).hexdigest()}]}
    for category in ('license_files', 'source_archives', 'build_files'):
        path = materials / f'{category}.txt'
        path.write_text(f'Synthetic test material: {category}')
        component[category] = [{'path': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}]
    path = materials / 'manifest.json'
    path.write_text(json.dumps({'schema_version': 1, 'components': [component]}))
    return staged, path, component


def test_package_rejects_missing_redistribution_materials(tmp_path):
    staged, _, _ = manifest(tmp_path)
    with pytest.raises(ValueError, match='third-party-materials'):
        stage_release_licenses(staged, None)


def test_package_stages_licenses_sources_and_inventory(tmp_path):
    staged, path, _ = manifest(tmp_path)
    stage_release_licenses(staged, path)
    inventory = json.loads((staged / 'third-party-components.json').read_text())
    assert inventory['components'][0]['license'] == 'GPL-3.0-or-later'
    assert (staged / 'licenses' / 'LICENSE').is_file()
    assert len(inventory['components'][0]['source_materials']) == 2
    assert json.loads((staged / 'sbom.cdx.json').read_text())['bomFormat'] == 'CycloneDX'


@pytest.mark.parametrize('change', ['binary', 'license', 'source', 'unattributed'])
def test_package_rejects_changed_incomplete_or_unknown_materials(tmp_path, change):
    staged, path, component = manifest(tmp_path)
    if change == 'binary':
        (staged / 'ffmpeg.exe').write_bytes(b'MZchanged')
    elif change == 'license':
        component['license'] = 'NOASSERTION'
    elif change == 'source':
        component['source_archives'] = []
    else:
        (staged / 'extra.dll').write_bytes(b'MZextra')
    path.write_text(json.dumps({'schema_version': 1, 'components': [component]}))
    with pytest.raises(ValueError):
        stage_release_licenses(staged, path)


def test_release_manifest_cannot_copy_private_external_files(tmp_path):
    staged, path, component = manifest(tmp_path)
    component['license_files'][0]['path'] = '../private.txt'
    path.write_text(json.dumps({'schema_version': 1, 'components': [component]}))
    with pytest.raises(ValueError, match='contained'):
        stage_release_licenses(staged, path)


def test_release_rejects_external_directory_symlinks(tmp_path):
    staged, path, _ = manifest(tmp_path)
    external = tmp_path / 'private'
    external.mkdir()
    (staged / 'external').symlink_to(external, target_is_directory=True)
    with pytest.raises(ValueError, match='External symlink'):
        stage_release_licenses(staged, path)
