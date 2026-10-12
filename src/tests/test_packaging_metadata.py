import subprocess
import sys
import tarfile
from pathlib import Path


def test_cli_sdist_contains_license_and_excludes_local_vendor_data(tmp_path):
    repo = Path(__file__).resolve().parents[2]
    for name in ('pyproject.toml', 'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'constraints/runtime.txt'):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((repo / name).read_bytes())
    source = tmp_path / 'src' / 'atot' / '__init__.py'
    source.parent.mkdir(parents=True)
    source.write_text('__version__ = "0.1.0"\n')
    # Reproduce the ignored submodule-local dependency that previously leaked into sdist.
    vendor = tmp_path / 'FreeCM' / 'vscode-extension' / 'node_modules' / 'private.txt'
    vendor.parent.mkdir(parents=True)
    vendor.write_text('synthetic local-only data')
    (tmp_path / 'config.toml').write_text('synthetic private config')
    output = tmp_path / 'dist'
    subprocess.run([sys.executable, '-m', 'hatchling', 'build', '-t', 'sdist', '-d', str(output)],
                   cwd=tmp_path, check=True, capture_output=True)
    with tarfile.open(next(output.glob('*.tar.gz'))) as archive:
        names = archive.getnames()
    assert any(n.endswith('/LICENSE') for n in names)
    assert any(n.endswith('/THIRD_PARTY_NOTICES.md') for n in names)
    assert any(n.endswith('/src/atot/__init__.py') for n in names)
    assert not any('node_modules' in n or '/FreeCM/' in n or n.endswith('/config.toml') for n in names)
