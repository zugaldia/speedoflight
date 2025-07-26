import asyncio

from mcp import types
from pydantic import BaseModel

from speedoflight.constants import SERVER_INITIALIZED_SIGNAL
from speedoflight.models import (
    ResponseMessage,
    StdioConfig,
    StreamableHttpConfig,
    ToolInputResponse,
)
from speedoflight.services.base_service import BaseService
from speedoflight.services.configuration import ConfigurationService
from speedoflight.services.mcp.base_server import BaseServer
from speedoflight.services.mcp.stdio_server import StdioConfiguration, StdioServer
from speedoflight.services.mcp.streamable_http_server import (
    StreamableHttpConfiguration,
    StreamableHttpServer,
)


class McpCallToolResult(BaseModel):
    """We include both the call ID and the tool name because some providers
    require the former (e.g. Anthropic, OpenAi) and others require the
    latter (e.g. Ollama)."""

    call_id: str
    name: str
    result: types.CallToolResult


class McpService(BaseService):
    def __init__(self, configuration: ConfigurationService):
        super().__init__(service_name="mcp")
        self._configuration = configuration
        self._servers: dict[str, BaseServer] = {}
        self._tools: dict[str, list[types.Tool]] = {}
        self._resources: dict[str, list[types.Resource]] = {}
        self._resource_templates: dict[str, list[types.ResourceTemplate]] = {}
        self._prompts: dict[str, list[types.Prompt]] = {}
        self._initialize()
        self._logger.info("Initialized.")

    @property
    def tools(self) -> dict[str, list[types.Tool]]:
        return self._tools

    @property
    def resources(self) -> dict[str, list[types.Resource]]:
        return self._resources

    @property
    def resource_templates(self) -> dict[str, list[types.ResourceTemplate]]:
        return self._resource_templates

    @property
    def prompts(self) -> dict[str, list[types.Prompt]]:
        return self._prompts

    def _initialize(self):
        if not self._configuration.config.mcps:
            self._logger.warning("No MCPs configured in the application config.")
            return

        for server_name, mcp_config in self._configuration.config.mcps.items():
            if mcp_config.enabled:
                if isinstance(mcp_config, StdioConfig):
                    self._logger.info(f"Adding STDIO MCP: {server_name}")
                    self._servers[server_name] = StdioServer(
                        server_name=server_name,
                        configuration=StdioConfiguration(
                            command=mcp_config.command,
                            args=mcp_config.args,
                            env=mcp_config.env,
                        ),
                    )
                elif isinstance(mcp_config, StreamableHttpConfig):
                    self._logger.info(f"Adding Streamable HTTP MCP: {server_name}")
                    self._servers[server_name] = StreamableHttpServer(
                        server_name=server_name,
                        configuration=StreamableHttpConfiguration(
                            url=mcp_config.url,
                            headers=mcp_config.headers,
                        ),
                    )
                else:
                    self._logger.warning(f"Unsupported MCP type: {mcp_config.type}")
                    continue

        for server in self._servers.values():
            server.connect(SERVER_INITIALIZED_SIGNAL, self._on_server_initialized)
            self._logger.info(f"Initializing {server.server_name} server.")
            asyncio.create_task(server.initialize())

    def _on_server_initialized(self, server: BaseServer, server_name: str):
        self._logger.info(f"Server {server_name} is ready, querying for features.")
        asyncio.create_task(self._query_server_features(server))

    async def _query_server_features(self, server: BaseServer) -> None:
        server_name = server.server_name
        self._logger.info(f"{server_name} protocol version: {server.protocol_version}")
        self._logger.info(f"{server_name} server info: {server.server_info}")
        self._logger.info(f"{server_name} instructions: {server.instructions}")

        capabilities = server.capabilities
        self._logger.info(f"{server_name} capabilities: {capabilities}")
        if capabilities.tools:
            await self._query_tools(server)
        if capabilities.resources:
            await self._query_resources(server)
            await self._query_resource_templates(server)
        if capabilities.prompts:
            await self._query_prompts(server)

    async def _query_tools(self, server: BaseServer) -> None:
        server_name = server.server_name
        try:
            tools = await server.list_tools()
            if tools:
                self._tools[server_name] = tools
                count = len(tools)
                names = [tool.name for tool in tools]
                self._logger.info(f"{server_name} has {count} tools: {names}")
            else:
                self._logger.info(f"{server_name} has no tools")
        except Exception as e:
            self._logger.error(f"Failed to query tools for {server_name}: {e}")

    async def _query_resources(self, server: BaseServer) -> None:
        server_name = server.server_name
        try:
            resources = await server.list_resources()
            if resources:
                self._resources[server_name] = resources
                count = len(resources)
                names = [resource.name for resource in resources]
                self._logger.info(f"{server_name} has {count} resources: {names}")
            else:
                self._logger.info(f"{server_name} has no resources")
        except Exception as e:
            self._logger.error(f"Failed to query resources for {server_name}: {e}")

    async def _query_resource_templates(self, server: BaseServer) -> None:
        server_name = server.server_name
        try:
            templates = await server.list_resource_templates()
            if templates:
                self._resource_templates[server_name] = templates
                count = len(templates)
                names = [template.name for template in templates]
                self._logger.info(
                    f"{server_name} has {count} resource templates: {names}"
                )
            else:
                self._logger.info(f"{server_name} has no resource templates")
        except Exception as e:
            self._logger.error(
                f"Failed to query resource templates for {server_name}: {e}"
            )

    async def _query_prompts(self, server: BaseServer) -> None:
        server_name = server.server_name
        try:
            prompts = await server.list_prompts()
            if prompts:
                self._prompts[server_name] = prompts
                count = len(prompts)
                names = [prompt.name for prompt in prompts]
                self._logger.info(f"{server_name} has {count} prompts: {names}")
            else:
                self._logger.info(f"{server_name} has no prompts")
        except Exception as e:
            self._logger.error(f"Failed to query prompts for {server_name}: {e}")

    async def call_tool(self, message: ResponseMessage) -> McpCallToolResult | None:
        try:
            # This assumes that only one tool use content is present per
            # message. If there are more than one, they will be ignored.
            # (See e.g. Anthropic's ToolChoiceAutoParam)
            tool_input = next(
                (
                    content
                    for content in message.content
                    if isinstance(content, ToolInputResponse)
                ),
                None,
            )
            if tool_input is None:
                self._logger.warning("No tool input content found in message.")
                return None

            # This assumes that there are no overlaps in tool names across
            # servers (which should be the case anyway). If there is, the first
            # tool with the right name will be used.
            for server_name, tools in self._tools.items():
                for tool in tools:
                    if tool.name == tool_input.name:
                        tool_output = await self._servers[server_name].call_tool(
                            tool_input.name, tool_input.arguments
                        )
                        return (
                            McpCallToolResult(
                                call_id=tool_input.call_id,
                                name=tool_input.name,
                                result=tool_output,
                            )
                            if tool_output
                            else None
                        )
        except Exception as e:
            self._logger.error(f"Error calling tool: {e}")
            return None

    def shutdown(self):
        # TODO: Shutdown all servers gracefully
        self._logger.info("Shutting down.")
