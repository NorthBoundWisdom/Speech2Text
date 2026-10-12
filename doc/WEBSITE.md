# SonaFolio website and GitHub Pages

Website: <https://northboundwisdom.github.io/sonafolio/>.
Source: `website/`. Output: `build/website/`. Workflow: `.github/workflows/website-pages.yml`.

The site follows the handbook structure of sibling project Ravo. The English home page introduces the
product, workflow, and platform boundaries; guides cover installation, transcription, library, MCP,
CLI, QA, privacy, and troubleshooting. Material provides search, color schemes, code copying, and
mobile navigation. No analytics or remote fonts are configured.

## Local preview

Use a separate build environment:

```bash
python3 -m venv build/website-env
build/website-env/bin/python -m pip install -r website/requirements.txt
NO_MKDOCS_2_WARNING=true build/website-env/bin/python -m mkdocs serve -f website/mkdocs.yml
```

On Windows use `build\website-env\Scripts\python.exe` and set
`$env:NO_MKDOCS_2_WARNING = "true"`. This suppresses Material's MkDocs 2 migration advisory only;
ordinary strict-build warnings remain failures.

## Validate

```bash
python3 configs/check_docs.py
build/website-env/bin/python -m pytest website/tests/test_build_metadata.py
NO_MKDOCS_2_WARNING=true build/website-env/bin/python -m mkdocs build -f website/mkdocs.yml --strict
python3 configs/check_docs.py --site build/website
```

The home page shows the current Git commit and actual UTC build time, with escaped commit text.
`SONAFOLIO_SITE_BUILT_AT` accepts an offset-bearing timestamp for reproducible time display.
Commit messages must not contain private information.

## Deploy and maintain

Pages uses GitHub Actions. Pushes to `main` check links, metadata, public source, and the strict build,
then upload a separate artifact and deploy through the `github-pages` environment. PRs do not deploy.
Generated HTML and `gh-pages` branches are not source. Only the deployment job has Pages write and
OIDC permissions. Checkout includes FreeCM so the complete public-source audit can run.

Website deployment does not create application tags or packages; `release.yml` handles native
releases. Download links point to Releases, and successful Actions trials are not advertised as
published versions. Keep capabilities, signing, and model requirements aligned with source.

Use English for default pages and navigation. Localized translations belong in explicit locale
resources. Internal architecture and measured research remain in `doc/`, rather than on the product
home page. See [branding](BRANDING.md).
