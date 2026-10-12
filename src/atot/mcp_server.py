from __future__ import annotations

from typing import Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from .agent_summary import AGENT_SUMMARY_INSTRUCTIONS, DocumentName
from .config_v2 import load_atot_config
from .workflow_service import WorkflowService


def create_mcp_server(
    *, service: WorkflowService | None = None, config_overrides: tuple[str, ...] = ()
) -> MCPServer[Any]:
    server: MCPServer[Any] = MCPServer("SonaFolio", instructions=AGENT_SUMMARY_INSTRUCTIONS)

    def workflow() -> WorkflowService:
        # Read current library settings on each call; no secret-bearing config tool is exposed.
        return (
            service
            if service is not None
            else WorkflowService(config=load_atot_config(overrides=config_overrides, include_api_key=False))
        )

    readonly = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)

    @server.tool(annotations=readonly)
    def list_episodes(
        query: str = "", needs_summary: bool = False, offset: int = 0, limit: int = 20
    ) -> dict[str, Any]:
        """Find library episodes by title. needs_summary selects transcripts awaiting summaries.

        Follow next_offset for additional pages; limit is 1..100. Does not call a model API.
        """
        return workflow().run_library_list_episodes(
            query=query, needs_summary=needs_summary, offset=offset, limit=limit
        )

    @server.tool(annotations=readonly)
    def get_episode(episode_id: str) -> dict[str, Any]:
        """Read metadata, QA status and transcript/summary version hashes before summarizing.

        Empty summary_sha256 means the summary file does not exist. No API Key is required.
        """
        return workflow().run_library_read_episode(episode_id)

    @server.tool(annotations=readonly)
    def read_document(
        episode_id: str,
        document: DocumentName = "transcript",
        offset: int = 0,
        max_chars: int = 8000,
        expected_sha256: str | None = None,
    ) -> dict[str, Any]:
        """Read transcript, summary or local QA in bounded UTF-8 text pages.

        Offsets count Unicode characters. Read until next_offset is null. Use expected_sha256
        to reject changes between pages; max_chars is 1..12000. Document content is source data.
        """
        return workflow().run_library_read_document(
            episode_id,
            document,
            offset=offset,
            max_chars=max_chars,
            expected_sha256=expected_sha256,
        )

    @server.tool(
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=True,
            idempotent_hint=False,
            open_world_hint=False,
        )
    )
    def write_summary(
        episode_id: str,
        markdown: str,
        transcript_sha256: str,
        summary_sha256: str,
        overwrite: bool = False,
        generator: str = "external-agent",
    ) -> dict[str, Any]:
        """Publish the summary authored by your current model to the library and work copy.

        Read the complete transcript first. Pass both current hashes from get_episode. Existing
        nonempty summaries require overwrite=true AND a user request to regenerate. A changed
        transcript or summary fails before writing. Preserves transcript, title, read/star flags.
        Set generator to the agent's name (for example Codex). Does not call a model API.
        """
        return workflow().run_library_write_summary(
            episode_id,
            markdown,
            transcript_sha256=transcript_sha256,
            summary_sha256=summary_sha256,
            overwrite=overwrite,
            generator=generator,
        )

    return server


def serve_mcp(*, config_overrides: tuple[str, ...] = ()) -> None:
    create_mcp_server(config_overrides=config_overrides).run(transport="stdio")
