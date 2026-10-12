#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 path/to/local_transcribe_demo [repo-root]" >&2
  exit 2
fi

SRC="$1"
DST="${2:-.}"

if [[ ! -d "$SRC" ]]; then
  echo "Source demo folder does not exist: $SRC" >&2
  exit 1
fi

mkdir -p "$DST/process/imported-demo"
if [[ -f "$SRC/transcribe_mlx.py" ]]; then
  mkdir -p "$DST/src/scripts"
  cp -v "$SRC/transcribe_mlx.py" "$DST/src/scripts/transcribe_mlx.baseline.py"
fi
if [[ -f "$SRC/samples/sample_04m_2min.wav" ]]; then
  cp -v "$SRC/samples/sample_04m_2min.wav" "$DST/process/imported-demo/sample_04m_2min.wav"
fi
