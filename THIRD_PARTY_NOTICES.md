# Third-party components

SonaFolio's original source is licensed under MIT (see LICENSE). This grant does not relicense
its dependencies, optional model weights, downloaded media, or externally supplied runtimes.

- **FreeCM**: MIT, Copyright (c) 2026 FreeCM. Its full license is in `FreeCM/LICENSE`.
  FreeCM is a development/build dependency and is not part of the Python runtime wheel.
  Python source distributions contain the CLI source; App, Qt and FreeCM development sources
  are available from the repository rather than bundled into the CLI sdist.
- **Python dependencies**: installed separately by the package manager. Their distribution metadata,
  licenses and notices remain in each installed package. A wheel of SonaFolio does not contain
  these dependencies. A release that embeds Python and its dependencies must inventory them.
- **Website localization**: mkdocs-static-i18n is MIT-licensed and installed as a website build
  dependency. It is not bundled into the ASR runtime or native client installers. Its upstream
  source and license are at https://github.com/ultrabug/mkdocs-static-i18n.
- **Qt**: the license depends on the selected modules and build. Open-source Qt can contain LGPL,
  GPL and other third-party code. See https://doc.qt.io/qt-6/licensing.html and
  https://doc.qt.io/qt-6/licenses-used-in-qt.html. The release inventory must describe the actual
  deployed libraries, plugins and resources, including their notices and corresponding sources.
- **GeoControls**: MIT, Copyright (c) 2026 Shanghai Astroform Software Ltd. The Qt client
  embeds its controls, application shell and icon resources from the exact revision in
  `source_roots.lock.jsonc.in`. The upstream license is available at
  https://github.com/NorthBoundWisdom/GeoControls/blob/main/LICENSE and is copied into
  Qt package licenses with a pinned-revision component record. It is not part of the
  Python wheel, Swift client or ASR runtime.
- **FFmpeg/ffprobe**: the license depends on build options and linked components. Builds with
  `--enable-gpl` or `--enable-version3` have different obligations; a build with `--enable-nonfree`
  must not be redistributed. See https://ffmpeg.org/legal.html. Native release packaging records
  actual build information and requires matching distribution materials. It does not assume LGPL.
- **Python and Microsoft runtime DLLs**: optional Windows bundles must include their actual licenses,
  notices and redistribution terms; they are not covered by SonaFolio's MIT license.
- **Models**: no weights are included. Download URLs and required files are in
  `src/atot/data/model_inventory.json`. Consult the linked upstream model card/license before
  downloading or redistributing a model.
- **Gold reference text**: the text fixtures under `tests/gold/` are selected rows from Mozilla
  Common Voice 21.0 Chinese (CC0-1.0), obtained from the named Hugging Face mirror. The fixture
  metadata records the dataset revision, split and row provenance. No corpus audio is committed.
  Common Voice licensing: https://commonvoice.mozilla.org/en/terms;
  CC0 text: https://creativecommons.org/publicdomain/zero/1.0/legalcode.

Native release archives include their own `licenses/`, `third-party-components.json` and
`sbom.cdx.json`. Follow `doc/RELEASE_LICENSES.md` to provide and verify redistribution materials.
