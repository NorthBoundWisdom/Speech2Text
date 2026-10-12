from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .agent_summary import AgentSummaryService, DocumentName
from .cloud.output_state import CloudOutputOptions
from .cloud.prepare import CloudPrepareOptions, prepare_cloud_input
from .cloud.review import write_cloud_glossary_review, write_cloud_polish_suggestions
from .cloud.summary_outputs import write_cloud_short_title, write_cloud_summary
from .config_v2 import AtotConfig, load_atot_config
from .languages import normalize_language_hint
from .library_store import (
    LibraryStore,
    library_episode_record_from_local_file,
    publish_work_documents_to_library,
    resolve_library_location,
)
from .paths import DEFAULT_GLOSSARY_FILE, DEFAULT_PROMPT_FILE, path_context
from .pipeline import TranscribeOptions, print_run_summary, run_transcription
from .qa import run_qa
from .qa.report import qa_to_markdown
from .redaction import redact_sensitive
from .repair import RepairOptions, run_repair
from .runtime_defaults import (
    DEFAULT_CLOUD_CHUNK_MINUTES,
    DEFAULT_COMPRESSION_RATIO_THRESHOLD,
    DEFAULT_LOGPROB_THRESHOLD,
    DEFAULT_NO_SPEECH_THRESHOLD,
    DEFAULT_SAMPLE_RATE,
)
from .runinfo import now_iso
from .subscriptions import (
    add_subscription,
    list_subscriptions,
    refresh_subscriptions,
    remove_subscription,
)
from .task_store import TaskRecord, TaskStore
from .utils import read_json
from .xiaoyuzhou import import_xiaoyuzhou_episode


EventSink = Callable[[dict[str, Any]], None]


class WorkflowService:
    """Synchronous application service for CLI workflows and task tracking.

    The service translates user-facing commands into pipeline, QA, repair,
    cloud, import, and subscription operations while recording task status
    events in ``TaskStore``.
    """

    def __init__(
        self,
        *,
        config: AtotConfig | None = None,
        task_store: TaskStore | None = None,
        event_sink: EventSink | None = None,
    ) -> None:
        self.config = config or load_atot_config(include_api_key=False)
        self.task_store = task_store or TaskStore()
        self.event_sink = event_sink

    def status(self, task_id: str | None = None) -> dict[str, Any]:
        return self.task_store.status(task_id)

    def run_transcribe(
        self,
        input_path: Path,
        *,
        output_dir: Path | None = None,
        job_dir: Path | None = None,
        name: str | None = None,
        backend: str | None = None,
        model: str | None = None,
        language: str | None = None,
        profile: str | None = None,
        prompt_file: Path | None = None,
        glossary_file: Path | None = None,
        rule_packs: list[str] | tuple[str, ...] | None = None,
        chunking: str | None = None,
        chunk_length: float | None = None,
        max_chunk_length: float | None = None,
        silence_threshold: float | None = None,
        min_silence: float | None = None,
        overlap: float | None = None,
        force: bool = False,
        local_only: bool | None = None,
        cloud_summary: bool | None = None,
        recording_json: Path | None = None,
    ) -> dict[str, Any]:
        task = self._create_task("transcribe", input_path.name, input_path=str(input_path))
        try:
            store = self._library_store()
            episode = self._ensure_library_episode_for_input(store, input_path)
            episode_id = str(episode["episode_id"])
            if job_dir is None and output_dir is None:
                job_dir = store.local_work_dir(episode_id)
            self._emit(task, "task.stage", stage="transcribe", detail="local transcription started")
            run = run_transcription(
                TranscribeOptions(
                    input_path=input_path,
                    output_dir=output_dir or path_context().output_dir,
                    job_dir=job_dir,
                    name=name,
                    backend=backend or self.config.local.backend,
                    recording_json=recording_json,
                    model=model or self.config.local.asr_model,
                    language=normalize_language_hint(language or self.config.local.language),
                    prompt_file=prompt_file or DEFAULT_PROMPT_FILE,
                    glossary_file=glossary_file or DEFAULT_GLOSSARY_FILE,
                    rule_packs=tuple(rule_packs or ()) or None,
                    chunk_length=chunk_length or self.config.workflow.chunk_length,
                    chunking=chunking or self.config.workflow.chunking,
                    max_chunk_length=max_chunk_length,
                    silence_threshold=silence_threshold,
                    min_silence=min_silence or 0.5,
                    overlap=overlap if overlap is not None else self.config.workflow.overlap,
                    local_only=self._local_only(local_only),
                    force_prepare=force,
                    force_chunks=force,
                    force_transcribe=force,
                    profile=profile or self.config.local.asr_profile,
                    progress_callback=self._pipeline_progress(task),
                )
            )
            run["library"] = publish_work_documents_to_library(
                store=store,
                episode_id=episode_id,
                work_dir=Path(str(run.get("job_dir") or job_dir or "")),
            )
            run["library_root"] = str(store.root)
            run["episode_id"] = episode_id
            run["material_dir"] = str(store.local_material_dir(episode_id))
            run["work_dir"] = str(Path(str(run.get("job_dir") or job_dir or "")))
            write_run_patch(Path(str(run.get("job_dir") or job_dir or "")), run)
            result: dict[str, Any] = {"task_id": task.task_id, "run": run}
            if self._should_run_cloud_summary(local_only=local_only, cloud_summary=cloud_summary):
                output = Path(str(run.get("job_dir") or ""))
                if not output:
                    raise RuntimeError(
                        "Transcription did not return an output directory for cloud summary."
                    )
                result["cloud_summary"] = self.run_cloud_summarize(
                    output, call_api=True, from_readable=True
                )
            self._emit(task, "task.output", output=print_run_summary(run), output_type="summary")
            self._emit(task, "task.finished", success=True, result=_compact_result(result))
            return result
        except Exception as exc:
            self._emit_failed(task, exc, stage="transcribe")
            raise

    def run_import_xiaoyuzhou(
        self,
        url: str,
        *,
        process_dir: Path | None = None,
        group_name: str | None = None,
        folder_name: str | None = None,
        audio_name: str | None = None,
        download: bool = True,
        force: bool = False,
        data_only: bool = False,
        transcribe: bool = True,
        backend: str | None = None,
        model: str | None = None,
        language: str | None = None,
        profile: str | None = None,
        local_only: bool | None = None,
    ) -> dict[str, Any]:
        task = self._create_task("import", url, url=url)
        try:
            self._emit(task, "task.stage", stage="import", detail="fetching episode metadata")
            result = import_xiaoyuzhou_episode(
                url,
                process_dir=process_dir if process_dir else path_context().process_dir,
                group_name=group_name,
                folder_name=folder_name,
                audio_name=audio_name,
                download=download,
                force=force,
            )
            payload = result.to_json()
            self._emit(task, "task.output", output=payload, output_type="import")
            if transcribe and not data_only:
                audio_path = Path(str(payload["audio_path"]))
                if not audio_path.exists():
                    raise FileNotFoundError(f"Audio file is missing after import: {audio_path}")
                payload["transcription"] = self.run_transcribe(
                    audio_path,
                    backend=backend,
                    model=model,
                    language=language,
                    profile=profile,
                    local_only=local_only,
                    force=force,
                )
            self._emit(task, "task.finished", success=True, result=_compact_result(payload))
            return {"task_id": task.task_id, **payload}
        except Exception as exc:
            self._emit_failed(task, exc, stage="import")
            raise

    def run_qa(
        self,
        output: Path,
        *,
        profile: str = "balanced",
        json_output: bool = False,
    ) -> dict[str, Any]:
        task = self._create_task("qa", output.name, output=str(output))
        try:
            self._emit(task, "task.stage", stage="qa", detail="running local quality gate")
            report = run_qa(output, profile=profile)
            self._emit(
                task,
                "task.output",
                output=report if json_output else qa_to_markdown(report),
                output_type="qa",
            )
            self._emit(
                task,
                "task.finished",
                success=bool(report.get("success")),
                result=_compact_result(report),
            )
            return {"task_id": task.task_id, **report}
        except Exception as exc:
            self._emit_failed(task, exc, stage="qa")
            raise

    def run_repair(
        self,
        output: Path,
        *,
        plan_only: bool = False,
        local_only: bool | None = None,
    ) -> dict[str, Any]:
        task = self._create_task("repair", output.name, output=str(output))
        try:
            self._emit(task, "task.stage", stage="repair", detail="building repair plan")
            result = run_repair(
                RepairOptions(
                    output_dir=output,
                    model=self.config.local.asr_model,
                    plan_only=plan_only,
                    local_only=self._local_only(local_only),
                )
            )
            self._emit(task, "task.finished", success=True, result=_compact_result(result))
            return {"task_id": task.task_id, **result}
        except Exception as exc:
            self._emit_failed(task, exc, stage="repair")
            raise

    def run_cloud_prepare(
        self,
        output: Path,
        *,
        redact: str | None = None,
        chunk_minutes: float = DEFAULT_CLOUD_CHUNK_MINUTES,
    ) -> dict[str, Any]:
        task = self._create_task("cloud", output.name, output=str(output), cloud_stage="prepare")
        try:
            self._emit(
                task, "task.stage", stage="cloud.prepare", detail="writing cloud input package"
            )
            result = prepare_cloud_input(
                CloudPrepareOptions(output_dir=output, redact=redact, chunk_minutes=chunk_minutes)
            )
            self._emit(task, "task.finished", success=True, result=_compact_result(result))
            return {"task_id": task.task_id, **result}
        except Exception as exc:
            self._emit_failed(task, exc, stage="cloud.prepare")
            raise

    def run_cloud_summarize(
        self,
        output: Path,
        *,
        call_api: bool = False,
        prompt_file: Path | None = None,
        mode: str = "auto",
        from_readable: bool = False,
        stream_summary: bool = False,
    ) -> dict[str, Any]:
        task = self._create_task("cloud", output.name, output=str(output), cloud_stage="summarize")
        try:
            self._emit(
                task, "task.stage", stage="cloud.summarize", detail="generating cloud summary"
            )
            summary_mode = "direct" if from_readable else mode
            result = write_cloud_summary(
                CloudOutputOptions(
                    output_dir=output,
                    call_api=call_api,
                    prompt_file=prompt_file,
                    summary_mode=summary_mode,
                    direct_readable=summary_mode == "direct",
                    stream_summary=stream_summary,
                )
            )
            _publish_work_dir_to_library(self._library_store(), output)
            self._emit(task, "task.finished", success=True, result=_compact_result(result))
            return {"task_id": task.task_id, **result}
        except Exception as exc:
            self._emit_failed(task, exc, stage="cloud.summarize")
            raise

    def run_cloud_title(
        self,
        output: Path,
        *,
        call_api: bool = False,
        prompt_file: Path | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        task = self._create_task("cloud", output.name, output=str(output), cloud_stage="title")
        try:
            self._emit(task, "task.stage", stage="cloud.title", detail="generating short title")
            result = write_cloud_short_title(
                CloudOutputOptions(output_dir=output, call_api=call_api, prompt_file=prompt_file),
                force=force,
            )
            self._emit(task, "task.finished", success=True, result=_compact_result(result))
            return {"task_id": task.task_id, **result}
        except Exception as exc:
            self._emit_failed(task, exc, stage="cloud.title")
            raise

    def run_cloud_glossary_review(
        self,
        output: Path,
        *,
        call_api: bool = False,
        prompt_file: Path | None = None,
    ) -> dict[str, Any]:
        task = self._create_task(
            "cloud", output.name, output=str(output), cloud_stage="glossary_review"
        )
        try:
            self._emit(
                task,
                "task.stage",
                stage="cloud.glossary_review",
                detail="generating glossary review",
            )
            result = write_cloud_glossary_review(
                CloudOutputOptions(output_dir=output, call_api=call_api, prompt_file=prompt_file)
            )
            self._emit(task, "task.finished", success=True, result=_compact_result(result))
            return {"task_id": task.task_id, **result}
        except Exception as exc:
            self._emit_failed(task, exc, stage="cloud.glossary_review")
            raise

    def run_cloud_polish(
        self,
        output: Path,
        *,
        call_api: bool = False,
        prompt_file: Path | None = None,
    ) -> dict[str, Any]:
        task = self._create_task("cloud", output.name, output=str(output), cloud_stage="polish")
        try:
            self._emit(
                task,
                "task.stage",
                stage="cloud.polish",
                detail="generating transcript polish suggestions",
            )
            result = write_cloud_polish_suggestions(
                CloudOutputOptions(output_dir=output, call_api=call_api, prompt_file=prompt_file)
            )
            self._emit(task, "task.finished", success=True, result=_compact_result(result))
            return {"task_id": task.task_id, **result}
        except Exception as exc:
            self._emit_failed(task, exc, stage="cloud.polish")
            raise

    def run_srt(
        self,
        inputs: list[Path],
        *,
        languages: list[str] | None = None,
        backend: str | None = None,
        output: Path | None = None,
        output_dir: Path | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        from .commands.srt import SrtExportOptions, run_srt_export

        args = SrtExportOptions(
            inputs=inputs,
            output=output,
            output_dir=output_dir,
            overwrite=overwrite,
            language=languages or ["zh"],
            backend=backend or self.config.local.backend,
            recording_json=None,
            sample_rate=DEFAULT_SAMPLE_RATE,
            force_prepare=False,
            force_chunks=False,
            force=False,
            chunking=self.config.workflow.chunking,
            chunk_length=self.config.workflow.chunk_length,
            max_chunk_length=None,
            silence_threshold=None,
            min_silence=0.5,
            local_only=True,
            temperature=0.0,
            no_speech_threshold=DEFAULT_NO_SPEECH_THRESHOLD,
            logprob_threshold=DEFAULT_LOGPROB_THRESHOLD,
            compression_ratio_threshold=DEFAULT_COMPRESSION_RATIO_THRESHOLD,
            hallucination_silence_threshold=None,
            condition_on_previous_text=True,
            prompt_file=DEFAULT_PROMPT_FILE,
            glossary_file=DEFAULT_GLOSSARY_FILE,
            rule_pack=None,
            overlap=self.config.workflow.overlap,
            word_timestamps=False,
            verbose=False,
            json_output=True,
        )
        task = self._create_task("srt", ",".join(str(item) for item in inputs))
        try:
            payload = run_srt_export(args)
            self._emit(task, "task.output", output=payload, output_type="srt")
            self._emit(
                task,
                "task.finished",
                success=bool(payload.get("success")),
                result=_compact_result(payload),
            )
            if not payload.get("success"):
                raise RuntimeError("srt failed")
            return {"task_id": task.task_id, **payload}
        except Exception as exc:
            self._emit(task, "task.failed", error=str(exc), error_type=type(exc).__name__)
            raise

    def run_subscriptions(
        self,
        command: str,
        *,
        url: str | None = None,
        group_name: str = "Default",
        limit: int | None = 10,
        subscription_id: str | None = None,
        refresh_all: bool = False,
    ) -> dict[str, Any]:
        task = self._create_task("subscriptions", command)
        store = self._library_store()
        common: dict[str, Any] = {"library_root": store.root}
        stage = f"subscriptions.{command}"
        try:
            self._emit(task, "task.stage", stage=stage, detail=f"running subscriptions {command}")
            if command == "add":
                if not url:
                    raise ValueError("Missing subscription URL.")
                payload = add_subscription(url, group_name=group_name, limit=limit, **common)
            elif command == "list":
                payload = list_subscriptions(**common)
            elif command == "refresh":
                payload = refresh_subscriptions(
                    subscription_id=subscription_id,
                    refresh_all=refresh_all,
                    limit=limit,
                    **common,
                )
            elif command == "remove":
                if not subscription_id:
                    raise ValueError("Missing subscription id.")
                payload = remove_subscription(
                    subscription_id,
                    **common,
                )
            else:
                raise ValueError(f"Unknown subscriptions command: {command}")
            self._emit(task, "task.output", output=payload, output_type="subscriptions")
            self._emit(task, "task.finished", success=True, result=_compact_result(payload))
            return {"task_id": task.task_id, **payload}
        except Exception as exc:
            self._emit_failed(task, exc, stage=stage)
            raise

    def run_library_status(self) -> dict[str, Any]:
        task = self._create_task("library", "status")
        try:
            payload = self._library_store().status()
            self._emit(task, "task.finished", success=True, result=payload)
            return {"task_id": task.task_id, **payload}
        except Exception as exc:
            self._emit(task, "task.failed", error=str(exc), error_type=type(exc).__name__)
            raise

    def run_library_list_episodes(
        self, *, query: str = "", needs_summary: bool = False, offset: int = 0, limit: int = 20
    ) -> dict[str, Any]:
        return AgentSummaryService(self._library_store()).list_episodes(
            query=query, needs_summary=needs_summary, offset=offset, limit=limit
        )

    def run_library_read_episode(self, episode_id: str) -> dict[str, Any]:
        return AgentSummaryService(self._library_store()).get_episode(episode_id)

    def run_library_read_document(
        self,
        episode_id: str,
        document: DocumentName = "transcript",
        *,
        offset: int = 0,
        max_chars: int = 8000,
        expected_sha256: str | None = None,
    ) -> dict[str, Any]:
        return AgentSummaryService(self._library_store()).read_document(
            episode_id,
            document,
            offset=offset,
            max_chars=max_chars,
            expected_sha256=expected_sha256,
        )

    def run_library_write_summary(
        self,
        episode_id: str,
        markdown: str,
        *,
        transcript_sha256: str,
        summary_sha256: str,
        overwrite: bool = False,
        generator: str = "external-agent",
    ) -> dict[str, Any]:
        task = self._create_task("agent-summary", "library.summary.write", episode_id=episode_id)
        try:
            result = AgentSummaryService(self._library_store()).write_summary(
                episode_id,
                markdown,
                transcript_sha256=transcript_sha256,
                summary_sha256=summary_sha256,
                overwrite=overwrite,
                generator=generator,
            )
            self._emit(task, "task.finished", success=True, result=result)
            return {"task_id": task.task_id, **result}
        except Exception as exc:
            self._emit_failed(task, exc, stage="library.summary.write")
            raise

    def run_library_delete_episode(self, episode_id: str) -> dict[str, Any]:
        task = self._create_task("library", "episode.delete", episode_id=episode_id)
        try:
            payload = self._library_store().delete_episode(episode_id)
            self._emit(task, "task.finished", success=True, result=payload)
            return {"task_id": task.task_id, **payload}
        except Exception as exc:
            self._emit(task, "task.failed", error=str(exc), error_type=type(exc).__name__)
            raise

    def _library_store(self) -> LibraryStore:
        location = resolve_library_location(
            storage=self.config.library.storage,
            icloud_root=self.config.library.icloud_root,
            local_root=self.config.library.local_root,
        )
        return LibraryStore(location.root)

    def _ensure_library_episode_for_input(
        self, store: LibraryStore, input_path: Path
    ) -> dict[str, Any]:
        input_path = input_path.expanduser().resolve()
        for episode in store.load_episodes(include_deleted=True):
            episode_id = str(episode.get("episode_id") or "")
            if episode_id and _path_is_under(input_path, store.local_material_dir(episode_id)):
                return episode
        record = library_episode_record_from_local_file(input_path)
        persisted, _ = store.upsert_episode(record)
        return persisted

    def _create_task(self, kind: str, title: str, **fields: Any) -> TaskRecord:
        return self.task_store.create_task(kind, title, started_at=now_iso(), **fields)

    def _emit(self, task: TaskRecord, event: str, **fields: Any) -> dict[str, Any]:
        payload = self.task_store.append(task, event, **fields)
        if self.event_sink is not None:
            self.event_sink(redact_sensitive(payload))
        return payload

    def _emit_failed(self, task: TaskRecord, exc: Exception, *, stage: str) -> dict[str, Any]:
        return self._emit(
            task,
            "task.failed",
            stage=stage,
            detail=f"{stage} failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )

    def _pipeline_progress(self, task: TaskRecord) -> Callable[[dict[str, Any]], None]:
        def emit(event: dict[str, Any]) -> None:
            if event.get("event") == "stage":
                self._emit(task, "task.stage", stage=event.get("stage"), detail=event)
            elif event.get("event") == "chunk":
                total = int(event.get("total_chunks") or 0)
                chunk = int(event.get("chunk") or 0) + 1
                self._emit(
                    task,
                    "task.progress",
                    stage="transcribe",
                    completed=chunk if event.get("status") != "started" else max(0, chunk - 1),
                    total=total,
                    detail=event,
                )

        return emit

    def _local_only(self, value: bool | None) -> bool:
        return self.config.workflow.local_only if value is None else value

    def _should_run_cloud_summary(
        self, *, local_only: bool | None, cloud_summary: bool | None
    ) -> bool:
        if self._local_only(local_only):
            return False
        if cloud_summary is not None:
            return cloud_summary
        return self.config.workflow.default_cloud_summary


def _compact_result(payload: Any) -> Any:
    if isinstance(payload, dict):
        compact: dict[str, Any] = {}
        for key, value in payload.items():
            if key in {"segments", "chunks", "raw", "corrected"}:
                compact[key] = f"<{len(value)} items>" if isinstance(value, list) else "<omitted>"
            else:
                compact[key] = _compact_result(value)
        return compact
    if isinstance(payload, list) and len(payload) > 20:
        return [*_compact_result(payload[:20]), f"<{len(payload) - 20} more>"]
    return payload


def _publish_work_dir_to_library(store: LibraryStore, work_dir: Path) -> None:
    run_path = work_dir / "run.json"
    if not run_path.is_file():
        return
    try:
        run = read_json(run_path)
    except Exception:
        return
    if not isinstance(run, dict):
        return
    episode_id = str(run.get("episode_id") or "")
    if not episode_id:
        for episode in store.load_episodes(include_deleted=True):
            candidate = str(episode.get("episode_id") or "")
            if candidate and _path_is_under(work_dir, store.local_work_dir(candidate)):
                episode_id = candidate
                break
    if not episode_id:
        return
    run["library"] = publish_work_documents_to_library(
        store=store, episode_id=episode_id, work_dir=work_dir
    )
    run["library_root"] = str(store.root)
    run["episode_id"] = episode_id
    write_run_patch(work_dir, run)


def write_run_patch(work_dir: Path, run: dict[str, Any]) -> None:
    try:
        from .writer import write_run_info

        write_run_info(work_dir, run)
    except Exception:
        return


def _path_is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False
