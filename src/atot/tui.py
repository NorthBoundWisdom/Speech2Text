from __future__ import annotations

from dataclasses import dataclass
import shlex
from pathlib import Path
from typing import Any

from .config_v2 import load_atot_config
from .workflow_service import WorkflowService


SLASH_COMMANDS = {
    "import",
    "transcribe",
    "queue",
    "resume",
    "config",
    "models",
    "doctor",
    "cloud",
    "srt",
    "help",
    "quit",
}


@dataclass(frozen=True)
class SlashCommand:
    name: str
    args: list[str]
    raw: str


def parse_slash_command(text: str) -> SlashCommand:
    raw = text.strip()
    if not raw.startswith("/"):
        raise ValueError("Slash command must start with '/'.")
    parts = shlex.split(raw[1:])
    if not parts:
        raise ValueError("Empty slash command.")
    name = parts[0]
    if name not in SLASH_COMMANDS:
        raise ValueError(f"Unknown slash command: /{name}")
    return SlashCommand(name=name, args=parts[1:], raw=raw)


def slash_help() -> str:
    return "\n".join(
        [
            "/import <xiaoyuzhou-url>",
            "/transcribe <audio-path>",
            "/queue",
            "/resume [task-id]",
            "/config [key]",
            "/models",
            "/doctor",
            "/cloud prepare|summarize|title <output-dir>",
            "/srt <media-path>",
            "/help",
            "/quit",
        ]
    )


def run_tui(prompt: str | None = None, *, config_overrides: list[str] | None = None) -> int:
    try:
        from textual.app import App, ComposeResult
        from textual.containers import Horizontal, Vertical
        from textual.widgets import Footer, Header, Input, ListItem, ListView, RichLog, Static
    except ImportError as exc:  # pragma: no cover - depends on optional runtime import
        raise RuntimeError(
            "Textual is required for the interactive TUI. Run setup_local_app.py again."
        ) from exc

    class Audio2TextTui(App[None]):
        CSS = """
        Screen { layout: vertical; }
        #body { height: 1fr; }
        #library { width: 26; border: solid $accent; }
        #timeline { width: 1fr; border: solid $accent; }
        #details { width: 1fr; border: solid $accent; }
        #composer { dock: bottom; }
        Static.title { text-style: bold; padding: 0 1; }
        RichLog { padding: 0 1; }
        """
        BINDINGS = [
            ("ctrl+c", "quit", "Quit"),
            ("ctrl+d", "quit", "Quit"),
        ]

        def __init__(self, initial_prompt: str | None) -> None:
            super().__init__()
            self.initial_prompt = initial_prompt
            self.service = WorkflowService(
                config=load_atot_config(overrides=config_overrides or [], include_api_key=False),
                event_sink=self.on_task_event,
            )

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Horizontal(id="body"):
                with Vertical(id="library"):
                    yield Static("资料库 / Sessions", classes="title")
                    yield ListView(id="sessions")
                with Vertical(id="timeline"):
                    yield Static("工作流", classes="title")
                    yield RichLog(id="timeline_log", wrap=True, markup=True)
                with Vertical(id="details"):
                    yield Static("详情", classes="title")
                    yield RichLog(id="detail_log", wrap=True, markup=True)
            yield Input(placeholder="/transcribe path/to/audio.m4a  或 /help", id="composer")
            yield Footer()

        def on_mount(self) -> None:
            self.query_one("#timeline_log", RichLog).write(
                "Audio2Text 交互模式已启动。输入 /help 查看命令。"
            )
            self.refresh_sessions()
            if self.initial_prompt:
                self.handle_text(self.initial_prompt)

        def on_input_submitted(self, event: Input.Submitted) -> None:
            value = event.value.strip()
            event.input.value = ""
            if value:
                self.handle_text(value)

        def handle_text(self, text: str) -> None:
            timeline = self.query_one("#timeline_log", RichLog)
            details = self.query_one("#detail_log", RichLog)
            if not text.startswith("/"):
                details.write(text)
                return
            try:
                command = parse_slash_command(text)
                if command.name == "quit":
                    self.exit()
                    return
                if command.name == "help":
                    details.write(slash_help())
                    return
                result = self.run_command(command)
                details.write(result)
                self.refresh_sessions()
            except Exception as exc:
                timeline.write(f"[red]错误:[/] {exc}")

        def run_command(self, command: SlashCommand) -> Any:
            if command.name == "transcribe":
                if not command.args:
                    raise ValueError("/transcribe requires an audio path.")
                return self.service.run_transcribe(Path(command.args[0]), local_only=True)
            if command.name == "import":
                if not command.args:
                    raise ValueError("/import requires a Xiaoyuzhou URL.")
                return self.service.run_import_xiaoyuzhou(
                    command.args[0], data_only=True, transcribe=False
                )
            if command.name == "resume":
                return self.service.status(command.args[0] if command.args else None)
            if command.name == "queue":
                return self.service.status()
            if command.name == "config":
                config = load_atot_config(overrides=config_overrides or [], include_api_key=False)
                if command.args:
                    current: Any = config.raw
                    for part in command.args[0].split("."):
                        current = current.get(part) if isinstance(current, dict) else None
                    return {command.args[0]: current}
                return {
                    "path": str(config.path),
                    "local": vars(config.local),
                    "workflow": vars(config.workflow),
                }
            if command.name == "models":
                from .models import describe_models

                return describe_models()
            if command.name == "doctor":
                from .commands.diagnostics import cmd_doctor
                import argparse

                return_code = cmd_doctor(argparse.Namespace(json_output=True, local_only=True))
                return {"exit_code": return_code}
            if command.name == "cloud":
                if len(command.args) < 2:
                    raise ValueError(
                        "/cloud requires prepare|summarize|title and an output directory."
                    )
                stage, output = command.args[0], Path(command.args[1])
                if stage == "prepare":
                    return self.service.run_cloud_prepare(output)
                if stage == "summarize":
                    return self.service.run_cloud_summarize(
                        output, call_api=True, from_readable=True
                    )
                if stage == "title":
                    return self.service.run_cloud_title(output, call_api=True, force=True)
                raise ValueError(f"Unknown cloud stage: {stage}")
            if command.name == "srt":
                if not command.args:
                    raise ValueError("/srt requires a media path.")
                return self.service.run_srt([Path(command.args[0])])
            raise ValueError(f"Unknown command: /{command.name}")

        def on_task_event(self, event: dict[str, Any]) -> None:
            try:
                self.call_from_thread(self.write_task_event, event)
            except RuntimeError:
                self.write_task_event(event)

        def write_task_event(self, event: dict[str, Any]) -> None:
            timeline = self.query_one("#timeline_log", RichLog)
            timeline.write(
                f"{event.get('event')} · {event.get('task_id')} · {event.get('stage') or event.get('detail') or ''}"
            )

        def refresh_sessions(self) -> None:
            sessions = self.query_one("#sessions", ListView)
            sessions.clear()
            for task in self.service.status().get("tasks", [])[:20]:
                sessions.append(ListItem(Static(f"{task.get('kind')} · {task.get('title')}")))

    Audio2TextTui(prompt).run()
    return 0
