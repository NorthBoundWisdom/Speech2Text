#!/usr/bin/env python3
"""Launch final installer payloads on disposable CI runners without an SDK."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def runtime_environment(work: Path) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('QT_', 'QML', 'DYLD_'))
           and key not in {'LD_LIBRARY_PATH', 'LD_PRELOAD', 'CMAKE_PREFIX_PATH',
                           'QTDIR', 'QT_DIR', 'APPIMAGE', 'APPDIR', 'OWD',
                           'APPIMAGE_EXTRACT_AND_RUN', 'ATOT_CLI', 'ATOT_ATOT_PATH'}}
    if sys.platform == 'win32':
        system = Path(env.get('SYSTEMROOT') or env['SystemRoot'])
        env['PATH'] = os.pathsep.join(str(system / name) for name in ('System32', '', 'System32/Wbem'))
    else:
        env['PATH'] = '/usr/bin:/bin:/usr/sbin:/sbin'
    env['ATOT_DATA_ROOT'] = str(work / 'data')
    env['QT_QPA_PLATFORM'] = {'darwin': 'cocoa', 'win32': 'windows', 'linux': 'xcb'}[sys.platform]
    env['QT_QUICK_BACKEND'] = 'software'
    env['QT_DEBUG_PLUGINS'] = '1'
    return env


def run_logged(command: list[str], work: Path, env: dict[str, str], name: str,
               *, timeout: int = 90, accepted: tuple[int, ...] = (0,)) -> str:
    path = work / f'{name}.log'
    with path.open('w', encoding='utf-8') as log:
        log.write(f'command={command!r}\n')
        log.flush()
        result = subprocess.run(command, cwd=work, env=env, stdout=log,
                                stderr=subprocess.STDOUT, timeout=timeout, check=False)
    text = path.read_text(encoding='utf-8', errors='replace')
    if result.returncode not in accepted:
        raise RuntimeError(f'{name} exited {result.returncode}; see {path}\n{text[-8000:]}')
    return text


def require_frame(log: str, client: str) -> None:
    for line in log.splitlines():
        try:
            marker = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(marker, dict) and marker.get('type') == 'sonafolio.native_startup' \
                and marker.get('version') == 1 and marker.get('client') == client \
                and marker.get('first_frame') is True:
            return
    raise RuntimeError('The packaged application exited without native first-frame evidence.')


def launch_package(artifact: Path, client: str, work: Path, env: dict[str, str]) -> str:
    if sys.platform == 'darwin':
        mount = work / 'mounted'
        mount.mkdir()
        try:
            run_logged(['/usr/bin/hdiutil', 'attach', '-readonly', '-nobrowse',
                        '-mountpoint', str(mount), str(artifact)], work, env, 'dmg-mount')
            apps = list(mount.glob('*.app'))
            if len(apps) != 1:
                raise RuntimeError('The DMG must contain exactly one application.')
            app = work / apps[0].name
            shutil.copytree(apps[0], app, symlinks=True)
        finally:
            run_logged(['/usr/bin/hdiutil', 'detach', str(mount)], work, env, 'dmg-detach')
        run_logged(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app)],
                   work, env, 'signature')
        info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
        name = info['CFBundleExecutable']
        if Path(name).name != name:
            raise RuntimeError('Unsafe bundle executable name.')
        executable = app / 'Contents/MacOS' / name
        if not executable.resolve().is_relative_to(app.resolve()):
            raise RuntimeError('Bundle executable is outside the copied application.')
        command = [str(executable), '--startup-smoke']
        if client == 'qt':
            command += ['--data-root', env['ATOT_DATA_ROOT']]
    elif sys.platform == 'win32':
        if os.environ.get('GITHUB_ACTIONS') != 'true':
            raise RuntimeError('Installer verification requires a disposable GitHub Actions runner.')
        installed = work / 'installed'
        run_logged([str(artifact), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                    f'/DIR={installed}', f'/LOG={work / "installer.log"}'],
                   work, env, 'install', timeout=300, accepted=(0, 3010))
        command = [str(installed / 'bin/SonaFolioQt.exe'), '--startup-smoke',
                   '--data-root', env['ATOT_DATA_ROOT']]
    elif sys.platform == 'linux':
        if not env.get('DISPLAY'):
            raise RuntimeError('Linux native startup requires a virtual display (xvfb-run).')
        local = work / artifact.name
        shutil.copy2(artifact, local)
        local.chmod(local.stat().st_mode | 0o100)
        # Execute the final AppImage payload without requiring a privileged FUSE mount.
        command = [str(local), '--appimage-extract-and-run', '--startup-smoke',
                   '--data-root', env['ATOT_DATA_ROOT']]
    else:
        raise RuntimeError('Unsupported package verification platform.')
    return run_logged(command, work, env, 'native-startup')


def verify(artifact: Path, client: str, work: Path, evidence: Path, commit: str) -> None:
    if work.exists() and any(work.iterdir()):
        raise RuntimeError('Verification requires an empty work directory outside the checkout.')
    work.mkdir(parents=True, exist_ok=True)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    report = {'schema_version': 1, 'asset': artifact.name, 'client': client,
              'commit': commit, 'sha256': sha256(artifact), 'success': False}
    try:
        proof = json.loads(artifact.with_suffix(artifact.suffix + '.build.json').read_text())
        if proof['asset'] != artifact.name or proof['sha256'] != report['sha256'] \
                or proof['commit'] != commit or proof.get('dirty'):
            raise RuntimeError('Final package provenance does not match this workflow commit.')
        log = launch_package(artifact, client, work, runtime_environment(work))
        require_frame(log, client)
        report['success'] = True
        report['first_frame'] = True
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        evidence.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package-dir', type=Path, required=True)
    parser.add_argument('--pattern', required=True)
    parser.add_argument('--client', choices=['qt', 'swift'], required=True)
    parser.add_argument('--workdir', type=Path, required=True)
    parser.add_argument('--evidence-json', type=Path, required=True)
    parser.add_argument('--source-sha', required=True)
    args = parser.parse_args()
    files = list(args.package_dir.glob(args.pattern))
    if len(files) != 1:
        raise RuntimeError(f'Expected one final package, found {len(files)}.')
    verify(files[0].resolve(), args.client, args.workdir.resolve(),
           args.evidence_json.resolve(), args.source_sha)


if __name__ == '__main__':
    main()
