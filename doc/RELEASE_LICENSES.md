# Native release licenses

The root MIT license covers SonaFolio's original source. It does not cover bundled dependencies.
Python wheels include LICENSE and THIRD_PARTY_NOTICES.md; dependencies are installed separately.
Swift macOS bundles include those files and FreeCM's license under Contents/Resources/licenses.

## Qt release gate

Pass `--third-party-materials materials/manifest.json` to `configs/qt_workflow.py package` on macOS
or Windows. Use a directory outside the repository (or under ignored build/) for these materials.
Without a reviewed manifest, native runtime packaging fails before an archive is created.
A failed gate leaves staging available for inspection; it is not a release.

The manifest must identify the exact deployed Qt plugins/frameworks, FFmpeg/ffprobe, their linked
libraries and optional Windows Python, Python packages and Microsoft runtimes. Inventories and
license metadata supplied by the actual vendors/builds are the starting point; do not infer LGPL
from a tool name or use a different version's sources. Use Qt's module licenses, third-party
notices and SBOM. For Homebrew FFmpeg, inspect the formula, receipt, `-version`, `-L` and linked
libraries. Homebrew binaries can be GPL builds and can depend on libraries outside the package.
A portable package must separately deploy those dependencies and account for them. The macOS
release gate rejects non-system absolute library references to avoid exporting developer-specific
runtime dependencies.

Example schema (hash placeholders must be replaced with actual SHA-256 values):

```json
{
  "schema_version": 1,
  "components": [{
    "name": "ffmpeg",
    "version": "actual-version",
    "license": "GPL-3.0-or-later",
    "files": [{"path": "ffmpeg.exe", "sha256": "actual-sha256"}],
    "license_files": [{"path": "ffmpeg/COPYING.GPLv3", "sha256": "actual-sha256"}],
    "source_archives": [{"path": "ffmpeg/matching-source.tar.xz", "sha256": "actual-sha256"}],
    "build_files": [{"path": "ffmpeg/build-instructions.txt", "sha256": "actual-sha256"}]
  }]
}
```

`files` paths are relative to the staged package; the other paths are relative to the manifest's
directory. File and material hashes must match. Each deployed native binary, Python payload and
vendor QML/JavaScript/resource file must have an attribution. Names must be unique. License texts
and notices are required; GPL/LGPL/MPL components also require source archives and build files.
Include patches, configurations, scripts and any installation/relinking materials required by the
specific license and delivery form. A URL alone is not accepted in place of corresponding source.

The gate copies redistribution materials into `licenses/<component>/`, writes a file inventory
with hashes to `third-party-components.json` and emits `sbom.cdx.json` (CycloneDX 1.6). Actual
FFmpeg license and enabled/disabled build flags are recorded beside each copied tool; builds with
`--enable-nonfree` are rejected. Unexpected files in a Windows Python runtime root and symlinks
are rejected; use a clean Python distribution, not a developer's custom environment.

The gate verifies completeness and matching bytes. A maintainer must still verify the accuracy of
license expressions, corresponding sources, redistribution rights, Qt relinking/installation
instructions, and any commercial Microsoft terms. It cannot determine legal rights from hashes.
No third-party binary or source archive is added to git by this workflow.

References: [FFmpeg legal guide](https://ffmpeg.org/legal.html),
[Qt licensing](https://doc.qt.io/qt-6/licensing.html),
[Qt third-party components](https://doc.qt.io/qt-6/licenses-used-in-qt.html).

## Models and media

Model weights and imported media are excluded from source and release packages. Upstream model
licenses and terms apply separately; the root MIT license grants no rights to them. Gold reference
text provenance is recorded in `tests/gold/*.meta.json` and THIRD_PARTY_NOTICES.md.
