# Gold Transcript Fixtures

This directory stores public, text-only gold references for regression benchmarking. The current
references are concatenated Mozilla Common Voice zh-CN test-split clips. Audio files remain local
runtime assets and are not committed.

Audio files are intentionally not committed. To run the gold benchmark, place matching local WAV
files next to these references or copy the text fixtures next to the local WAV files:

```text
ai_podcast_2min.wav
coffee_podcast_2min.wav
casual_talk_2min.wav
```

Each sample has:

- `<name>.ref.txt`: manually reviewed reference text.
- `<name>.terms.json`: expected key terms.
- `<name>.meta.json`: source, time range, and known difficulty notes.

Committed metadata records the public dataset rows used to build each local WAV. Local WAV files
should be generated under the data root or copied next to these references for a runtime-only run.
