#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 path/to/sample.wav" >&2
  exit 2
fi

SAMPLE="$1"
MODELS="${ATOT_BENCHMARK_MODELS:-small-4bit large-v3-turbo-q4}"
"$HOME/Documents/SpeechToTextData/env/bin/python" -m atot.cli benchmark "$SAMPLE" \
  --language zh \
  --prompt-file "$ROOT_DIR/src/atot/data/prompt.zh.txt" \
  --glossary-file "$ROOT_DIR/doc/examples/glossary.zh.json" \
  --repeat 2 \
  --models $MODELS
