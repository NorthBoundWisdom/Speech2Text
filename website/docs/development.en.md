# Development and contribution

Original source is MIT; dependencies, models, and media retain their terms. Chinese is the default with matching English website pages. Code/identifiers keep their real names and historical measurements retain evidence.

## Clients

```bash
git clone --recurse-submodules https://github.com/NorthBoundWisdom/sonafolio.git
cd sonafolio
python3 configs/setup_local_app.py
python3 configs/ios_workflow.py build --platform mac --scheme Audio2TextApp --configuration debug --distribution ad-hoc
python3 configs/ios_workflow.py build --platform ios --scheme Audio2Text-iOS --configuration debug
```

Mac output is build/app/SonaFolio.app; iOS validates the simulator. Qt uses your SDK/CMake:

```bash
python3 configs/qt_workflow.py config --configuration Release --qt-prefix <Qt-prefix>
python3 configs/qt_workflow.py smoke --configuration Release
```

Use actual local SDK paths without committing them. Backend promotion needs gates/semantic review, not only compilation.

## Checks and documentation

```bash
python -m ruff check .
python -m mypy
python -m pytest
python configs/check_docs.py
python configs/check_repository_language.py
```

Use the managed environment. Client READMEs describe Swift/Qt checks.

Website sources are in website/, output in build/website/. Chinese pages keep existing URLs, with index.en.md-style English companions built under en/. Translate all pages together; missing pairs fail documentation validation. Top header links retain the corresponding page. Strict builds/resources/policies precede Pages publication, and generated files, weights, recordings, keys, and libraries stay out of Git.

## Engineering references

- [Repository / English README](https://github.com/NorthBoundWisdom/sonafolio/blob/main/README.en.md)
- [Architecture](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/ARCHITECTURE.md)
- [Builds and extension](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/TECHNICAL_GUIDE.md)
- [Agent policy](https://github.com/NorthBoundWisdom/sonafolio/blob/main/AGENTS.md)
- [CI/tag releases](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/CI_RELEASES.md)
- [Third-party licensing](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/RELEASE_LICENSES.md)
- [Website maintenance](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/WEBSITE.md)

Research preserves original text/measurements. Package capabilities follow their release, and translated docs do not establish broader ASR validation.
