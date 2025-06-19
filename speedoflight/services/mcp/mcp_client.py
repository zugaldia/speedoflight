import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, override

from langchain_mcp_adapters.client import Connection, MultiServerMCPClient
from langchain_mcp_adapters.sessions import create_session
from mcp import ClientSession, types


class McpClient(MultiServerMCPClient):
    """Extends the functionality of the Langchain client to access additional MCP functionality."""

    def __init__(self, connections: dict[str, Connection] | None = None) -> None:
        super().__init__(connections=connections)
        self._logger = logging.getLogger(__name__)
        self._metadata: dict[str, types.InitializeResult] = {}
        self._logger.info("Initialized.")

    @override
    @asynccontextmanager
    async def session(
        self, server_name: str, *, auto_initialize: bool = True
    ) -> AsyncIterator[ClientSession]:
        """Override the original implementation to capture the initialization result."""
        async with create_session(self.connections[server_name]) as session:
            result = await session.initialize()
            self._log_metadata(server_name, result)
            yield session

    def _log_metadata(self, server_name: str, result: types.InitializeResult) -> None:
        if server_name in self._metadata:
            return  # Already logged

        self._metadata[server_name] = result
        self._logger.debug(f"----- Server {server_name} -----")
        self._logger.debug(f"- Protocol version: {result.protocolVersion}")
        self._logger.debug(f"- Experimental: {result.capabilities.experimental}")
        self._logger.debug(f"- Logging: {result.capabilities.logging}")
        self._logger.debug(f"- Prompts: {result.capabilities.prompts}")
        self._logger.debug(f"- Resources: {result.capabilities.resources}")
        self._logger.debug(f"- Tools: {result.capabilities.tools}")
        self._logger.debug(f"- Server info: {result.serverInfo}")
        self._logger.debug(f"- Instructions: {result.instructions}")

    async def send_ping(self, server_name: str) -> types.EmptyResult:
        async with self.session(server_name) as session:
            return await session.send_ping()

    async def list_prompts(self, server_name: str) -> types.ListPromptsResult:
        async with self.session(server_name) as session:
            return await session.list_prompts()
