import asyncio
import logging
from abc import abstractmethod
from contextlib import AsyncExitStack
from typing import Any

import mcp.types as types
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from gi.repository import GLib, GObject  # type: ignore
from mcp import ClientSession, Implementation, ServerCapabilities
from mcp.client.session import (
    _default_elicitation_callback,
    _default_list_roots_callback,
    _default_logging_callback,
    _default_message_handler,
    _default_sampling_callback,
)
from mcp.shared.context import RequestContext
from mcp.shared.message import SessionMessage
from mcp.shared.session import RequestResponder

from speedoflight.constants import APPLICATION_NAME, SERVER_INITIALIZED_SIGNAL

CLIENT_INFO = types.Implementation(name=APPLICATION_NAME, version="0.1.0")


class BaseServer(GObject.Object):
    __gsignals__ = {
        SERVER_INITIALIZED_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, server_name: str):
        super().__init__()
        self._logger = logging.getLogger(server_name)
        self._server_name = server_name
        self._protocolVersion: str | int
        self._capabilities: ServerCapabilities
        self._serverInfo: Implementation
        self._instructions: str | None = None
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
        self._exit_stack: AsyncExitStack = AsyncExitStack()
        self._session: ClientSession | None = None

    @property
    def server_name(self) -> str:
        return self._server_name

    @property
    def protocol_version(self) -> str | int:
        return self._protocolVersion

    @property
    def capabilities(self) -> ServerCapabilities:
        return self._capabilities

    @property
    def server_info(self) -> Implementation:
        return self._serverInfo

    @property
    def instructions(self) -> str | None:
        return self._instructions

    @abstractmethod
    async def initialize(self):
        pass

    async def shutdown(self) -> None:
        async with self._cleanup_lock:
            try:
                await self._exit_stack.aclose()
                self._session = None
            except Exception as e:
                logging.error(f"Error shutting down {self.server_name}: {e}")

    def safe_emit(self, signal_name: str, *args):
        try:
            GLib.idle_add(self.emit, signal_name, *args)
        except Exception as e:
            self._logger.error(f"Error emitting signal ({signal_name}): {e}")

    async def _initialize_session(
        self,
        read_stream: MemoryObjectReceiveStream[SessionMessage | Exception],
        write_stream: MemoryObjectSendStream[SessionMessage],
    ):
        session = await self._exit_stack.enter_async_context(
            ClientSession(
                read_stream=read_stream,
                write_stream=write_stream,
                read_timeout_seconds=None,  # Default
                sampling_callback=self._on_sampling_callback,
                elicitation_callback=self._on_elicitation_callback,
                list_roots_callback=self._on_list_roots_callback,
                logging_callback=self._on_logging_callback,
                message_handler=self._on_message_handler,
                client_info=CLIENT_INFO,
            )
        )

        result: types.InitializeResult = await session.initialize()
        self._protocolVersion = result.protocolVersion
        self._capabilities = result.capabilities
        self._serverInfo = result.serverInfo
        self._instructions = result.instructions
        self._session = session
        self.safe_emit(SERVER_INITIALIZED_SIGNAL, self.server_name)

    async def list_tools(self) -> list[types.Tool]:
        tools: list[types.Tool] = []
        if not self._session:
            self._logger.error(f"Server {self.server_name} not initialized.")
            return tools

        cursor = None
        while True:
            result = await self._session.list_tools(cursor=cursor)
            tools.extend(result.tools)
            if result.nextCursor is None:
                break
            cursor = result.nextCursor

        return tools

    async def list_resources(self) -> list[types.Resource]:
        resources: list[types.Resource] = []
        if not self._session:
            self._logger.error(f"Server {self.server_name} not initialized.")
            return resources

        cursor = None
        while True:
            result = await self._session.list_resources(cursor=cursor)
            resources.extend(result.resources)
            if result.nextCursor is None:
                break
            cursor = result.nextCursor

        return resources

    async def list_resource_templates(self) -> list[types.ResourceTemplate]:
        templates: list[types.ResourceTemplate] = []
        if not self._session:
            self._logger.error(f"Server {self.server_name} not initialized.")
            return templates

        cursor = None
        while True:
            result = await self._session.list_resource_templates(cursor=cursor)
            templates.extend(result.resourceTemplates)
            if result.nextCursor is None:
                break
            cursor = result.nextCursor

        return templates

    async def list_prompts(self) -> list[types.Prompt]:
        prompts: list[types.Prompt] = []
        if not self._session:
            self._logger.error(f"Server {self.server_name} not initialized.")
            return prompts

        cursor = None
        while True:
            result = await self._session.list_prompts(cursor=cursor)
            prompts.extend(result.prompts)
            if result.nextCursor is None:
                break
            cursor = result.nextCursor

        return prompts

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        retries: int = 2,
        delay: float = 1.0,
    ) -> types.CallToolResult | None:
        if not self._session:
            self._logger.error(f"Server {self.server_name} not initialized.")
            return None

        attempt = 0
        while attempt < retries:
            try:
                self._logger.info(f"Executing {tool_name}.")
                return await self._session.call_tool(tool_name, arguments)
            except Exception as e:
                attempt += 1
                self._logger.warning(f"Error executing tool ({attempt}/{retries}): {e}")
                if attempt < retries:
                    self._logger.info(f"Retrying in {delay} seconds.")
                    await asyncio.sleep(delay)
                else:
                    self._logger.error("Max retries reached, failing.")
                    raise e

    #
    # Callbacks
    #
    # TODO: Find real MCP servers that support these features (besides test
    # MCPs like `everything`) and implement them.
    #
    # https://modelcontextprotocol.io/docs/learn/client-concepts
    #

    async def _on_sampling_callback(
        self,
        context: RequestContext["ClientSession", Any],
        params: types.CreateMessageRequestParams,
    ) -> types.CreateMessageResult | types.ErrorData:
        """Sampling allows servers to request language model completions
        through the client, enabling agentic behaviors while maintaining
        security and user control."""
        self._logger.warning(f"Sampling: context ({context}) and params ({params}).")
        return await _default_sampling_callback(context, params)

    async def _on_elicitation_callback(
        self,
        context: RequestContext["ClientSession", Any],
        params: types.ElicitRequestParams,
    ) -> types.ElicitResult | types.ErrorData:
        """Elicitation enables servers to request specific information from
        users during interactions, creating more dynamic and responsive workflows."""
        self._logger.warning(f"Elicitation: context ({context}) and params ({params}).")
        return await _default_elicitation_callback(context, params)

    async def _on_list_roots_callback(
        self,
        context: RequestContext["ClientSession", Any],
    ) -> types.ListRootsResult | types.ErrorData:
        """Roots define filesystem boundaries for server operations, allowing
        clients to specify which directories servers should focus on."""
        self._logger.warning(f"List roots: context ({context}).")
        return await _default_list_roots_callback(context)

    async def _on_logging_callback(
        self,
        params: types.LoggingMessageNotificationParams,
    ) -> None:
        self._logger.warning(f"Logging: params ({params}).")
        await _default_logging_callback(params)

    async def _on_message_handler(
        self,
        message: (
            RequestResponder[types.ServerRequest, types.ClientResult]
            | types.ServerNotification
            | Exception
        ),
    ) -> None:
        self._logger.warning(f"Message handler: message ({message})")
        await _default_message_handler(message)
