# Quality Tooling

This note records the current P2 quality-tooling baseline.

## Coverage

Coverage support is available through the `dev` extra:

```bash
python -m pip install -e ".[dev]"
python -m pytest --cov=atot --cov-report=term-missing:skip-covered
```

The default `pytest` command intentionally stays fast and does not force coverage.

## Mypy

The strict mypy scope covers the source package:

```bash
python -m mypy
```

Keep the configured file list aligned with `src/atot` unless a temporary third-party typing issue
requires a documented exception.

## Architecture Boundary Checks

Architecture boundary behavior is covered by focused contract tests:

```bash
python -m pytest \
  src/tests/test_backend_profile_boundaries.py \
  src/tests/test_validate_backend_promotion.py \
  src/tests/test_service_contract.py
```

These tests cover backend implementation import boundaries, backend promotion evidence, and the
shared service command contract.

## Security Audit

Dependency auditing is available through:

```bash
python -m pip_audit --progress-spinner off
```

The reproducibility baseline is CPython 3.13 on macOS arm64. The public package keeps Python 3.10+
compatibility, while `configs/setup_local_app.py` consumes `constraints/runtime.txt` for
cross-platform security floors and upgrades an existing editable environment when those floors are
stale. A full `pip freeze` remains intentionally out of source because it would capture
platform-specific ML packages and local toolchain state.

The 2026-10-12 macOS arm64 environment refresh passed `pip check` and `pip-audit` with no known
vulnerabilities and no vulnerability exclusions. The local editable `audio2text-local` package is
not on PyPI and remains outside the audit's third-party package coverage. The previous
`CVE-2025-3000` exclusion is no longer needed for this refreshed environment.

## Dependency Locking

The repository does not commit a `pip freeze` lockfile. Public dependency intent remains in
`pyproject.toml`; auditable security floors live in `constraints/runtime.txt`; the validation target
is CPython 3.13 on macOS arm64. Windows remains a supported CLI target and consumes the same
platform-neutral constraints while its backend dependencies continue to use environment markers.

To explicitly refresh the runtime and development dependencies to the newest compatible versions,
run this from the repository root with the data-root environment activated:

```bash
python -m pip install --upgrade --upgrade-strategy eager --constraint constraints/runtime.txt -e ".[dev]"
python -m pip check
python -m ruff check .
python -m mypy
python -m pytest
python -m pip_audit --progress-spinner off
```

`setup_local_app.py` repairs the runtime as needed; it does not refresh every dependency on each
build. Respect upstream dependency bounds during an explicit refresh. For example, the validated
SymPy dependency requires `mpmath<1.4`, so `mpmath` remains at 1.3.0 even when 1.4.1 is available.

The 2026-10-12 validation used CPython 3.13, MLX Whisper 0.4.3, MLX 0.32.3, NumPy 2.5.4,
Transformers 5.19.0, Hugging Face Hub 2.2.0, PyTorch 2.14.1, Typer 0.27.3, Ruff 0.17.0,
and mypy 2.4.0. All 497 Python tests and 155 Swift tests passed. A short, locally synthesized
Chinese speech sample also passed the default `large-v3-turbo` transcription path with network
model access disabled. This smoke check confirms runtime compatibility, not long-form ASR quality.
Windows dependencies and CUDA execution were not validated on this macOS host.

The same maintenance pass built the macOS and iOS Simulator Release targets with Xcode 27 / Swift
6.4, and built and loaded the Qt/QML client with Qt 6.12.0. These builds emitted no compiler
warnings. The Qt target enables `/W4` with MSVC and `-Wall -Wextra -Wpedantic` with Clang/GCC;
single-config CMake generators receive `CMAKE_BUILD_TYPE` from the requested configuration.
Configuration also refreshes cached Qt package directories and feature flags so existing builds
use the selected SDK without retaining feature values from an older Qt installation.
macOS FreeCM discovery now points to Qt 6.12.0. The Windows Qt path retains the supplied 6.11.2
configuration pending validation on Windows.

The Ruff rule selection is explicit in `pyproject.toml`, preserving the established `E4`, `E7`,
`E9`, and `F` gate across changes to Ruff's default rules. The App targets currently define no
App Intents, so the generated Xcode project skips their unused metadata extraction step. Remove
`LM_SKIP_METADATA_EXTRACTION` from the relevant target if App Intents are introduced.

## Hotspot Benchmark

A lightweight local benchmark is available for an existing output bundle:

```bash
python src/scripts/benchmark_quality_hotspots.py output/<batch>/<episode>
```

It reports median timings for correction application and QA report construction.

## Current CI and documentation baseline

The subsequent SonaFolio branding pass passed 587 Python tests, 198 Swift tests and the
Windows/Linux/macOS Qt build and smoke matrix. All four installer builds, including Windows
silent installation and installed-app launch, passed the build-only release workflow. These checks
validate packaging and software behavior; they do not claim real ASR accuracy, CUDA execution or
cloud API acceptance on every runner. Earlier dated dependency measurements above remain historical.

The website uses its own `website/requirements.txt`, independent of ASR dependencies. Its workflow
performs documentation-link checks, metadata tests and a strict MkDocs build before Pages deployment.
