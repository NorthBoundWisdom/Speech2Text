from __future__ import annotations

import asyncio
import os
import sys

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from atot.config_v2 import AtotConfig, AtotLibraryConfig
from atot.library_store import LibraryStore
from atot.mcp_server import create_mcp_server
from atot.task_store import TaskStore
from atot.workflow_service import WorkflowService


def fixture_service(tmp_path):
    store = LibraryStore(tmp_path / "Audio2TextLibrary", data_root=tmp_path / "data")
    store.upsert_episode({"episode_id": "mcp-episode", "title": "MCP 测试"})
    store.write_episode_documents("mcp-episode", summary="", transcript="[00:00:01] 本地转录。\n")
    service = WorkflowService(
        config=AtotConfig(
            path=tmp_path / "config.toml",
            library=AtotLibraryConfig(
                storage="local",
                local_root=str(store.root),
            ),
        ),
        task_store=TaskStore(tmp_path / "tasks"),
    )
    # Keep every test artifact in its fixture's data root.
    service._library_store = lambda: store
    return service


def test_mcp_client_can_read_and_write_without_credentials(tmp_path):
    service = fixture_service(tmp_path)

    async def run():
        async with Client(create_mcp_server(service=service)) as client:
            listing = await client.list_tools()
            tools = {tool.name: tool for tool in listing.tools}
            assert set(tools) == {"list_episodes", "get_episode", "read_document", "write_summary"}
            assert tools["read_document"].annotations.read_only_hint is True
            assert tools["write_summary"].annotations.read_only_hint is False
            episode = await client.call_tool("get_episode", {"episode_id": "mcp-episode"})
            assert not episode.is_error
            info = episode.structured_content
            page = await client.call_tool("read_document", {"episode_id": "mcp-episode"})
            transcript = (
                service._library_store().episodes_root / "mcp-episode/documents/transcript.md"
            )
            assert page.structured_content["text"] == transcript.read_bytes().decode("utf-8")
            result = await client.call_tool(
                "write_summary",
                {
                    "episode_id": "mcp-episode",
                    "markdown": "# Agent 总结\n\n基于转录。",
                    "transcript_sha256": info["transcript_sha256"],
                    "summary_sha256": info["summary_sha256"],
                    "generator": "Codex",
                },
            )
            assert not result.is_error and result.structured_content["success"] is True
            refused = await client.call_tool(
                "write_summary",
                {
                    "episode_id": "mcp-episode",
                    "markdown": "# stale",
                    "transcript_sha256": info["transcript_sha256"],
                    "summary_sha256": info["summary_sha256"],
                },
            )
            assert refused.is_error

    asyncio.run(run())


@pytest.mark.parametrize("mode", ["auto", "legacy"])
def test_real_stdio_server_initializes_and_uses_configured_library(tmp_path, mode):
    service = fixture_service(tmp_path)
    store = service._library_store()
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "atot.cli",
            "-c",
            'library.storage="local"',
            "-c",
            f'library.local_root="{store.root.as_posix()}"',
            "mcp",
        ],
        env={**os.environ, "ATOT_DATA_ROOT": str(store.data_root)},
    )

    async def run():
        async with Client(params, read_timeout_seconds=15, mode=mode) as client:
            tools = await client.list_tools()
            assert len(tools.tools) == 4
            result = await client.call_tool("list_episodes", {"needs_summary": True})
            assert not result.is_error
            assert result.structured_content["episodes"][0]["episode_id"] == "mcp-episode"

    asyncio.run(run())
