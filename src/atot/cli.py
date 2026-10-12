from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any

import click
from rich.console import Console
import typer

from .commands.diagnostics import cmd_doctor, cmd_models
from .config_v2 import (
    config_as_dict,
    load_atot_config,
    parse_toml_value,
    read_config_value,
    set_config_value,
)
from .redaction import redact_sensitive
from .runtime_defaults import DEFAULT_CLOUD_CHUNK_MINUTES, DEFAULT_SERVICE_HTTP_PORT
from .service import serve_http, serve_stdio
from .workflow_service import WorkflowService


console = Console()

app = typer.Typer(
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)
exec_app = typer.Typer(add_completion=False, help="Run Audio2Text non-interactively.")
cloud_app = typer.Typer(add_completion=False, help="Run text-only cloud stages.")
config_app = typer.Typer(add_completion=False, help="Read and edit config.toml.")
subscriptions_app = typer.Typer(add_completion=False, help="Manage podcast subscriptions.")
library_app = typer.Typer(add_completion=False, help="Manage the unified Audio2Text Library.")
library_episode_app = typer.Typer(
    add_completion=False, help="Manage episodes in the unified Audio2Text library."
)


def _config_overrides(ctx: typer.Context) -> list[str]:
    obj = ctx.obj if isinstance(ctx.obj, dict) else {}
    return list(obj.get("config_overrides") or [])


def _service(ctx: typer.Context, *, watch: bool = False) -> WorkflowService:
    def sink(event: dict[str, Any]) -> None:
        # stdout protocol for --watch consumers.
        print(json.dumps(redact_sensitive(event), ensure_ascii=False), flush=True)

    return WorkflowService(
        config=load_atot_config(overrides=_config_overrides(ctx), include_api_key=False),
        event_sink=sink if watch else None,
    )


def _print(payload: Any, *, json_output: bool) -> None:
    if json_output:
        # stdout protocol for --json consumers.
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        console.print(payload)


@app.callback()
def root(
    ctx: typer.Context,
    config_overrides: list[str] | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Override config with a TOML value, e.g. -c local.asr_model='large-v3-turbo'.",
    ),
) -> None:
    ctx.obj = {"config_overrides": config_overrides or []}
    if ctx.invoked_subcommand is None:
        from .tui import run_tui

        raise typer.Exit(run_tui(None, config_overrides=config_overrides or []))


@exec_app.command("transcribe")
def exec_transcribe(
    ctx: typer.Context,
    input: Path = typer.Argument(..., exists=True, readable=True, help="Input audio/video file."),
    output_dir: Path | None = typer.Option(None, "--output-dir", help="Work/output root."),
    job_dir: Path | None = typer.Option(None, "--job-dir", help="Exact output job directory."),
    name: str | None = typer.Option(None, "--name", help="Output folder name."),
    backend: str | None = typer.Option(None, "--backend", help="ASR backend."),
    model: str | None = typer.Option(None, "--model", help="Model alias."),
    language: str | None = typer.Option(None, "--language", help="Source language hint."),
    profile: str | None = typer.Option(None, "--profile", help="Decode profile."),
    prompt_file: Path | None = typer.Option(None, "--prompt-file", help="Prompt/context file."),
    glossary_file: Path | None = typer.Option(None, "--glossary-file", help="Glossary JSON file."),
    rule_pack: list[str] | None = typer.Option(
        None, "--rule-pack", help="Reusable rule pack name. Repeatable."
    ),
    chunking: str | None = typer.Option(None, "--chunking", help="auto, fixed, or smart."),
    chunk_length: float | None = typer.Option(
        None, "--chunk-length", help="Target chunk length in seconds."
    ),
    max_chunk_length: float | None = typer.Option(
        None, "--max-chunk-length", help="Smart chunk maximum length."
    ),
    silence_threshold: float | None = typer.Option(
        None, "--silence-threshold", help="Smart chunk silence threshold."
    ),
    min_silence: float | None = typer.Option(
        None, "--min-silence", help="Smart chunk minimum silence duration."
    ),
    overlap: float | None = typer.Option(None, "--overlap", help="Chunk overlap in seconds."),
    force: bool = typer.Option(False, "--force", help="Rebuild existing transcribe artifacts."),
    local_only: bool = typer.Option(False, "--local-only", help="Skip cloud summary stages."),
    cloud_summary: bool = typer.Option(
        False, "--cloud-summary", help="Run explicit cloud summary after local QA."
    ),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
    watch: bool = typer.Option(
        False, "--watch", help="Stream task events as JSON lines while running."
    ),
) -> None:
    result = _service(ctx, watch=watch).run_transcribe(
        input,
        output_dir=output_dir,
        job_dir=job_dir,
        name=name,
        backend=backend,
        model=model,
        language=language,
        profile=profile,
        prompt_file=prompt_file,
        glossary_file=glossary_file,
        rule_packs=rule_pack,
        chunking=chunking,
        chunk_length=chunk_length,
        max_chunk_length=max_chunk_length,
        silence_threshold=silence_threshold,
        min_silence=min_silence,
        overlap=overlap,
        force=force,
        local_only=local_only,
        cloud_summary=cloud_summary,
    )
    _print(result, json_output=json_output)


@exec_app.command("import")
def exec_import(
    ctx: typer.Context,
    url: str = typer.Argument(..., help="Xiaoyuzhou episode URL."),
    process_dir: Path | None = typer.Option(None, "--process-dir", help="Process cache directory."),
    group_name: str | None = typer.Option(None, "--group-name", help="App group label."),
    folder_name: str | None = typer.Option(
        None, "--folder-name", help="Override episode folder name."
    ),
    audio_name: str | None = typer.Option(None, "--audio-name", help="Override audio filename."),
    backend: str | None = typer.Option(None, "--backend", help="ASR backend."),
    model: str | None = typer.Option(None, "--model", help="Model alias."),
    language: str | None = typer.Option(None, "--language", help="Source language hint."),
    profile: str | None = typer.Option(None, "--profile", help="Decode profile."),
    no_download: bool = typer.Option(False, "--no-download", help="Skip audio download."),
    force: bool = typer.Option(False, "--force", help="Redownload and replace imported audio."),
    data_only: bool = typer.Option(False, "--data-only", help="Only write metadata/audio files."),
    transcribe: bool = typer.Option(
        True, "--transcribe/--no-transcribe", help="Run local transcription after import."
    ),
    local_only: bool = typer.Option(False, "--local-only", help="Skip cloud summary stages."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
    watch: bool = typer.Option(
        False, "--watch", help="Stream task events as JSON lines while running."
    ),
) -> None:
    result = _service(ctx, watch=watch).run_import_xiaoyuzhou(
        url,
        process_dir=process_dir,
        group_name=group_name,
        folder_name=folder_name,
        audio_name=audio_name,
        download=not no_download,
        force=force,
        data_only=data_only,
        transcribe=transcribe,
        backend=backend,
        model=model,
        language=language,
        profile=profile,
        local_only=local_only,
    )
    _print(result, json_output=json_output)


@exec_app.command("qa")
def exec_qa(
    ctx: typer.Context,
    output: Path = typer.Argument(..., help="Output directory."),
    profile: str = typer.Option("balanced", "--profile", help="QA profile."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    result = _service(ctx).run_qa(output, profile=profile, json_output=json_output)
    _print(result, json_output=json_output)
    if not result.get("success"):
        raise typer.Exit(1)


@exec_app.command("repair")
def exec_repair(
    ctx: typer.Context,
    output: Path = typer.Argument(..., help="Output directory."),
    plan_only: bool = typer.Option(False, "--plan-only", help="Only write the repair plan."),
    local_only: bool = typer.Option(True, "--local-only/--allow-cloud", help="Keep repair local."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    result = _service(ctx).run_repair(output, plan_only=plan_only, local_only=local_only)
    _print(result, json_output=json_output)


@exec_app.command("srt")
def exec_srt(
    ctx: typer.Context,
    inputs: list[Path] = typer.Argument(..., help="Input media file(s)."),
    language: list[str] | None = typer.Option(
        None, "--language", help="Source language hint. Repeatable."
    ),
    backend: str | None = typer.Option(None, "--backend", help="ASR backend."),
    output: Path | None = typer.Option(None, "--output", help="Exact SRT output path."),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", help="Directory for generated SRT files."
    ),
    overwrite: bool = typer.Option(False, "--overwrite", help="Replace existing SRT files."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
    watch: bool = typer.Option(
        False, "--watch", help="Stream task events as JSON lines while running."
    ),
) -> None:
    result = _service(ctx, watch=watch).run_srt(
        inputs,
        languages=language,
        backend=backend,
        output=output,
        output_dir=output_dir,
        overwrite=overwrite,
    )
    _print(result, json_output=json_output)
    if not result.get("success"):
        raise typer.Exit(1)


@cloud_app.command("prepare")
def exec_cloud_prepare(
    ctx: typer.Context,
    output: Path = typer.Argument(..., help="Output directory."),
    redact: str | None = typer.Option(None, "--redact", help="Redaction mode."),
    chunk_minutes: float = typer.Option(
        DEFAULT_CLOUD_CHUNK_MINUTES, "--chunk-minutes", help="Cloud input chunk size."
    ),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    result = _service(ctx).run_cloud_prepare(output, redact=redact, chunk_minutes=chunk_minutes)
    _print(result, json_output=json_output)


@cloud_app.command("summarize")
def exec_cloud_summarize(
    ctx: typer.Context,
    output: Path = typer.Argument(..., help="Output directory."),
    call_api: bool = typer.Option(False, "--call-api", help="Call configured cloud model."),
    prompt_file: Path | None = typer.Option(
        None, "--prompt-file", help="Override prompt template."
    ),
    mode: str = typer.Option("auto", "--mode", help="auto, chunked, or direct."),
    from_readable: bool = typer.Option(
        False, "--from-readable", help="Summarize transcript.readable.md directly."
    ),
    stream_summary: bool = typer.Option(
        False, "--stream-summary", help="Stream summary to cloud/summary.md."
    ),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    result = _service(ctx).run_cloud_summarize(
        output,
        call_api=call_api,
        prompt_file=prompt_file,
        mode=mode,
        from_readable=from_readable,
        stream_summary=stream_summary,
    )
    _print(result, json_output=json_output)


@cloud_app.command("title")
def exec_cloud_title(
    ctx: typer.Context,
    output: Path = typer.Argument(..., help="Output directory."),
    call_api: bool = typer.Option(False, "--call-api", help="Call configured cloud model."),
    prompt_file: Path | None = typer.Option(
        None, "--prompt-file", help="Override prompt template."
    ),
    force: bool = typer.Option(False, "--force", help="Regenerate existing title."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    result = _service(ctx).run_cloud_title(
        output, call_api=call_api, prompt_file=prompt_file, force=force
    )
    _print(result, json_output=json_output)


@cloud_app.command("glossary-review")
def exec_cloud_glossary_review(
    ctx: typer.Context,
    output: Path = typer.Argument(..., help="Output directory."),
    call_api: bool = typer.Option(False, "--call-api", help="Call configured cloud model."),
    prompt_file: Path | None = typer.Option(
        None, "--prompt-file", help="Override prompt template."
    ),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    result = _service(ctx).run_cloud_glossary_review(
        output, call_api=call_api, prompt_file=prompt_file
    )
    _print(result, json_output=json_output)


@cloud_app.command("polish")
def exec_cloud_polish(
    ctx: typer.Context,
    output: Path = typer.Argument(..., help="Output directory."),
    call_api: bool = typer.Option(False, "--call-api", help="Call configured cloud model."),
    prompt_file: Path | None = typer.Option(
        None, "--prompt-file", help="Override prompt template."
    ),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    result = _service(ctx).run_cloud_polish(output, call_api=call_api, prompt_file=prompt_file)
    _print(result, json_output=json_output)


@subscriptions_app.command("add")
def subscriptions_add(
    ctx: typer.Context,
    url: str,
    group_name: str = typer.Option("Default", "--group-name"),
    limit: int = typer.Option(10, "--limit"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _print(
        _service(ctx).run_subscriptions(
            "add",
            url=url,
            group_name=group_name,
            limit=limit,
        ),
        json_output=json_output,
    )


@subscriptions_app.command("list")
def subscriptions_list(
    ctx: typer.Context, json_output: bool = typer.Option(False, "--json")
) -> None:
    _print(_service(ctx).run_subscriptions("list"), json_output=json_output)


@subscriptions_app.command("refresh")
def subscriptions_refresh(
    ctx: typer.Context,
    refresh_all: bool = typer.Option(False, "--all"),
    id: str | None = typer.Option(None, "--id"),
    limit: int = typer.Option(10, "--limit"),
    full_history: bool = typer.Option(
        False, "--full-history", help="Import every episode currently exposed by the feed."
    ),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _print(
        _service(ctx).run_subscriptions(
            "refresh",
            refresh_all=refresh_all,
            subscription_id=id,
            limit=None if full_history else limit,
        ),
        json_output=json_output,
    )


@subscriptions_app.command("remove")
def subscriptions_remove(
    ctx: typer.Context, id: str, json_output: bool = typer.Option(False, "--json")
) -> None:
    _print(_service(ctx).run_subscriptions("remove", subscription_id=id), json_output=json_output)


@library_app.command("status")
def library_status(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    _print(_service(ctx).run_library_status(), json_output=json_output)


@library_episode_app.command("delete")
def library_episode_delete(
    ctx: typer.Context,
    episode_id: str = typer.Argument(...),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    _print(_service(ctx).run_library_delete_episode(episode_id), json_output=json_output)


@app.command("resume")
def resume(
    ctx: typer.Context,
    session: str | None = typer.Argument(None, help="Task/session id."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    _print(_service(ctx).status(session), json_output=json_output)


@app.command("status")
def status(
    ctx: typer.Context,
    task_id: str | None = typer.Option(None, "--task-id", help="Task/session id."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    _print(_service(ctx).status(task_id), json_output=json_output)


@app.command("doctor")
def doctor(
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    code = cmd_doctor(argparse.Namespace(json_output=json_output, local_only=True))
    if code:
        raise typer.Exit(code)


@app.command("models")
def models(
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    raise typer.Exit(cmd_models(argparse.Namespace(json_output=json_output, local_only=True)))


@config_app.command("list")
def config_list(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    _print(
        config_as_dict(load_atot_config(overrides=_config_overrides(ctx))), json_output=json_output
    )


@config_app.command("get")
def config_get(
    key: str = typer.Argument(...), json_output: bool = typer.Option(False, "--json")
) -> None:
    payload = {"key": key, "value": read_config_value(key)}
    _print(payload, json_output=json_output)


@config_app.command("set")
def config_set(
    key: str = typer.Argument(...), value: str | None = typer.Argument(None),
    stdin: bool = typer.Option(False, "--stdin", help="Read a cloud API key from stdin without shell history."),
) -> None:
    if stdin:
        if key != "cloud.api_key" or value is not None:
            raise typer.BadParameter("--stdin requires cloud.api_key and no value argument.")
        parsed = sys.stdin.read().rstrip("\r\n")
    elif value is not None:
        try:
            parsed = parse_toml_value(value)
        except ValueError:
            raise typer.BadParameter("Invalid config value.") from None
    else:
        raise typer.BadParameter("Provide a value or use --stdin for cloud.api_key.")
    path = set_config_value(key, parsed)
    console.print({"path": str(path), "key": key})


@config_app.command("path")
def config_path_cmd(ctx: typer.Context) -> None:
    console.print(str(load_atot_config(overrides=_config_overrides(ctx), include_api_key=False).path))


@config_app.command("edit")
def config_edit(ctx: typer.Context) -> None:
    path = load_atot_config(overrides=_config_overrides(ctx), include_api_key=False).path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    editor_command = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if not editor_command:
        raise typer.BadParameter("Set EDITOR or VISUAL to use `atot config edit`.")
    raise typer.Exit(subprocess.call([*shlex.split(editor_command), str(path)]))


@app.command("mcp")
def mcp_server(ctx: typer.Context) -> None:
    """Serve the local agent summary tools over MCP stdio. No API Key is required."""
    from .mcp_server import serve_mcp

    serve_mcp(config_overrides=tuple(_config_overrides(ctx)))


@app.command("serve")
def serve(
    stdio: bool = typer.Option(False, "--stdio", help="Serve JSON requests over stdin/stdout."),
    http: bool = typer.Option(False, "--http", help="Serve JSON requests over HTTP."),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(DEFAULT_SERVICE_HTTP_PORT, "--port"),
    request_json: str | None = typer.Option(
        None, "--request-json", help="Run one service request JSON and exit."
    ),
    unwrap_result: bool = typer.Option(
        False, "--unwrap-result", help="With --request-json, print only result."
    ),
) -> None:
    if http:
        serve_http(host, port)
        return
    if stdio or request_json is not None:
        raise typer.Exit(serve_stdio(request_json=request_json, unwrap_result=unwrap_result))
    raise typer.BadParameter("Choose --stdio or --http.")


exec_app.add_typer(cloud_app, name="cloud")
exec_app.add_typer(subscriptions_app, name="subscriptions")
library_app.add_typer(library_episode_app, name="episode")
exec_app.add_typer(library_app, name="library")
app.add_typer(exec_app, name="exec")
app.add_typer(config_app, name="config")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    interactive_argv, prompt_overrides = _strip_leading_config_overrides(argv)
    if _looks_like_interactive_prompt(interactive_argv):
        from .tui import run_tui

        return run_tui(" ".join(interactive_argv), config_overrides=prompt_overrides)
    command = typer.main.get_command(app)
    try:
        command.main(args=argv, prog_name="atot", standalone_mode=False)
        return 0
    except click.ClickException as exc:
        exc.show()
        return exc.exit_code
    except click.Abort:
        return 1
    except typer.Exit as exc:
        return int(exc.exit_code or 0)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def _strip_leading_config_overrides(argv: list[str]) -> tuple[list[str], list[str]]:
    remaining: list[str] = []
    overrides: list[str] = []
    index = 0
    while index < len(argv):
        item = argv[index]
        if item == "--":
            remaining.extend(argv[index + 1 :])
            break
        if item in {"-c", "--config"}:
            if index + 1 >= len(argv):
                remaining.extend(argv[index:])
                break
            overrides.append(argv[index + 1])
            index += 2
            continue
        if item.startswith("--config="):
            overrides.append(item.split("=", 1)[1])
            index += 1
            continue
        if item.startswith("-c") and item != "-c":
            overrides.append(item[2:])
            index += 1
            continue
        remaining.extend(argv[index:])
        break
    return remaining, overrides


def _looks_like_interactive_prompt(argv: list[str]) -> bool:
    if not argv:
        return False
    first = argv[0]
    if first.startswith("-"):
        return False
    known_commands = {"exec", "resume", "status", "doctor", "models", "config", "serve", "mcp", "library"}
    removed_v1_commands = {
        "transcribe",
        "prepare",
        "import-local",
        "srt",
        "benchmark",
        "benchmark-gold",
        "import-xiaoyuzhou",
        "subscriptions",
        "backends",
        "validate-backend-promotion",
        "summary-local",
        "search",
        "qa",
        "validate",
        "cleanup",
        "postprocess",
        "repair",
        "diarize",
        "ui",
        "batch",
        "cloud",
        "sync",
    }
    return first not in known_commands | removed_v1_commands


if __name__ == "__main__":
    raise SystemExit(main())
