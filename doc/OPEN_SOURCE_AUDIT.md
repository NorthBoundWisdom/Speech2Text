# Current-source open-source audit

Scope: the current host source and checked-out FreeCM submodule, reviewed on 2026-10-12.
Git history was excluded. Generated runtime data, model weights, media and private local settings
are not release source. This records fixes and the release boundary; it is not a legal certification.

| Finding | Resolution | Regression evidence |
|---|---|---|
| Episode/subscription IDs could escape storage roots and delete arbitrary directories | Shared ASCII identifier validation and root confinement cover library and task operations. Managed child symlinks and metadata identity mismatches are rejected. Deletion validates local targets before removing library records. | `test_storage_security.py` |
| Legacy HTTP allowed unauthenticated mutation/deletion and remote binds | Requires an independent random bearer token, loopback binding, exact Host, no Origin, JSON body type, bounded body size and no duplicate critical headers or transfer encoding. | `test_service_http_security.py` |
| Host license text and wheel licensing files were absent | Root MIT license added; Hatch uses SPDX metadata and includes LICENSE and THIRD_PARTY_NOTICES.md. Swift app bundles include license resources. CLI sdist uses an explicit file list, excluding FreeCM's local node_modules and other development artifacts. | Built wheel, sdist and app resources inspected |
| Native bundles lacked dependency attribution, license/source materials and a release gate | Exact file/material hashes, component licenses/notices and corresponding-source/build materials are required. Native inventory and CycloneDX SBOM are emitted. Nonfree FFmpeg and developer-specific macOS dependency paths are rejected; Windows Python source must be a clean distribution. | `test_release_licenses.py`, `test_qt_workflow.py`; actual Qt packaging refused missing materials |
| Privacy documentation claimed Keychain while config/UserDefaults held keys | macOS App/CLI share native Keychain by resolved config path, Windows CLI uses Credential Manager, iOS uses device-only Keychain. Legacy migration erases plaintext only after secure persistence. Failures preserve original settings and are reported. Local/MCP paths avoid cloud credential reads. | Synthetic credential migration/failure tests and native Python/Swift Keychain interoperability |
| Local runtime and credential paths were not all ignored | Root materials/work/library/cache/config, local Codex config, environment secrets and mypy cache are ignored. Public environment templates remain allowed. | `.gitignore` inspected |
| Public-source check ignored historical notes, unstaged tracked content and submodules; logs could expose matched tokens | Explicit staged/worktree/both scopes, current submodule recursion, Windows/Linux/macOS user paths, additional token/private-key patterns and masked output. Commit hook scans the staged source. | `test_check_public_paths.py`; full current-source check |
| Python 3.10 imported unavailable stdlib tomllib | Shared compatibility module uses tomli on Python 3.10 and stdlib tomllib on newer Python; conditional dependency declared. | Full Python 3.10 suite |
| Public template carried a personal signing team | Public team default is empty. Signing configuration belongs in ignored generated local settings. | `source_roots.lock.jsonc.in` |
| Gold text provenance could drift with the mirror's default branch | Metadata pins the mirror revision, split, row indices, stable clip names, sentence/reference hashes and CC0 links. Reference text and measured historical results are unchanged. | Mirror text rows matched to existing reference fixtures; no audio downloaded |

## Validation

- Python 3.13 and 3.10 suites, Ruff, mypy and `pip check`.
- Swift app/core tests and macOS/iOS simulator Release builds.
- Native Keychain interoperability used disposable synthetic values and cleaned up the test item.
- Wheel SPDX/license contents and Swift app license resources inspected.
- Current source plus FreeCM public-path/secret scan; no history scanned.
- `pip-audit` found no known third-party vulnerabilities in the maintained macOS environment;
  the unpublished local Audio2Text distribution itself is outside PyPI audit coverage.
- No real cloud API-key tests or cloud API calls. No model weights downloaded.

## Release boundary

Source publication and a distributable native bundle have different requirements. Qt release
archives require reviewed redistribution materials for the actual runtime build, as described in
[RELEASE_LICENSES.md](RELEASE_LICENSES.md). Hash and inventory checks cannot establish redistribution
rights or prove that supplied source archives are complete; the maintainer reviews those materials.
The local Homebrew FFmpeg is a GPL build and links external Homebrew libraries, so copying its
executables alone does not make a portable or documented release bundle. Such output is blocked.

The Windows credential backend and packaging rules have unit coverage but were not executed on a
Windows host in this macOS audit. iOS Keychain code was compiled for the simulator; device access
behavior was not tested on physical hardware. Model licenses and media rights remain separate from
the repository's MIT license. No existing binary release was uploaded or republished.
