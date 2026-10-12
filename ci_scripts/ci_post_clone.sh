#!/bin/sh
set -eu

REPO_ROOT="${CI_PRIMARY_REPOSITORY_PATH:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"

echo "[ci_post_clone] repo root: $REPO_ROOT"
cd "$REPO_ROOT"

if [ ! -f configs/generate_xcodeproj.py ]; then
    echo "[ci_post_clone] missing configs/generate_xcodeproj.py" >&2
    exit 1
fi

if [ ! -f source_roots.lock.jsonc ]; then
    if [ ! -f source_roots.lock.jsonc.in ]; then
        echo "[ci_post_clone] missing source_roots.lock.jsonc.in" >&2
        exit 1
    fi
    echo "[ci_post_clone] materializing active source root config"
    cp source_roots.lock.jsonc.in source_roots.lock.jsonc
fi

echo "[ci_post_clone] generating Audio2Text.xcodeproj"
python3 configs/generate_xcodeproj.py

if [ ! -f Audio2Text.xcodeproj/project.pbxproj ]; then
    echo "[ci_post_clone] Audio2Text.xcodeproj/project.pbxproj was not generated" >&2
    exit 1
fi

if [ ! -f Audio2Text.xcodeproj/xcshareddata/xcschemes/Audio2TextApp.xcscheme ]; then
    echo "[ci_post_clone] missing Audio2TextApp shared scheme" >&2
    exit 1
fi

if [ ! -f Audio2Text.xcodeproj/xcshareddata/xcschemes/Audio2Text-iOS.xcscheme ]; then
    echo "[ci_post_clone] missing Audio2Text-iOS shared scheme" >&2
    exit 1
fi

echo "[ci_post_clone] Xcode project is ready"
