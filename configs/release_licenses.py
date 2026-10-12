"""Fail-closed verification and staging of native release redistribution materials."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
_NATIVE_MAGICS = {b'MZ', b'\x7fELF', b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xfe\xed\xfa\xce', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca', b'\xca\xfe\xba\xbf', b'\xbf\xba\xfe\xca'}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _contained(root: Path, value: str) -> Path:
    path = root / value
    if Path(value).is_absolute() or '..' in Path(value).parts or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Release material path must be relative and contained in its root.')
    if not path.is_file():
        raise ValueError(f'Release material is missing: {value}')
    return path


def copy_project_licenses(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
        shutil.copy2(REPO_ROOT / name, destination / name)
    shutil.copy2(REPO_ROOT / 'FreeCM' / 'LICENSE', destination / 'FreeCM-LICENSE')


def _required_files(staging: Path) -> set[str]:
    required = set()
    for path in staging.rglob('*'):
        if path.is_symlink() and not path.resolve().is_relative_to(staging.resolve()):
            raise ValueError('External symlink in release: ' + path.relative_to(staging).as_posix())
        if not path.is_file() or 'licenses' in path.relative_to(staging).parts:
            continue
        rel = path.relative_to(staging).as_posix()
        if not path.resolve().is_relative_to(staging.resolve()):
            raise ValueError(f'External symlink in release: {rel}')
        with path.open('rb') as handle:
            magic = handle.read(4)
        native = magic in _NATIVE_MAGICS or magic[:2] in _NATIVE_MAGICS
        # Audio2Text's own executable is covered by the root MIT license.
        own_binary = path.name in {'Audio2TextQt', 'Audio2TextQt.exe'}
        python_payload = 'python' in path.relative_to(staging).parts
        vendor_asset = path.suffix.lower() in {'.qml', '.js', '.rcc', '.pak', '.qm'}
        if (native and not own_binary) or python_payload or vendor_asset:
            required.add(rel)
    return required


def stage_release_licenses(staging: Path, manifest_path: Path | None) -> None:
    copy_project_licenses(staging / 'licenses')
    required = _required_files(staging)
    if required and manifest_path is None:
        raise ValueError('Native release requires --third-party-materials manifest.json; see doc/RELEASE_LICENSES.md.')
    if manifest_path is None:
        components: list[dict[str, Any]] = []
    else:
        document = json.loads(manifest_path.read_text(encoding='utf-8'))
        if document.get('schema_version') != 1 or not isinstance(document.get('components'), list):
            raise ValueError('Invalid third-party materials manifest.')
        materials = manifest_path.resolve().parent
        components = []
        covered: set[str] = set()
        names: set[str] = set()
        for component in document['components']:
            name = component.get('name', '')
            license_id = component.get('license', '')
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', name) or name in names:
                raise ValueError('Third-party component names must be unique safe identifiers.')
            names.add(name)
            if not component.get('version') or not license_id or license_id in {'UNKNOWN', 'NOASSERTION'}:
                raise ValueError(f'Component {name} needs a version and an actual license expression.')
            if not component.get('license_files') or not component.get('files'):
                raise ValueError(f'Component {name} needs license texts and file hashes.')
            destination = staging / 'licenses' / name
            destination.mkdir(parents=True, exist_ok=True)
            rows = []
            for row in component['files']:
                path = _contained(staging, row['path'])
                digest = _sha(path)
                if digest != row.get('sha256') or row['path'] in covered:
                    raise ValueError(f'Changed or multiply attributed release file: {row["path"]}')
                covered.add(row['path'])
                rows.append({'path': row['path'], 'sha256': digest})
            license_files = []
            sources = []
            for category in ('license_files', 'source_archives', 'build_files'):
                if ('GPL' in license_id or 'MPL' in license_id) and category != 'license_files' and not component.get(category):
                    raise ValueError(f'Component {name} requires corresponding sources and build files.')
                for row in component.get(category, []):
                    path = _contained(materials, row['path'])
                    digest = _sha(path)
                    if digest != row.get('sha256'):
                        raise ValueError(f'Changed release material for {name}.')
                    target = destination / category / path.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists():
                        raise ValueError(f'Duplicate material filename for {name}.')
                    shutil.copy2(path, target)
                    record = {'path': target.relative_to(staging).as_posix(), 'sha256': digest}
                    if category == 'license_files':
                        license_files.append(record)
                    else:
                        sources.append(record)
            components.append({'name': name, 'version': component['version'], 'license': license_id,
                               'files': rows, 'license_files': license_files, 'source_materials': sources})
        if missing := required - covered:
            raise ValueError('Unattributed runtime files: ' + ', '.join(sorted(missing)[:12]))
    (staging / 'third-party-components.json').write_text(json.dumps({'schema_version': 1, 'components': components}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    sbom = {'bomFormat': 'CycloneDX', 'specVersion': '1.6', 'version': 1,
            'components': [{'type': 'library', 'name': c['name'], 'version': c['version'],
                            'licenses': [{'expression': c['license']}],
                            'properties': [{'name': 'audio2text:files', 'value': json.dumps(c['files'])}]}
                           for c in components]}
    (staging / 'sbom.cdx.json').write_text(json.dumps(sbom, indent=2) + '\n', encoding='utf-8')
