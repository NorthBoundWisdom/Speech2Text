from __future__ import annotations

import argparse
import json

from ..benchmark import BenchmarkOptions, run_benchmark
from ..gold import GoldBenchmarkOptions, run_gold_benchmark


def cmd_benchmark(args: argparse.Namespace) -> int:
    summary = run_benchmark(
        BenchmarkOptions(
            sample_path=args.sample,
            output_dir=args.output_dir,
            models=tuple(args.models),
            language=args.language or None,
            prompt_file=args.prompt_file,
            glossary_file=args.glossary_file,
            repeat=max(1, args.repeat),
            word_timestamps=args.word_timestamps,
            verbose=True if args.verbose else False,
        )
    )
    print(f"Benchmark written to: {args.output_dir / 'benchmark.md'}")
    print(json.dumps({"results": summary.get("results", [])}, ensure_ascii=False, indent=2))
    return 0


def cmd_benchmark_gold(args: argparse.Namespace) -> int:
    condition_values = (
        (True, False) if args.condition_matrix else (args.condition_on_previous_text,)
    )
    report = run_gold_benchmark(
        GoldBenchmarkOptions(
            samples=tuple(args.samples),
            output_dir=args.output_dir,
            model=args.model,
            models=tuple(args.models or ()),
            language=args.language or None,
            prompt_file=args.prompt_file,
            glossary_file=args.glossary_file,
            terms_file=args.terms_file,
            condition_on_previous_text_values=condition_values,
            max_cer=args.max_cer,
            min_term_hit_rate=args.min_term_hit_rate,
            require_qa_pass=args.require_qa_pass,
            require_srt_pass=args.require_srt_pass,
            max_repeated_phrase_count=args.max_repeated_phrase_count,
            max_large_gap_count=args.max_large_gap_count,
        )
    )
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Gold benchmark written to: {report['output_dir']}")
    return 0 if report.get("success") else 1
