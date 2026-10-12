#!/usr/bin/env bash
set -euo pipefail

INPUT="${1:?usage: src/scripts/create_sample_from_episode.sh input.m4a [start_seconds] [duration_seconds]}"
START="${2:-240}"
DURATION="${3:-120}"
OUT="${4:-$HOME/Documents/SpeechToTextData/materials/sample_04m_2min.wav}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON="$HOME/Documents/SpeechToTextData/env/bin/python"

mkdir -p "$(dirname "$OUT")"
if command -v ffmpeg >/dev/null 2>&1; then
  ffmpeg -hide_banner -loglevel error -y \
    -ss "$START" -t "$DURATION" -i "$INPUT" \
    -ac 1 -ar 16000 -c:a pcm_s16le "$OUT"
else
  "$PYTHON" - "$INPUT" "$START" "$DURATION" "$OUT" <<'PY'
from pathlib import Path
import sys
import tempfile

from atot.audio import prepare_audio, write_wav_chunk

input_path = Path(sys.argv[1])
start = float(sys.argv[2])
duration = float(sys.argv[3])
out = Path(sys.argv[4])
with tempfile.TemporaryDirectory() as tmp:
    prepared = prepare_audio(input_path, Path(tmp) / "prepared.wav", overwrite=True)
    write_wav_chunk(prepared, out, start, duration)
PY
fi
echo "$OUT"
