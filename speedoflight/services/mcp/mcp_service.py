from langchain_core.tools import BaseTool
from mcp import types

from speedoflight.services.base_service import BaseService
from speedoflight.services.configuration.configuration_service import (
    ConfigurationService,
)
from speedoflight.services.mcp.mcp_client import McpClient


class McpService(BaseService):
    def __init__(self, configuration: ConfigurationService):
        super().__init__(service_name="mcp")
        self._mcp_servers = configuration.get_config().mcp_servers
        self._client = McpClient(connections=self._mcp_servers)
        self._logger.info("Initialized.")

    async def send_ping(self, server_name: str) -> types.EmptyResult | None:
        try:
            return await self._client.send_ping(server_name)
        except Exception as e:
            self._logger.error(f"Failed to ping {server_name}: {e}")
            return None

    async def list_prompts(self, server_name: str) -> types.ListPromptsResult | None:
        try:
            # This will fail, for example, if prompt capabilities is missing
            return await self._client.list_prompts(server_name=server_name)
        except Exception as e:
            self._logger.error(f"Failed to list prompts for {server_name}: {e}")
            return None

    async def get_tools(self, *, server_name: str | None = None) -> list[BaseTool]:
        try:
            # Safe to assume that all MCP servers include tools but not guaranteed
            return await self._client.get_tools(server_name=server_name)
        except Exception as e:
            name = server_name or "all servers"
            self._logger.error(f"Failed to get tools for {name}: {e}")
            return []
