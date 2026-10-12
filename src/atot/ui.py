from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
from typing import Any
from urllib.parse import parse_qs, urlparse
import webbrowser

from .models import describe_models
from .progress import cloud_progress, local_progress
from .utils import read_json


@dataclass(frozen=True)
class UiOptions:
    host: str = "127.0.0.1"
    port: int = 8765


HTML = """<!doctype html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SonaFolio</title>
  <style>
    :root { color-scheme: light dark; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: Canvas; color: CanvasText; }
    main { max-width: 1120px; margin: 0 auto; padding: 24px; display: grid; gap: 18px; }
    header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
    h1 { font-size: 22px; margin: 0; letter-spacing: 0; }
    section { border: 1px solid color-mix(in srgb, CanvasText 18%, transparent); border-radius: 8px; padding: 16px; }
    label { display: grid; gap: 6px; font-size: 13px; color: color-mix(in srgb, CanvasText 72%, transparent); }
    input, select, button { font: inherit; border-radius: 6px; border: 1px solid color-mix(in srgb, CanvasText 22%, transparent); padding: 9px 10px; background: Canvas; color: CanvasText; }
    button { cursor: pointer; min-width: 40px; }
    button.primary { background: CanvasText; color: Canvas; }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .status { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
    .metric { border: 1px solid color-mix(in srgb, CanvasText 14%, transparent); border-radius: 6px; padding: 10px; min-height: 54px; }
    .metric strong { display: block; font-size: 18px; margin-top: 4px; }
    .progress-wrap { display: grid; gap: 10px; }
    .progress-row { display: grid; grid-template-columns: 76px minmax(0, 1fr) 120px; gap: 10px; align-items: center; font-size: 13px; }
    .bar { height: 10px; border-radius: 999px; background: color-mix(in srgb, CanvasText 12%, transparent); overflow: hidden; }
    .fill { height: 100%; width: 0%; background: CanvasText; transition: width 160ms ease; }
    .fill.cloud { background: color-mix(in srgb, CanvasText 72%, #2aa198); }
    .progress-meta { text-align: right; color: color-mix(in srgb, CanvasText 72%, transparent); white-space: nowrap; }
    pre { overflow: auto; white-space: pre-wrap; margin: 0; font-size: 12px; }
    @media (max-width: 760px) { .grid, .status, .progress-row { grid-template-columns: 1fr; } main { padding: 14px; } .progress-meta { text-align: left; } }
  </style>
</head>
<body>
  <main>
    <header><h1>SonaFolio</h1><button id="refresh">↻</button></header>
    <section class="grid">
      <label>Input <input id="input" placeholder="process/0528/episode/episode.m4a"></label>
      <label>Output <input id="output" placeholder="process/0528/episode/output"></label>
      <label>Model <select id="model"></select></label>
      <label>Mode <select id="mode"><option value="local">Local</option><option value="cloud-input">Cloud Input</option></select></label>
      <label><input id="smart" type="checkbox"> Smart chunking</label>
      <label><input id="localOnly" type="checkbox" checked> Local only</label>
    </section>
    <section class="actions">
      <button id="start" class="primary">▶</button>
      <button id="qa">QA</button>
      <button id="cloud">Cloud</button>
      <button id="openOutput">Open</button>
      <span id="message"></span>
    </section>
    <section class="status">
      <div class="metric">Run<strong id="runStatus">idle</strong></div>
      <div class="metric">QA<strong id="qaStatus">unknown</strong></div>
      <div class="metric">Repair<strong id="repairStatus">none</strong></div>
      <div class="metric">Cloud<strong id="cloudStatus">none</strong></div>
    </section>
    <section class="progress-wrap">
      <div class="progress-row"><span>Local</span><div class="bar"><div id="localFill" class="fill"></div></div><span id="localMeta" class="progress-meta">0/0</span></div>
      <div class="progress-row"><span>Cloud</span><div class="bar"><div id="cloudFill" class="fill cloud"></div></div><span id="cloudMeta" class="progress-meta">0/0</span></div>
    </section>
    <section><pre id="log">{}</pre></section>
  </main>
  <script>
    async function api(path, options) {
      const r = await fetch(path, options);
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || r.statusText);
      return data;
    }
    async function loadModels() {
      const rows = await api('/api/models');
      const select = document.getElementById('model');
      select.innerHTML = rows.map(r => `<option value="${r.alias}">${r.alias}</option>`).join('');
    }
    async function refresh() {
      const output = document.getElementById('output').value;
      if (!output) return;
      const status = await api('/api/status?output=' + encodeURIComponent(output));
      runStatus.textContent = status.run_status || 'idle';
      qaStatus.textContent = status.qa_status || 'unknown';
      repairStatus.textContent = status.repair_status || 'none';
      const local = status.local_progress || status.chunk_progress || {completed: 0, total: 0, percent: 0, stage: 'missing'};
      const cloud = status.cloud_progress || {completed: 0, total: 0, percent: 0, status: 'missing'};
      cloudStatus.textContent = status.cloud_status || cloud.status || 'none';
      localFill.style.width = Math.max(0, Math.min(100, local.percent || 0)) + '%';
      cloudFill.style.width = Math.max(0, Math.min(100, cloud.percent || 0)) + '%';
      localMeta.textContent = (local.stage || local.status || 'local') + ' · ' + local.completed + '/' + local.total;
      cloudMeta.textContent = (cloud.status || 'cloud') + ' · ' + cloud.completed + '/' + cloud.total + (cloud.failed ? ' · failed ' + cloud.failed : '');
      log.textContent = JSON.stringify(status, null, 2);
    }
    start.onclick = async () => {
      const body = {
        input: input.value, output: output.value, model: model.value,
        smart: smart.checked, local_only: localOnly.checked
      };
      const result = await api('/api/transcribe', {method: 'POST', body: JSON.stringify(body)});
      message.textContent = 'pid ' + result.pid;
      setTimeout(refresh, 1000);
    };
    qa.onclick = async () => { await api('/api/qa', {method:'POST', body: JSON.stringify({output: output.value})}); await refresh(); };
    cloud.onclick = async () => { await api('/api/cloud-prepare', {method:'POST', body: JSON.stringify({output: output.value})}); await refresh(); };
    openOutput.onclick = async () => {
      const result = await api('/api/open-output', {method:'POST', body: JSON.stringify({output: output.value})});
      message.textContent = result.opened ? 'opened' : result.output;
    };
    refresh.onclick = refresh;
    loadModels();
  </script>
</body>
</html>
"""


def status_payload(output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir).expanduser()
    details = output
    run = _read_json(details / "run.json")
    qa = _read_json(details / "qa.json")
    repair = _read_json(output / "repair" / "repair_plan.json")
    repair_run = _read_latest_json(output / "repair", "repair_run_*.json")
    cloud_manifest = _read_json(output / "cloud" / "input" / "manifest.json")
    run_success = run.get("success") if run else None
    qa_success = qa.get("success") if qa else None
    repair_windows = repair.get("windows", []) if isinstance(repair.get("windows"), list) else []
    cloud_files = (
        cloud_manifest.get("input_files", [])
        if isinstance(cloud_manifest.get("input_files"), list)
        else []
    )
    local = local_progress(output)
    cloud = cloud_progress(output)
    return {
        "output": str(output),
        "run_status": "done" if run_success is True else "missing" if not run else "failed",
        "qa_status": "pass" if qa_success is True else "fail" if qa else "missing",
        "repair_status": "applied"
        if repair_run.get("success") is True
        else f"{len(repair_windows)} windows"
        if repair
        else "missing",
        "cloud_status": cloud["status"]
        if cloud["status"] != "missing"
        else f"{len(cloud_files)} files"
        if cloud_manifest
        else "missing",
        "chunk_progress": {
            "completed": local["completed"],
            "total": local["total"],
            "counts": run.get("chunk_status_counts", {})
            if isinstance(run.get("chunk_status_counts"), dict)
            else {},
        },
        "local_progress": local,
        "cloud_progress": cloud,
        "run": run,
        "qa": qa,
        "repair": repair,
        "repair_run": repair_run,
        "cloud_manifest": cloud_manifest,
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def _read_latest_json(directory: Path, pattern: str) -> dict[str, Any]:
    paths = sorted(directory.glob(pattern))
    if not paths:
        return {}
    return _read_json(paths[-1])


def _json_response(handler: BaseHTTPRequestHandler, payload: Any, *, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _start_process(args: list[str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def transcribe_command(payload: dict[str, Any]) -> list[str]:
    args = [sys.executable, "-m", "atot.cli", "exec", "transcribe", str(payload["input"])]
    if payload.get("output"):
        args.extend(["--job-dir", str(payload["output"])])
    if payload.get("model"):
        args.extend(["--model", str(payload["model"])])
    if payload.get("smart"):
        args.extend(["--chunking", "smart"])
    if payload.get("local_only"):
        args.append("--local-only")
    return args


def qa_command(payload: dict[str, Any]) -> list[str]:
    return [sys.executable, "-m", "atot.cli", "exec", "qa", str(payload["output"])]


def cloud_prepare_command(payload: dict[str, Any]) -> list[str]:
    return [sys.executable, "-m", "atot.cli", "exec", "cloud", "prepare", str(payload["output"])]


def open_output_folder(output_dir: str | Path, *, opener: Any | None = None) -> dict[str, Any]:
    output = Path(output_dir).expanduser()
    if not output.exists():
        raise FileNotFoundError(f"Output directory does not exist: {output}")
    open_fn = opener or (lambda path: webbrowser.open(path.resolve().as_uri()))
    opened = bool(open_fn(output))
    return {"success": opened, "output": str(output), "opened": opened}


def make_handler() -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                body = HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if parsed.path == "/api/models":
                _json_response(self, describe_models())
                return
            if parsed.path == "/api/status":
                output = parse_qs(parsed.query).get("output", [""])[0]
                _json_response(self, status_payload(output))
                return
            _json_response(self, {"error": "not found"}, status=404)

        def do_POST(self) -> None:  # noqa: N802
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/api/transcribe":
                    args = transcribe_command(payload)
                    proc = _start_process(args)
                    _json_response(self, {"pid": proc.pid, "command": args})
                    return
                if self.path == "/api/qa":
                    proc = _start_process(qa_command(payload))
                    _json_response(self, {"pid": proc.pid})
                    return
                if self.path == "/api/cloud-prepare":
                    proc = _start_process(cloud_prepare_command(payload))
                    _json_response(self, {"pid": proc.pid})
                    return
                if self.path == "/api/open-output":
                    _json_response(self, open_output_folder(str(payload["output"])))
                    return
            except Exception as exc:
                _json_response(self, {"error": str(exc)}, status=400)
                return
            _json_response(self, {"error": "not found"}, status=404)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    return Handler


def serve_ui(options: UiOptions) -> None:
    server = ThreadingHTTPServer((options.host, options.port), make_handler())
    print(f"SonaFolio UI: http://{options.host}:{options.port}", file=sys.stderr)
    server.serve_forever()
